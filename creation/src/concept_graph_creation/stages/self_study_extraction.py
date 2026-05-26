from __future__ import annotations

import concurrent.futures
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from concept_graph_creation.runtime.stage_runner import (
    ModelCall,
    ModelRouter,
    PRO_THINKING_ROUTE_ALIAS,
    StageBlockedError,
    StageContract,
    StageResult,
    StageRunner,
)


ALLOWED_SOURCE_ROLES = {
    "introducing",
    "explaining",
    "demonstrating",
    "implementing",
    "practicing",
    "referencing",
    "warning",
    "incidental_mention",
}
SOURCE_ROLE_ALIASES = {
    "concluding": ("explaining",),
    "conclusion": ("explaining",),
    "summarizing": ("explaining",),
    "summary": ("explaining",),
    "motivating": ("introducing",),
    "motivation": ("introducing",),
    "defining": ("explaining",),
    "describing": ("explaining",),
    "contextualizing": ("explaining",),
    "comparing": ("explaining",),
    "mentioning": ("incidental_mention",),
    "example": ("demonstrating",),
    "examples": ("demonstrating",),
    "exemplifying": ("demonstrating",),
    "applying": ("demonstrating",),
    "calculating": ("demonstrating",),
    "classifying": ("demonstrating",),
    "deriving": ("demonstrating",),
    "solving": ("demonstrating",),
    "advising": ("explaining",),
    "recommending": ("explaining",),
    "suggesting": ("explaining",),
    "reference": ("referencing",),
    "references": ("referencing",),
}

FORBIDDEN_OUTPUT_KEYS = {
    "concept_id",
    "concept_ids",
    "final_concept_id",
    "final_concept_ids",
    "concepts",
    "dependencies",
    "dependency_edges",
    "lesson_order",
    "bridge_concepts",
    "cross_source_connector_candidates",
}

PRO_THINKING_PASS_ID = "pro-thinking"
CONCURRENCY_LADDER = (60, 50, 40, 30, 25, 20, 16, 14, 8, 6, 4, 2)


def run_self_study_extraction_phase(
    *,
    cg_pipeline_root: Path,
    run_dir: Path,
    model_call: ModelCall,
    router: ModelRouter | None = None,
    prompt_path: Path | None = None,
    initial_concurrency: int = 60,
    pressure_backoff_seconds: float = 5.0,
    pressure_retry_limit: int = 3,
) -> dict[str, Any]:
    prompt_path = prompt_path or Path(__file__).resolve().parents[3] / "prompts" / "self_study_extraction.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    source_ledger = json.loads((run_dir / "source_ledger.json").read_text(encoding="utf-8"))
    lessons_by_id = {lesson["lesson_id"]: lesson for lesson in source_ledger.get("lessons", [])}

    tasks: list[_SelfStudyExtractionTask] = []
    usable_self_studies: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for order, self_study in enumerate(source_ledger.get("self_studies", [])):
        if self_study.get("source_body_status") != "usable_source_body":
            skipped.append(
                {
                    "self_study_id": str(self_study.get("self_study_id")),
                    "reason": str(self_study.get("source_body_status")),
                }
            )
            continue

        lesson_id = self_study["lesson_id"]
        lesson = lessons_by_id.get(lesson_id)
        if not lesson:
            raise StageBlockedError(f"Self-study {self_study.get('self_study_id')} references missing lesson {lesson_id}")
        usable_self_studies.append(self_study)
        self_study_dir = run_dir / "lessons" / lesson_id / "self_studies" / str(self_study["self_study_id"])
        stage_dir = self_study_dir / "extraction_passes" / PRO_THINKING_PASS_ID
        model_input = _build_model_input(
            cg_pipeline_root=cg_pipeline_root,
            prompt_path=prompt_path,
            prompt=prompt,
            source_ledger=source_ledger,
            lesson=lesson,
            self_study=self_study,
        )
        stage_dir.mkdir(parents=True, exist_ok=True)
        (stage_dir / "self_study_extraction_input.json").write_text(
            json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        contract = StageContract(
            name="self_study_extraction",
            required_inputs=["self_study_extraction_input.json"],
            output_artifact="self_study_extraction.json",
            model_route=PRO_THINKING_ROUTE_ALIAS,
            validator=validate_self_study_extraction,
            normalizer=_normalize_model_output,
        )
        tasks.append(
            _SelfStudyExtractionTask(
                order=order,
                self_study_id=str(self_study["self_study_id"]),
                lesson_id=lesson_id,
                self_study_dir=self_study_dir,
                stage_dir=stage_dir,
                contract=contract,
            )
        )

    runner = StageRunner(router=router or ModelRouter.default(), model_call=model_call)
    reusable_results: dict[int, StageResult] = {}
    runnable_tasks: list[_SelfStudyExtractionTask] = []
    for task in tasks:
        existing_result = _existing_valid_result(task)
        if existing_result:
            reusable_results[task.order] = existing_result
        else:
            runnable_tasks.append(task)
    result_by_order, concurrency_report = _run_tasks_with_adaptive_concurrency(
        runnable_tasks,
        runner=runner,
        initial_concurrency=initial_concurrency,
        pressure_backoff_seconds=pressure_backoff_seconds,
        pressure_retry_limit=pressure_retry_limit,
    )
    result_by_order.update(reusable_results)
    results = [result_by_order[task.order] for task in tasks]
    set_artifact_paths = _write_extraction_set_artifacts(run_dir=run_dir, tasks=tasks, results=results)

    summary = {
        "usable_self_study_count": len(usable_self_studies),
        "extracted_self_study_count": len(set_artifact_paths),
        "extraction_pass_count": len(results),
        "reused_extraction_pass_count": len(reusable_results),
        "skipped_count": len(skipped),
    }
    summary_path = run_dir / "self_study_extraction_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "artifact_type": "self_study_extraction_summary",
                "schema_version": "self_study_extraction_summary.v0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "set_artifacts": [str(path.relative_to(run_dir)) for path in set_artifact_paths],
                "pass_artifacts": [str(result.artifact_path.relative_to(run_dir)) for result in results],
                "skipped": skipped,
                "concurrency": concurrency_report,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "summary": summary,
        "artifact_paths": set_artifact_paths,
        "pass_artifact_paths": [result.artifact_path for result in results],
        "skipped": skipped,
        "concurrency": concurrency_report,
    }


@dataclass(frozen=True)
class _SelfStudyExtractionTask:
    order: int
    self_study_id: str
    lesson_id: str
    self_study_dir: Path
    stage_dir: Path
    contract: StageContract


def _existing_valid_result(task: _SelfStudyExtractionTask) -> StageResult | None:
    artifact_path = task.stage_dir / task.contract.output_artifact
    if not artifact_path.is_file():
        return None
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if validate_self_study_extraction(artifact):
        return None
    if artifact.get("self_study_id") != task.self_study_id:
        return None
    if artifact.get("lesson_id") != task.lesson_id:
        return None
    if artifact.get("model_route") != PRO_THINKING_ROUTE_ALIAS:
        return None
    return StageResult(
        stage_name=task.contract.name,
        artifact_path=artifact_path,
        raw_output_paths=[],
        repaired=False,
    )


def _run_tasks_with_adaptive_concurrency(
    tasks: list[_SelfStudyExtractionTask],
    *,
    runner: StageRunner,
    initial_concurrency: int,
    pressure_backoff_seconds: float,
    pressure_retry_limit: int,
) -> tuple[dict[int, StageResult], dict[str, Any]]:
    current_concurrency = _nearest_supported_concurrency(initial_concurrency)
    pressure_attempts: dict[str, int] = {}
    pressure_error_count = 0
    reductions: list[dict[str, Any]] = []
    pending = list(tasks)
    result_by_order: dict[int, StageResult] = {}
    active: dict[concurrent.futures.Future[StageResult], _SelfStudyExtractionTask] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=_nearest_supported_concurrency(initial_concurrency)) as executor:
        while pending or active:
            while pending and len(active) < current_concurrency:
                task = pending.pop(0)
                active[executor.submit(runner.run, task.contract, run_dir=task.stage_dir)] = task
            if not active:
                continue
            done, _not_done = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                task = active.pop(future)
                try:
                    result_by_order[task.order] = future.result()
                except StageBlockedError as exc:
                    pressure_reason = _provider_pressure_reason(exc)
                    if not pressure_reason:
                        raise
                    pressure_error_count += 1
                    pressure_key = task.self_study_id
                    pressure_attempts[pressure_key] = pressure_attempts.get(pressure_key, 0) + 1
                    if pressure_attempts[pressure_key] > pressure_retry_limit:
                        raise StageBlockedError(
                            f"Self-study {task.self_study_id} Pro Thinking pass exceeded provider pressure retry "
                            f"limit after {pressure_retry_limit} retries: {exc}"
                        ) from exc
                    previous_concurrency = current_concurrency
                    current_concurrency = _reduced_concurrency(current_concurrency)
                    if current_concurrency < previous_concurrency:
                        reductions.append(
                            {
                                "from": previous_concurrency,
                                "to": current_concurrency,
                                "reason": pressure_reason,
                            }
                        )
                    if pressure_backoff_seconds:
                        time.sleep(pressure_backoff_seconds)
                    pending.insert(0, task)

    return result_by_order, {
        "initial": _nearest_supported_concurrency(initial_concurrency),
        "final": current_concurrency,
        "pressure_error_count": pressure_error_count,
        "reductions": reductions,
    }


def _write_extraction_set_artifacts(
    *,
    run_dir: Path,
    tasks: list[_SelfStudyExtractionTask],
    results: list[StageResult],
) -> list[Path]:
    result_by_order = {task.order: result for task, result in zip(tasks, results)}
    tasks_by_self_study: dict[tuple[str, str], list[_SelfStudyExtractionTask]] = {}
    for task in tasks:
        tasks_by_self_study.setdefault((task.lesson_id, task.self_study_id), []).append(task)

    set_artifact_paths: list[Path] = []
    for (_lesson_id, _self_study_id), self_study_tasks in sorted(
        tasks_by_self_study.items(),
        key=lambda item: min(task.order for task in item[1]),
    ):
        first_task = min(self_study_tasks, key=lambda task: task.order)
        extraction_passes = []
        for task in sorted(self_study_tasks, key=lambda item: item.order):
            result = result_by_order[task.order]
            pass_artifact = json.loads(result.artifact_path.read_text(encoding="utf-8"))
            extraction_passes.append(
                {
                    "pass_id": PRO_THINKING_PASS_ID,
                    "route_alias": PRO_THINKING_ROUTE_ALIAS,
                    "artifact_path": str(result.artifact_path.relative_to(run_dir)),
                    "candidate_count": pass_artifact.get("summary", {}).get("candidate_count"),
                    "source_local_connector_candidate_count": pass_artifact.get("summary", {}).get(
                        "source_local_connector_candidate_count"
                    ),
                }
            )
        set_artifact = {
            "artifact_type": "self_study_extraction_set",
            "schema_version": "self_study_extraction_set.v0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_artifact": "source_ledger.json",
            "lesson_id": first_task.lesson_id,
            "self_study_id": first_task.self_study_id,
            "summary": {
                "extraction_pass_count": len(extraction_passes),
                "candidate_count": sum(item.get("candidate_count") or 0 for item in extraction_passes),
                "source_local_connector_candidate_count": sum(
                    item.get("source_local_connector_candidate_count") or 0 for item in extraction_passes
                ),
            },
            "extraction_passes": extraction_passes,
        }
        output_path = first_task.self_study_dir / "self_study_extraction_set.json"
        output_path.write_text(json.dumps(set_artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        set_artifact_paths.append(output_path)
    return set_artifact_paths


def _nearest_supported_concurrency(value: int) -> int:
    for concurrency in CONCURRENCY_LADDER:
        if value >= concurrency:
            return concurrency
    return CONCURRENCY_LADDER[-1]


def _reduced_concurrency(value: int) -> int:
    for concurrency in CONCURRENCY_LADDER:
        if concurrency < value:
            return concurrency
    return CONCURRENCY_LADDER[-1]


def _provider_pressure_reason(exc: StageBlockedError) -> str | None:
    message = str(exc)
    if "DeepSeek HTTP 403" in message:
        return "DeepSeek HTTP 403"
    if "DeepSeek HTTP 429" in message:
        return "DeepSeek HTTP 429"
    if "DeepSeek HTTP 503" in message:
        return "DeepSeek HTTP 503"
    if "DeepSeek request timed out" in message:
        return "DeepSeek request timed out"
    if "DeepSeek request failed" in message:
        return "DeepSeek request failed"
    if "DeepSeek returned an empty message" in message:
        return "DeepSeek returned an empty message"
    return None


def validate_self_study_extraction(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("artifact_type") != "self_study_extraction":
        errors.append("self_study_extraction.artifact_type must be 'self_study_extraction'")

    self_study_id = str(artifact.get("self_study_id") or "")
    if not self_study_id:
        errors.append("self_study_extraction.self_study_id is required")
    if not artifact.get("lesson_id"):
        errors.append("self_study_extraction.lesson_id is required")
    _append_forbidden_key_errors(errors, "self_study_extraction", artifact)

    candidates = artifact.get("candidate_concepts")
    if not isinstance(candidates, list) or not candidates:
        errors.append("self_study_extraction.candidate_concepts must not be empty")
        return errors

    candidate_ids: set[str] = set()
    for index, candidate in enumerate(candidates):
        location = f"candidate_concepts[{index}]"
        if not isinstance(candidate, dict):
            errors.append(f"{location} must be an object")
            continue
        _append_forbidden_key_errors(errors, location, candidate)
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id:
            errors.append(f"{location}.candidate_id is required")
        elif self_study_id and not candidate_id.startswith(f"candidate-{self_study_id}-"):
            errors.append(f"{location}.candidate_id must be scoped to self-study {self_study_id}")
        elif candidate_id in candidate_ids:
            errors.append(f"{location}.candidate_id is duplicated")
        candidate_ids.add(candidate_id)

        for field in ("label", "description"):
            if not str(candidate.get(field) or "").strip():
                errors.append(f"{location}.{field} is required")
        coverage = candidate.get("coverage_criteria")
        if not _non_empty_string_list(coverage):
            errors.append(f"{location}.coverage_criteria must contain at least one string")
        source_roles = candidate.get("source_roles")
        if not _non_empty_string_list(source_roles):
            errors.append(f"{location}.source_roles must contain at least one role")
        else:
            invalid_roles = sorted(set(source_roles) - ALLOWED_SOURCE_ROLES)
            if invalid_roles:
                errors.append(f"{location}.source_roles contains invalid roles: {', '.join(invalid_roles)}")
        reason = candidate.get("extraction_reason")
        if not isinstance(reason, dict):
            errors.append(f"{location}.extraction_reason must be an object")
        else:
            if not str(reason.get("source_grounded_rationale") or "").strip():
                errors.append(f"{location}.extraction_reason.source_grounded_rationale is required")
            if not str(reason.get("granularity_rationale") or "").strip():
                errors.append(f"{location}.extraction_reason.granularity_rationale is required")
        if not _valid_anchors(candidate.get("source_anchors")):
            errors.append(f"{location}.source_anchors must contain at least one anchor with kind and locator")
        if candidate.get("evidence_type") != "source_body":
            errors.append(f"{location}.evidence_type must be 'source_body'")

    connectors = artifact.get("source_local_connector_candidates")
    if connectors is None:
        errors.append("self_study_extraction.source_local_connector_candidates is required")
    elif not isinstance(connectors, list):
        errors.append("self_study_extraction.source_local_connector_candidates must be a list")
    else:
        for index, connector in enumerate(connectors):
            location = f"source_local_connector_candidates[{index}]"
            if not isinstance(connector, dict):
                errors.append(f"{location} must be an object")
                continue
            _append_forbidden_key_errors(errors, location, connector)
            for field in ("from_candidate_id", "to_candidate_id", "reason"):
                if not str(connector.get(field) or "").strip():
                    errors.append(f"{location}.{field} is required")
            for field in ("from_candidate_id", "to_candidate_id"):
                candidate_id = str(connector.get(field) or "")
                if candidate_id and candidate_id not in candidate_ids:
                    errors.append(f"{location}.{field} must reference a candidate from this self-study")
            if not _valid_anchors(connector.get("source_anchors")):
                errors.append(f"{location}.source_anchors must contain at least one anchor with kind and locator")

    summary = artifact.get("summary") or {}
    if summary.get("candidate_count") != len(candidates):
        errors.append("self_study_extraction.summary.candidate_count does not match candidate_concepts length")
    if summary.get("source_local_connector_candidate_count") != len(artifact.get("source_local_connector_candidates") or []):
        errors.append(
            "self_study_extraction.summary.source_local_connector_candidate_count does not match connectors length"
        )
    return errors


def _build_model_input(
    *,
    cg_pipeline_root: Path,
    prompt_path: Path,
    prompt: str,
    source_ledger: dict[str, Any],
    lesson: dict[str, Any],
    self_study: dict[str, Any],
) -> dict[str, Any]:
    source_body = self_study.get("source_body") or {}
    source_body_path = cg_pipeline_root / source_body["path"]
    markdown = source_body_path.read_text(encoding="utf-8")
    allowed_image_urls = _extract_markdown_image_urls(markdown)
    return {
        "artifact_type": "self_study_extraction_input",
        "schema_version": "self_study_extraction_input.v0",
        "source_artifact": "source_ledger.json",
        "prompt_path": str(prompt_path),
        "prompt": prompt,
        "course_id": source_ledger.get("course_id"),
        "module_id": source_ledger.get("module_id"),
        "subject_id": source_ledger.get("subject_id"),
        "extraction_pass": {
            "pass_id": PRO_THINKING_PASS_ID,
            "pass_index": 1,
            "route_alias": PRO_THINKING_ROUTE_ALIAS,
            "instruction": "Use the shared Self-study Extraction prompt with the Pro Thinking route.",
        },
        "lesson": lesson,
        "self_study": self_study,
        "source_body": {
            "path": source_body.get("path"),
            "sha256": source_body.get("sha256"),
            "word_count": source_body.get("word_count"),
            "source_markdown": source_body.get("source_markdown"),
            "markdown": markdown,
        },
        "web_access_policy": {
            "web_search_allowed": False,
            "allowed_image_urls": allowed_image_urls,
            "instruction": "You may inspect only these Source Body linked image URLs. Do not search or open unrelated URLs.",
        },
    }


def _normalize_model_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("self-study extraction model output must be a JSON object")
    if payload.get("artifact_type") == "self_study_extraction":
        payload["model_route"] = PRO_THINKING_ROUTE_ALIAS
        _canonicalize_candidate_source_roles(payload)
        return payload

    model_input = inputs["self_study_extraction_input.json"]
    candidates = payload.get("candidate_concepts")
    if not isinstance(candidates, list):
        raise ValueError("model output must include candidate_concepts")
    candidates = [_normalize_candidate(candidate) for candidate in candidates]
    connectors = payload.get("source_local_connector_candidates") or []
    if not isinstance(connectors, list):
        raise ValueError("source_local_connector_candidates must be a list")

    self_study = model_input["self_study"]
    source_body = model_input["source_body"]
    artifact = {
        "artifact_type": "self_study_extraction",
        "schema_version": "self_study_extraction.v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_artifact": "source_ledger.json",
        "model_route": PRO_THINKING_ROUTE_ALIAS,
        "lesson_id": model_input["lesson"]["lesson_id"],
        "self_study_id": str(self_study["self_study_id"]),
        "source_body_path": source_body.get("path"),
        "source_body_sha256": source_body.get("sha256"),
        "source_name": (self_study.get("workbook_metadata") or {}).get("title"),
        "source_year": payload.get("source_year"),
        "web_access_policy": model_input["web_access_policy"],
        "candidate_concepts": candidates,
        "source_local_connector_candidates": connectors,
        "summary": {
            "candidate_count": len(candidates),
            "source_local_connector_candidate_count": len(connectors),
        },
    }
    return artifact


def _normalize_candidate(candidate: Any) -> Any:
    if not isinstance(candidate, dict):
        return candidate
    normalized = dict(candidate)
    _canonicalize_source_roles(normalized)
    return normalized


def _canonicalize_candidate_source_roles(artifact: dict[str, Any]) -> None:
    candidates = artifact.get("candidate_concepts")
    if not isinstance(candidates, list):
        return
    for candidate in candidates:
        if isinstance(candidate, dict):
            _canonicalize_source_roles(candidate)


def _canonicalize_source_roles(candidate: dict[str, Any]) -> None:
    source_roles = candidate.get("source_roles")
    if not isinstance(source_roles, list):
        return

    canonical_roles: list[Any] = []
    for source_role in source_roles:
        if not isinstance(source_role, str):
            canonical_roles.append(source_role)
            continue
        normalized_role = _normalize_source_role_token(source_role)
        for canonical_role in SOURCE_ROLE_ALIASES.get(normalized_role, (normalized_role,)):
            if canonical_role not in canonical_roles:
                canonical_roles.append(canonical_role)
    candidate["source_roles"] = canonical_roles


def _normalize_source_role_token(source_role: str) -> str:
    return re.sub(r"[\s-]+", "_", source_role.strip().lower())


def _extract_markdown_image_urls(markdown: str) -> list[str]:
    urls: list[str] = []
    for match in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", markdown):
        url = match.group(1).strip()
        if url.startswith(("http://", "https://")) and url not in urls:
            urls.append(url)
    for match in re.finditer(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", markdown, flags=re.IGNORECASE):
        url = match.group(1).strip()
        if url.startswith(("http://", "https://")) and url not in urls:
            urls.append(url)
    return urls


def _append_forbidden_key_errors(errors: list[str], location: str, value: dict[str, Any]) -> None:
    forbidden = sorted(key for key in value if key in FORBIDDEN_OUTPUT_KEYS)
    for key in forbidden:
        errors.append(f"{location}.{key} is forbidden in Self-study Extraction")


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value)


def _valid_anchors(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for anchor in value:
        if not isinstance(anchor, dict):
            return False
        if not str(anchor.get("kind") or "").strip() or not str(anchor.get("locator") or "").strip():
            return False
    return True
