from __future__ import annotations

import concurrent.futures
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from concept_graph_creation.runtime.stage_runner import (
    ModelCall,
    ModelRouter,
    PRO_ROUTE_ALIAS,
    StageContract,
    StageResult,
    StageRunner,
)


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
    "source_local_connector_candidates",
    "cross_source_connector_candidates",
    "source_body",
    "source_body_path",
    "source_body_sha256",
}


@dataclass(frozen=True)
class _MetadataOnlyTask:
    order: int
    stage_dir: Path
    contract: StageContract


def run_metadata_only_extraction_phase(
    *,
    run_dir: Path,
    model_call: ModelCall,
    model_route: str = PRO_ROUTE_ALIAS,
    router: ModelRouter | None = None,
    prompt_path: Path | None = None,
    concurrency: int = 10,
) -> dict[str, Any]:
    prompt_path = prompt_path or Path(__file__).resolve().parents[3] / "prompts" / "metadata_only_extraction.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    source_ledger = json.loads((run_dir / "source_ledger.json").read_text(encoding="utf-8"))
    lessons_by_id = {lesson["lesson_id"]: lesson for lesson in source_ledger.get("lessons", [])}
    runner = StageRunner(router=router or ModelRouter.default(), model_call=model_call)

    skipped: list[dict[str, str]] = []
    result_by_order: dict[int, StageResult] = {}
    reused_count = 0
    tasks: list[_MetadataOnlyTask] = []
    candidate_self_studies = [
        self_study
        for self_study in source_ledger.get("self_studies", [])
        if self_study.get("source_body_status") == "unavailable_source_body"
    ]

    for order, self_study in enumerate(candidate_self_studies):
        self_study_id = str(self_study["self_study_id"])
        lesson_id = str(self_study.get("lesson_id") or "")
        lesson = lessons_by_id.get(lesson_id)
        if not lesson:
            skipped.append({"self_study_id": self_study_id, "reason": "missing_lesson"})
            continue

        self_study_dir = run_dir / "lessons" / lesson_id / "self_studies" / self_study_id
        self_study_dir.mkdir(parents=True, exist_ok=True)
        model_input = _build_model_input(
            prompt_path=prompt_path,
            prompt=prompt,
            source_ledger=source_ledger,
            lesson=lesson,
            self_study=self_study,
        )
        (self_study_dir / "metadata_only_extraction_input.json").write_text(
            json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        contract = StageContract(
            name="metadata_only_extraction",
            required_inputs=["metadata_only_extraction_input.json"],
            output_artifact="metadata_only_extraction.json",
            model_route=model_route,
            validator=validate_metadata_only_extraction,
            normalizer=_normalize_model_output,
        )
        existing_result = _existing_valid_result(
            self_study_dir=self_study_dir,
            contract=contract,
            self_study_id=self_study_id,
            lesson_id=lesson_id,
            model_route=model_route,
        )
        if existing_result:
            reused_count += 1
            result_by_order[order] = existing_result
            continue
        tasks.append(_MetadataOnlyTask(order=order, stage_dir=self_study_dir, contract=contract))

    result_by_order.update(_run_tasks_with_queue(tasks, runner=runner, concurrency=concurrency))
    results = [result_by_order[order] for order in sorted(result_by_order)]
    summary = {
        "metadata_only_candidate_count": len(candidate_self_studies),
        "extracted_self_study_count": len(results),
        "reused_extraction_count": reused_count,
        "skipped_count": len(skipped),
    }
    summary_path = run_dir / "metadata_only_extraction_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "artifact_type": "metadata_only_extraction_summary",
                "schema_version": "metadata_only_extraction_summary.v0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "artifacts": [str(result.artifact_path.relative_to(run_dir)) for result in results],
                "skipped": skipped,
                "model_route": model_route,
                "concurrency": {"initial": concurrency, "final": concurrency},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "summary": summary,
        "artifact_paths": [result.artifact_path for result in results],
        "skipped": skipped,
        "model_route": model_route,
        "concurrency": {"initial": concurrency, "final": concurrency},
    }


def validate_metadata_only_extraction(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("artifact_type") != "metadata_only_extraction":
        errors.append("metadata_only_extraction.artifact_type must be 'metadata_only_extraction'")
    self_study_id = str(artifact.get("self_study_id") or "")
    if not self_study_id:
        errors.append("metadata_only_extraction.self_study_id is required")
    if not artifact.get("lesson_id"):
        errors.append("metadata_only_extraction.lesson_id is required")
    _append_forbidden_key_errors(errors, "metadata_only_extraction", artifact)

    candidates = artifact.get("candidate_concepts")
    if not isinstance(candidates, list):
        errors.append("metadata_only_extraction.candidate_concepts must be a list")
        return errors
    if not candidates and artifact.get("excluded") is not True:
        errors.append("metadata_only_extraction.candidate_concepts must not be empty unless excluded is true")
    if artifact.get("excluded") is True and not str(artifact.get("exclusion_reason") or "").strip():
        errors.append("metadata_only_extraction.exclusion_reason is required when excluded is true")

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
        elif self_study_id and not candidate_id.startswith(f"metadata-candidate-{self_study_id}-"):
            errors.append(f"{location}.candidate_id must be scoped to self-study {self_study_id}")
        elif candidate_id in candidate_ids:
            errors.append(f"{location}.candidate_id is duplicated")
        candidate_ids.add(candidate_id)
        for field in ("label", "description"):
            if not str(candidate.get(field) or "").strip():
                errors.append(f"{location}.{field} is required")
        if not _non_empty_string_list(candidate.get("coverage_criteria")):
            errors.append(f"{location}.coverage_criteria must contain at least one string")
        if candidate.get("evidence_type") != "workbook_metadata":
            errors.append(f"{location}.evidence_type must be 'workbook_metadata'")
        if not _valid_anchors(candidate.get("metadata_anchors")):
            errors.append(f"{location}.metadata_anchors must contain at least one anchor with kind and locator")
        reason = candidate.get("extraction_reason")
        if not isinstance(reason, dict):
            errors.append(f"{location}.extraction_reason must be an object")
        else:
            if not str(reason.get("metadata_grounded_rationale") or "").strip():
                errors.append(f"{location}.extraction_reason.metadata_grounded_rationale is required")
            if not str(reason.get("granularity_rationale") or "").strip():
                errors.append(f"{location}.extraction_reason.granularity_rationale is required")

    summary = artifact.get("summary") or {}
    if summary.get("candidate_count") != len(candidates):
        errors.append("metadata_only_extraction.summary.candidate_count does not match candidate_concepts length")
    return errors


def _run_tasks_with_queue(
    tasks: list[_MetadataOnlyTask],
    *,
    runner: StageRunner,
    concurrency: int,
) -> dict[int, StageResult]:
    if not tasks:
        return {}
    worker_count = max(1, concurrency)
    result_by_order: dict[int, StageResult] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_task = {executor.submit(runner.run, task.contract, run_dir=task.stage_dir): task for task in tasks}
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            result_by_order[task.order] = future.result()
    return result_by_order


def _build_model_input(
    *,
    prompt_path: Path,
    prompt: str,
    source_ledger: dict[str, Any],
    lesson: dict[str, Any],
    self_study: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "metadata_only_extraction_input",
        "schema_version": "metadata_only_extraction_input.v0",
        "source_artifact": "source_ledger.json",
        "prompt_path": str(prompt_path),
        "prompt": prompt,
        "course_id": source_ledger.get("course_id"),
        "module_id": source_ledger.get("module_id"),
        "subject_id": source_ledger.get("subject_id"),
        "lesson": lesson,
        "self_study": {
            "self_study_id": str(self_study["self_study_id"]),
            "lesson_id": self_study.get("lesson_id"),
            "source_body_status": self_study.get("source_body_status"),
            "workbook_metadata": self_study.get("workbook_metadata") or {},
            "source_availability_failures": (self_study.get("source_body") or {}).get("availability_failures") or [],
            "ledger_warnings": self_study.get("ledger_warnings") or [],
        },
        "web_access_policy": {
            "web_search_allowed": False,
            "instruction": "Do not open URLs or use web search. Use Workbook Metadata only.",
        },
    }


def _normalize_model_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("metadata-only extraction model output must be a JSON object")
    if payload.get("artifact_type") == "metadata_only_extraction":
        return payload

    model_input = inputs["metadata_only_extraction_input.json"]
    candidates = payload.get("candidate_concepts")
    if not isinstance(candidates, list):
        raise ValueError("model output must include candidate_concepts")
    artifact = {
        "artifact_type": "metadata_only_extraction",
        "schema_version": "metadata_only_extraction.v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_artifact": "source_ledger.json",
        "model_route": payload.get("model_route") or PRO_ROUTE_ALIAS,
        "lesson_id": model_input["lesson"]["lesson_id"],
        "self_study_id": str(model_input["self_study"]["self_study_id"]),
        "source_name": (model_input["self_study"].get("workbook_metadata") or {}).get("title"),
        "excluded": bool(payload.get("excluded", False)),
        "exclusion_reason": payload.get("exclusion_reason"),
        "candidate_concepts": candidates,
        "summary": {"candidate_count": len(candidates)},
    }
    return artifact


def _existing_valid_result(
    *,
    self_study_dir: Path,
    contract: StageContract,
    self_study_id: str,
    lesson_id: str,
    model_route: str,
) -> StageResult | None:
    artifact_path = self_study_dir / contract.output_artifact
    if not artifact_path.is_file():
        return None
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if validate_metadata_only_extraction(artifact):
        return None
    if artifact.get("self_study_id") != self_study_id:
        return None
    if artifact.get("lesson_id") != lesson_id:
        return None
    if artifact.get("model_route") != model_route:
        return None
    return StageResult(
        stage_name=contract.name,
        artifact_path=artifact_path,
        raw_output_paths=[],
        repaired=False,
    )


def _append_forbidden_key_errors(errors: list[str], location: str, value: dict[str, Any]) -> None:
    forbidden = sorted(key for key in value if key in FORBIDDEN_OUTPUT_KEYS)
    for key in forbidden:
        errors.append(f"{location}.{key} is forbidden in Metadata-only Extraction")


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
