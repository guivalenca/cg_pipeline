from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


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


@dataclass(frozen=True)
class ModelRouter:
    routes: dict[str, ModelRoute]

    @classmethod
    def default(cls) -> "ModelRouter":
        return cls(
            routes={
                FLASH_ROUTE_ALIAS: ModelRoute(
                    alias=FLASH_ROUTE_ALIAS,
                    provider="deepseek",
                    model="deepseek-v4-flash",
                    thinking_enabled=False,
                    reasoning_effort=None,
                ),
                PRO_ROUTE_ALIAS: ModelRoute(
                    alias=PRO_ROUTE_ALIAS,
                    provider="deepseek",
                    model="deepseek-v4-pro",
                    thinking_enabled=False,
                    reasoning_effort=None,
                ),
                PRO_THINKING_ROUTE_ALIAS: ModelRoute(
                    alias=PRO_THINKING_ROUTE_ALIAS,
                    provider="deepseek",
                    model="deepseek-v4-pro",
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


@dataclass(frozen=True)
class StageResult:
    stage_name: str
    artifact_path: Path
    raw_output_paths: list[Path]
    repaired: bool


class StageBlockedError(RuntimeError):
    """A stage failed its contract and downstream stages must not consume it."""


class StageRunner:
    def __init__(self, *, router: ModelRouter, model_call: ModelCall):
        self.router = router
        self.model_call = model_call

    def run(self, contract: StageContract, *, run_dir: Path) -> StageResult:
        route = self.router.resolve(contract.model_route)
        inputs = self._load_required_inputs(contract, run_dir)
        raw_output_paths: list[Path] = []

        started_at = time.monotonic()
        self._write_progress_event(
            run_dir,
            contract.name,
            "model_call_start",
            attempt=1,
            route=route.alias,
            input_keys=sorted(inputs),
            input_bytes=_json_size_bytes(inputs),
        )
        try:
            raw = self.model_call(route=route, stage_name=contract.name, inputs=inputs, repair_context=None)
        except Exception as exc:
            self._write_progress_event(
                run_dir,
                contract.name,
                "model_call_error",
                attempt=1,
                route=route.alias,
                elapsed_seconds=round(time.monotonic() - started_at, 3),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise
        self._write_progress_event(
            run_dir,
            contract.name,
            "model_call_returned",
            attempt=1,
            route=route.alias,
            elapsed_seconds=round(time.monotonic() - started_at, 3),
            output_bytes=len(raw.encode("utf-8")),
        )
        raw_output_paths.append(self._write_raw_output(run_dir, contract.name, "attempt_1.txt", raw))
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
            repair_started_at = time.monotonic()
            self._write_progress_event(
                run_dir,
                contract.name,
                "model_call_start",
                attempt=2,
                route=repair_route.alias,
                repair_type=repair_type,
                input_keys=sorted(inputs),
                input_bytes=_json_size_bytes(inputs),
            )
            try:
                repaired_raw = self.model_call(
                    route=repair_route,
                    stage_name=contract.name,
                    inputs=inputs,
                    repair_context=repair_context,
                )
            except Exception as exc:
                self._write_progress_event(
                    run_dir,
                    contract.name,
                    "model_call_error",
                    attempt=2,
                    route=repair_route.alias,
                    elapsed_seconds=round(time.monotonic() - repair_started_at, 3),
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                raise
            self._write_progress_event(
                run_dir,
                contract.name,
                "model_call_returned",
                attempt=2,
                route=repair_route.alias,
                elapsed_seconds=round(time.monotonic() - repair_started_at, 3),
                output_bytes=len(repaired_raw.encode("utf-8")),
            )
            raw_output_paths.append(
                self._write_raw_output(run_dir, contract.name, f"attempt_2_{repair_type}.txt", repaired_raw)
            )
            artifact, errors = self._normalize_and_validate(repaired_raw, contract, inputs)
            if not errors:
                return self._write_artifact(contract, run_dir, artifact, raw_output_paths, repaired=True)

        if errors:
            joined = "; ".join(errors)
            raise StageBlockedError(f"Stage '{contract.name}' failed Stage Contract: {joined}")

        return self._write_artifact(contract, run_dir, artifact, raw_output_paths, repaired=False)

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
