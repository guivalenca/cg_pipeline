from __future__ import annotations

import json
import inspect
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from concept_graph_creation.runtime.output_budget import (
    OutputBudgetPolicy,
    resolve_output_budget,
)


Validator = Callable[[dict[str, Any]], list[str]]
ModelCall = Callable[..., str]
Normalizer = Callable[[str, dict[str, Any]], dict[str, Any]]
FLASH_ROUTE_ALIAS = "Flash"
PRO_ROUTE_ALIAS = "Pro"
PRO_THINKING_ROUTE_ALIAS = "Pro Thinking"


@dataclass(frozen=True)
class ModelRoute:
    alias: str
    provider: str
    model: str
    thinking_enabled: bool = True
    reasoning_effort: str | None = "high"
    provider_sort: str | None = "latency"
    allow_provider_fallbacks: bool = True
    require_provider_parameters: bool = True


@dataclass(frozen=True)
class ModelRouter:
    routes: dict[str, ModelRoute]

    @classmethod
    def default(cls) -> "ModelRouter":
        return cls(
            routes={
                FLASH_ROUTE_ALIAS: ModelRoute(
                    alias=FLASH_ROUTE_ALIAS,
                    provider="openrouter",
                    model="deepseek/deepseek-v4-flash",
                    thinking_enabled=False,
                    reasoning_effort=None,
                ),
                PRO_ROUTE_ALIAS: ModelRoute(
                    alias=PRO_ROUTE_ALIAS,
                    provider="openrouter",
                    model="deepseek/deepseek-v4-pro",
                    thinking_enabled=False,
                    reasoning_effort=None,
                ),
                PRO_THINKING_ROUTE_ALIAS: ModelRoute(
                    alias=PRO_THINKING_ROUTE_ALIAS,
                    provider="openrouter",
                    model="deepseek/deepseek-v4-pro",
                    thinking_enabled=True,
                    reasoning_effort="high",
                ),
            }
        )

    def resolve(self, alias: str) -> ModelRoute:
        try:
            return self.routes[alias]
        except KeyError as exc:
            known = ", ".join(sorted(self.routes))
            raise StageBlockedError(f"Unknown model route '{alias}'. Known routes: {known}") from exc


@dataclass(frozen=True)
class StageContract:
    name: str
    required_inputs: list[str]
    output_artifact: str
    model_route: str
    validator: Validator
    repair_model_route: str | None = None
    contextual_repair_model_route: str | None = None
    allow_format_repair: bool = True
    normalizer: Normalizer | None = None
    output_budget_policy: OutputBudgetPolicy | None = None


@dataclass(frozen=True)
class StageResult:
    stage_name: str
    artifact_path: Path
    raw_output_paths: list[Path]
    repaired: bool


class StageBlockedError(RuntimeError):
    """A stage failed its contract and downstream stages must not consume it."""


class ModelOutputTruncatedError(StageBlockedError):
    """The provider stopped at the output cap; the partial response is unusable."""

    finish_reason = "length"


class StageRunner:
    def __init__(self, *, router: ModelRouter, model_call: ModelCall):
        self.router = router
        self.model_call = model_call

    def run(self, contract: StageContract, *, run_dir: Path) -> StageResult:
        route = self.router.resolve(contract.model_route)
        inputs = self._load_required_inputs(contract, run_dir)
        raw_output_paths: list[Path] = []
        output_budget = resolve_output_budget(
            stage_name=contract.name,
            inputs=inputs,
            configured=contract.output_budget_policy,
        )

        raw, primary_attempt_count = self._run_budgeted_model_call(
            run_dir=run_dir,
            contract=contract,
            route=route,
            inputs=inputs,
            repair_context=None,
            output_budget=output_budget,
            attempt_offset=0,
        )
        primary_filename = (
            "attempt_1.txt"
            if primary_attempt_count == 1
            else f"attempt_{primary_attempt_count}_length_retry.txt"
        )
        raw_output_paths.append(
            self._write_raw_output(run_dir, contract.name, primary_filename, raw)
        )
        artifact, errors = self._normalize_and_validate(raw, contract, inputs)
        if errors and contract.allow_format_repair:
            repair_type = _repair_type_for_errors(errors)
            repair_route = self.router.resolve(_repair_route_alias(contract, repair_type))
            repair_context = {
                "repair_type": repair_type,
                "validator_errors": errors,
                "failed_output": raw,
                "instruction": _repair_instruction(repair_type),
            }
            repaired_raw, repair_attempt_count = self._run_budgeted_model_call(
                run_dir=run_dir,
                contract=contract,
                route=repair_route,
                inputs=inputs,
                repair_context=repair_context,
                output_budget=output_budget,
                attempt_offset=primary_attempt_count,
                repair_type=repair_type,
            )
            repaired_attempt = primary_attempt_count + repair_attempt_count
            repair_suffix = (
                f"{repair_type}_length_retry"
                if repair_attempt_count > 1
                else repair_type
            )
            raw_output_paths.append(
                self._write_raw_output(
                    run_dir,
                    contract.name,
                    f"attempt_{repaired_attempt}_{repair_suffix}.txt",
                    repaired_raw,
                )
            )
            artifact, errors = self._normalize_and_validate(repaired_raw, contract, inputs)
            if not errors:
                return self._write_artifact(contract, run_dir, artifact, raw_output_paths, repaired=True)

        if errors:
            joined = "; ".join(errors)
            raise StageBlockedError(f"Stage '{contract.name}' failed Stage Contract: {joined}")

        return self._write_artifact(contract, run_dir, artifact, raw_output_paths, repaired=False)

    def _run_budgeted_model_call(
        self,
        *,
        run_dir: Path,
        contract: StageContract,
        route: ModelRoute,
        inputs: dict[str, Any],
        repair_context: dict[str, Any] | None,
        output_budget: OutputBudgetPolicy,
        attempt_offset: int,
        repair_type: str | None = None,
    ) -> tuple[str, int]:
        caps = output_budget.attempt_caps()
        for budget_index, max_tokens in enumerate(caps, start=1):
            attempt = attempt_offset + budget_index
            started_at = time.monotonic()
            progress_fields: dict[str, Any] = {
                "attempt": attempt,
                "route": route.alias,
                "input_keys": sorted(inputs),
                "input_bytes": _json_size_bytes(inputs),
                "requested_max_tokens": max_tokens,
                "output_budget_policy": output_budget.operation,
                "output_budget_policy_version": output_budget.version,
                "output_budget_attempt": budget_index,
                "output_budget_retry": budget_index > 1,
                "length_retry_from": output_budget.initial_max_tokens,
                "length_retry_to": output_budget.length_retry_max_tokens,
            }
            if repair_type is not None:
                progress_fields["repair_type"] = repair_type
            self._write_progress_event(
                run_dir,
                contract.name,
                "model_call_start",
                **progress_fields,
            )
            try:
                raw = self._invoke_model_call(
                    route=route,
                    stage_name=contract.name,
                    inputs=inputs,
                    repair_context=repair_context,
                    max_tokens=max_tokens,
                    output_budget=output_budget,
                    output_budget_attempt=budget_index,
                )
            except Exception as exc:
                self._write_progress_event(
                    run_dir,
                    contract.name,
                    "model_call_error",
                    **{
                        key: value
                        for key, value in progress_fields.items()
                        if key not in {"input_keys", "input_bytes"}
                    },
                    elapsed_seconds=round(time.monotonic() - started_at, 3),
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                if (
                    isinstance(exc, ModelOutputTruncatedError)
                    and budget_index < len(caps)
                ):
                    continue
                raise
            self._write_progress_event(
                run_dir,
                contract.name,
                "model_call_returned",
                **{
                    key: value
                    for key, value in progress_fields.items()
                    if key not in {"input_keys", "input_bytes"}
                },
                elapsed_seconds=round(time.monotonic() - started_at, 3),
                output_bytes=len(raw.encode("utf-8")),
            )
            return raw, budget_index
        raise AssertionError("output budget attempts were exhausted unexpectedly")

    def _invoke_model_call(
        self,
        *,
        route: ModelRoute,
        stage_name: str,
        inputs: dict[str, Any],
        repair_context: dict[str, Any] | None,
        max_tokens: int,
        output_budget: OutputBudgetPolicy,
        output_budget_attempt: int,
    ) -> str:
        arguments: dict[str, Any] = {
            "route": route,
            "stage_name": stage_name,
            "inputs": inputs,
            "repair_context": repair_context,
        }
        optional_arguments = {
            "max_tokens": max_tokens,
            "output_budget": output_budget,
            "output_budget_attempt": output_budget_attempt,
        }
        try:
            signature = inspect.signature(self.model_call)
        except (TypeError, ValueError):
            signature = None
        if signature is not None:
            accepts_arbitrary_keywords = any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in signature.parameters.values()
            )
            for name, value in optional_arguments.items():
                if accepts_arbitrary_keywords or name in signature.parameters:
                    arguments[name] = value
        return self.model_call(**arguments)

    def _write_progress_event(self, run_dir: Path, stage_name: str, event: str, **fields: Any) -> None:
        path = run_dir / "stage_progress.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stage_name": stage_name,
            "event": event,
            **fields,
        }
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def _load_required_inputs(self, contract: StageContract, run_dir: Path) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        for relative_path in contract.required_inputs:
            path = run_dir / relative_path
            if not path.is_file():
                raise StageBlockedError(f"Stage '{contract.name}' missing required input artifact: {relative_path}")
            try:
                inputs[relative_path] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise StageBlockedError(
                    f"Stage '{contract.name}' input artifact is not valid JSON: {relative_path}: {exc.msg}"
                ) from exc
        return inputs

    def _normalize_and_validate(
        self,
        raw: str,
        contract: StageContract,
        inputs: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        if contract.normalizer:
            try:
                artifact = contract.normalizer(raw, inputs)
            except json.JSONDecodeError as exc:
                return {}, [f"JSON parse error at line {exc.lineno} column {exc.colno}: {exc.msg}"]
            except ValueError as exc:
                return {}, [str(exc)]
        else:
            try:
                artifact = json.loads(raw)
            except json.JSONDecodeError as exc:
                return {}, [f"JSON parse error at line {exc.lineno} column {exc.colno}: {exc.msg}"]
            if not isinstance(artifact, dict):
                return {}, ["stage output must be a JSON object"]
        return artifact, contract.validator(artifact)

    def _write_raw_output(self, run_dir: Path, stage_name: str, filename: str, raw: str) -> Path:
        output_dir = run_dir / "raw_model_outputs" / stage_name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        output_path.write_text(raw, encoding="utf-8")
        return output_path

    def _write_artifact(
        self,
        contract: StageContract,
        run_dir: Path,
        artifact: dict[str, Any],
        raw_output_paths: list[Path],
        *,
        repaired: bool,
    ) -> StageResult:
        artifact_path = run_dir / contract.output_artifact
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._write_progress_event(
            run_dir,
            contract.name,
            "artifact_written",
            artifact_path=str(artifact_path.relative_to(run_dir)),
            repaired=repaired,
        )
        return StageResult(
            stage_name=contract.name,
            artifact_path=artifact_path,
            raw_output_paths=raw_output_paths,
            repaired=repaired,
        )


def _json_size_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def _repair_route_alias(contract: StageContract, repair_type: str) -> str:
    if repair_type == "contextual_repair" and contract.contextual_repair_model_route:
        return contract.contextual_repair_model_route
    return contract.repair_model_route or contract.model_route


def _repair_type_for_errors(errors: list[str]) -> str:
    format_markers = (
        "JSON parse error",
        "stage output must be a JSON object",
        "must be a JSON object",
        "must include accepted_concepts",
        "must include candidate_assignments",
    )
    if all(any(marker in error for marker in format_markers) for error in errors):
        return "format_repair"
    return "contextual_repair"


def _repair_instruction(repair_type: str) -> str:
    if repair_type == "format_repair":
        return (
            "Fix JSON syntax or contract shape only. Preserve all concepts, labels, descriptions, "
            "coverage criteria, candidate assignments, pruning decisions, and learning meaning from the failed output. "
            "Do not add, remove, merge, split, or reinterpret concepts."
        )
    return (
        "Fix only the reported contract/context errors using the provided inputs and failed output. "
        "Preserve concepts and learning meaning wherever possible. Change semantic decisions only when necessary "
        "to resolve unsupported references, missing required assignments, or impossible candidate links."
    )
