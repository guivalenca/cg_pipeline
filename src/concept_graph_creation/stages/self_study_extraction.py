from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from concept_graph_creation.runtime.generation import (
    ledger_fingerprint,
    matches_ledger_fingerprint,
    stamp_ledger_fingerprint,
)
from concept_graph_creation.runtime.provider_errors import transient_provider_error_reason
from concept_graph_creation.runtime.stage_runner import (
    ModelCall,
    ModelRouter,
    PRO_THINKING_ROUTE_ALIAS,
    StageBlockedError,
    StageContract,
    StageResult,
    StageRunner,
)
from concept_graph_creation.stages.source_ledger import resolve_source_body_path


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
COVERAGE_DIAGNOSTICS_SCHEMA_VERSION = "self_study_coverage_diagnostics.v1"
DENSE_SOURCE_MIN_WORD_COUNT = 1200
DENSE_SOURCE_MIN_DURATION_SECONDS = 600.0
DENSE_SOURCE_MIN_HEADING_COUNT = 6
DENSE_SOURCE_MIN_CANDIDATE_COUNT = 3
DENSE_SOURCE_MIN_DISTINCT_ANCHOR_COUNT = 3


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
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    prompt_path = prompt_path or Path(__file__).resolve().parents[3] / "prompts" / "self_study_extraction.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    source_ledger = json.loads((run_dir / "source_ledger.json").read_text(encoding="utf-8"))
    current_ledger_fingerprint = ledger_fingerprint(source_ledger)
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
            run_dir=run_dir,
            prompt_path=prompt_path,
            prompt=prompt,
            source_ledger=source_ledger,
            lesson=lesson,
            self_study=self_study,
            current_ledger_fingerprint=current_ledger_fingerprint,
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
            validator=lambda artifact, model_input=model_input: _validate_self_study_extraction_for_input(
                artifact,
                model_input=model_input,
            ),
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
                model_input=model_input,
            )
        )

    runner = StageRunner(router=router or ModelRouter.default(), model_call=model_call)
    reusable_results: dict[int, StageResult] = {}
    runnable_tasks: list[_SelfStudyExtractionTask] = []
    completed_count = 0
    _emit_self_study_progress(progress_callback, current=completed_count, total=len(tasks))
    for task in tasks:
        existing_result = _existing_valid_result(task, current_ledger_fingerprint=current_ledger_fingerprint)
        if existing_result:
            reusable_results[task.order] = existing_result
            completed_count += 1
            _emit_self_study_progress(
                progress_callback,
                current=completed_count,
                total=len(tasks),
                task=task,
                reused=True,
            )
        else:
            runnable_tasks.append(task)
    result_by_order, concurrency_report = _run_tasks_with_adaptive_concurrency(
        runnable_tasks,
        runner=runner,
        initial_concurrency=initial_concurrency,
        pressure_backoff_seconds=pressure_backoff_seconds,
        pressure_retry_limit=pressure_retry_limit,
        completed_count=completed_count,
        total_count=len(tasks),
        progress_callback=progress_callback,
    )
    result_by_order.update(reusable_results)
    results = [result_by_order[task.order] for task in tasks]
    set_artifact_paths = _write_extraction_set_artifacts(
        run_dir=run_dir,
        tasks=tasks,
        results=results,
        current_ledger_fingerprint=current_ledger_fingerprint,
    )

    summary = {
        "usable_self_study_count": len(usable_self_studies),
        "extracted_self_study_count": len(set_artifact_paths),
        "extraction_pass_count": len(results),
        "reused_extraction_pass_count": len(reusable_results),
        "skipped_count": len(skipped),
    }
    coverage = _summarize_extraction_coverage(results)
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
                "coverage": coverage,
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
        "coverage": coverage,
    }


@dataclass(frozen=True)
class _SelfStudyExtractionTask:
    order: int
    self_study_id: str
    lesson_id: str
    self_study_dir: Path
    stage_dir: Path
    contract: StageContract
    model_input: dict[str, Any]


def _existing_valid_result(
    task: _SelfStudyExtractionTask,
    *,
    current_ledger_fingerprint: str,
) -> StageResult | None:
    artifact_path = task.stage_dir / task.contract.output_artifact
    if not artifact_path.is_file():
        return None
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if _validate_self_study_extraction_for_input(artifact, model_input=task.model_input):
        return None
    if not matches_ledger_fingerprint(artifact, current_ledger_fingerprint):
        return None
    if artifact.get("self_study_id") != task.self_study_id:
        return None
    if artifact.get("lesson_id") != task.lesson_id:
        return None
    if artifact.get("model_route") != PRO_THINKING_ROUTE_ALIAS:
        return None
    _stamp_coverage_diagnostics(artifact, model_input=task.model_input)
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
    completed_count: int = 0,
    total_count: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[dict[int, StageResult], dict[str, Any]]:
    total_count = len(tasks) if total_count is None else total_count
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
                    completed_count += 1
                    _emit_self_study_progress(
                        progress_callback,
                        current=completed_count,
                        total=total_count,
                        task=task,
                        reused=False,
                    )
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


def _emit_self_study_progress(
    callback: Callable[[dict[str, Any]], None] | None,
    *,
    current: int,
    total: int,
    task: _SelfStudyExtractionTask | None = None,
    reused: bool = False,
) -> None:
    if callback is None:
        return
    details: dict[str, Any] = {"progress_unit": "fontes"}
    message = f"{current}/{total} fontes concluídas"
    if task is not None:
        details.update(
            {
                "completed_self_study_id": task.self_study_id,
                "reused": reused,
            }
        )
        message += f" · última: Self-study {task.self_study_id}"
    callback(
        {
            "current": current,
            "total": total,
            "message": message,
            "details": details,
        }
    )


def _write_extraction_set_artifacts(
    *,
    run_dir: Path,
    tasks: list[_SelfStudyExtractionTask],
    results: list[StageResult],
    current_ledger_fingerprint: str,
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
            coverage_diagnostics = (pass_artifact.get("summary") or {}).get("coverage_diagnostics") or {}
            extraction_passes.append(
                {
                    "pass_id": PRO_THINKING_PASS_ID,
                    "route_alias": PRO_THINKING_ROUTE_ALIAS,
                    "artifact_path": str(result.artifact_path.relative_to(run_dir)),
                    "candidate_count": pass_artifact.get("summary", {}).get("candidate_count"),
                    "source_local_connector_candidate_count": pass_artifact.get("summary", {}).get(
                        "source_local_connector_candidate_count"
                    ),
                    "repaired": result.repaired,
                    "coverage_status": coverage_diagnostics.get("status"),
                    "coverage_flags": coverage_diagnostics.get("flags") or [],
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
                "coverage_status": (
                    "repair_required"
                    if any(item.get("coverage_status") == "repair_required" for item in extraction_passes)
                    else "reliable"
                ),
                "repaired_pass_count": sum(1 for item in extraction_passes if item.get("repaired")),
            },
            "extraction_passes": extraction_passes,
        }
        stamp_ledger_fingerprint(set_artifact, current_ledger_fingerprint)
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
    return transient_provider_error_reason(exc)


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


def _validate_self_study_extraction_for_input(
    artifact: dict[str, Any],
    *,
    model_input: dict[str, Any],
) -> list[str]:
    errors = validate_self_study_extraction(artifact)
    expected_prompt_hash = str(model_input.get("prompt_sha256") or "")
    if not expected_prompt_hash:
        errors.append("self_study_extraction_input.prompt_sha256 is required")
    elif artifact.get("prompt_sha256") != expected_prompt_hash:
        errors.append("self_study_extraction.prompt_sha256 does not match the prompt file")
    diagnostics = _build_coverage_diagnostics(artifact, model_input=model_input)
    source_profile = diagnostics["source_profile"]
    evidence_profile = diagnostics["evidence_profile"]
    automatic_acceptance = diagnostics["automatic_acceptance"]
    if "dense_source_under_covered" in diagnostics["flags"]:
        errors.append(
            "self_study_extraction.coverage_diagnostics dense_source_under_covered: "
            f"the structured Source Body has {source_profile['word_count']} words, "
            f"{source_profile['heading_count']} headings, and "
            f"{evidence_profile['candidate_count']} Candidate Concepts; automatic acceptance requires at least "
            f"{automatic_acceptance['minimum_candidate_count']} distinct source-grounded candidates. "
            "Re-extract the teachable distinctions across the Source Body without inventing unsupported content."
        )
    if "dense_source_anchor_coverage_too_narrow" in diagnostics["flags"]:
        errors.append(
            "self_study_extraction.coverage_diagnostics dense_source_anchor_coverage_too_narrow: "
            f"the structured Source Body has {source_profile['heading_count']} headings but the candidates use only "
            f"{evidence_profile['distinct_anchor_count']} distinct Source Anchors; automatic acceptance requires at "
            f"least {automatic_acceptance['minimum_distinct_anchor_count']}. Re-check separate source sections and "
            "anchor every additional candidate to content actually present in the Source Body."
        )
    return errors


def _stamp_coverage_diagnostics(
    artifact: dict[str, Any],
    *,
    model_input: dict[str, Any],
) -> None:
    summary = artifact.get("summary")
    if not isinstance(summary, dict):
        summary = {}
        artifact["summary"] = summary
    summary["coverage_diagnostics"] = _build_coverage_diagnostics(
        artifact,
        model_input=model_input,
    )


def _build_coverage_diagnostics(
    artifact: dict[str, Any],
    *,
    model_input: dict[str, Any],
) -> dict[str, Any]:
    source_body = model_input.get("source_body") or {}
    coverage_profile = source_body.get("coverage_profile") or {}
    source_profile = {
        "word_count": int(coverage_profile.get("word_count") or 0),
        "character_count": int(coverage_profile.get("character_count") or 0),
        "heading_count": int(coverage_profile.get("heading_count") or 0),
        "timestamped_heading_count": int(coverage_profile.get("timestamped_heading_count") or 0),
        "duration_seconds": _optional_float(coverage_profile.get("duration_seconds")),
    }
    automatic_acceptance = coverage_profile.get("automatic_acceptance")
    if not isinstance(automatic_acceptance, dict):
        automatic_acceptance = _automatic_coverage_expectation(source_profile)

    candidates = artifact.get("candidate_concepts")
    if not isinstance(candidates, list):
        candidates = []
    anchor_locators = [
        str(anchor.get("locator") or "").strip()
        for candidate in candidates
        if isinstance(candidate, dict)
        for anchor in candidate.get("source_anchors") or []
        if isinstance(anchor, dict) and str(anchor.get("locator") or "").strip()
    ]
    normalized_anchor_locators = {
        normalized
        for locator in anchor_locators
        for normalized in [_normalize_locator(locator)]
        if normalized
    }
    heading_locators = [
        locator
        for locator in coverage_profile.get("heading_locators") or []
        if isinstance(locator, str) and locator.strip()
    ]
    matched_headings = {
        heading
        for heading in heading_locators
        if _locator_matches_any(heading, normalized_anchor_locators)
    }
    evidence_profile = {
        "candidate_count": len(candidates),
        "distinct_anchor_count": len(normalized_anchor_locators),
        "matched_heading_count": len(matched_headings),
    }
    flags: list[str] = []
    if automatic_acceptance.get("applies"):
        if len(candidates) < int(automatic_acceptance["minimum_candidate_count"]):
            flags.append("dense_source_under_covered")
        if len(normalized_anchor_locators) < int(automatic_acceptance["minimum_distinct_anchor_count"]):
            flags.append("dense_source_anchor_coverage_too_narrow")
    return {
        "schema_version": COVERAGE_DIAGNOSTICS_SCHEMA_VERSION,
        "status": "repair_required" if flags else "reliable",
        "flags": flags,
        "source_profile": source_profile,
        "evidence_profile": evidence_profile,
        "automatic_acceptance": automatic_acceptance,
    }


def _build_source_profile(markdown: str, *, declared_word_count: Any = None) -> dict[str, Any]:
    frontmatter, body = _split_frontmatter(markdown)
    measured_word_count = len(re.findall(r"(?u)\b[^\W_]+(?:[’'-][^\W_]+)*\b", body))
    word_count = _positive_int(declared_word_count)
    if word_count is None:
        word_count = _positive_int(frontmatter.get("word_count")) or measured_word_count
    character_count = _positive_int(frontmatter.get("char_count")) or len(body)
    headings = _markdown_heading_locators(markdown)
    timestamped_heading_count = sum(1 for heading in headings if _is_timestamped_heading(heading))
    return {
        "word_count": word_count,
        "character_count": character_count,
        "heading_count": len(headings),
        "timestamped_heading_count": timestamped_heading_count,
        "duration_seconds": _optional_float(frontmatter.get("duration_seconds")),
    }


def _automatic_coverage_expectation(source_profile: dict[str, Any]) -> dict[str, Any]:
    word_count = int(source_profile.get("word_count") or 0)
    heading_count = int(source_profile.get("heading_count") or 0)
    duration_seconds = _optional_float(source_profile.get("duration_seconds")) or 0.0
    applies = heading_count >= DENSE_SOURCE_MIN_HEADING_COUNT and (
        word_count >= DENSE_SOURCE_MIN_WORD_COUNT
        or duration_seconds >= DENSE_SOURCE_MIN_DURATION_SECONDS
    )
    signals: list[str] = []
    if word_count >= DENSE_SOURCE_MIN_WORD_COUNT:
        signals.append("long_text")
    if duration_seconds >= DENSE_SOURCE_MIN_DURATION_SECONDS:
        signals.append("long_duration")
    if heading_count >= DENSE_SOURCE_MIN_HEADING_COUNT:
        signals.append("structured_sections")
    return {
        "applies": applies,
        "signals": signals,
        "minimum_candidate_count": DENSE_SOURCE_MIN_CANDIDATE_COUNT if applies else 1,
        "minimum_distinct_anchor_count": DENSE_SOURCE_MIN_DISTINCT_ANCHOR_COUNT if applies else 1,
        "policy": "structured_long_source.v1",
    }


def _split_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    match = re.match(r"\A---[ \t]*\r?\n(?P<frontmatter>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", markdown, re.DOTALL)
    if match is None:
        return {}, markdown
    fields: dict[str, str] = {}
    for line in match.group("frontmatter").splitlines():
        key, separator, raw_value = line.partition(":")
        if separator and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
            fields[key.strip()] = raw_value.strip().strip("\"'")
    return fields, markdown[match.end() :]


def _markdown_heading_locators(markdown: str) -> list[str]:
    _frontmatter, body = _split_frontmatter(markdown)
    return [
        match.group(1).strip()
        for match in re.finditer(r"^#{1,6}[ \t]+(.+?)[ \t]*$", body, flags=re.MULTILINE)
        if match.group(1).strip()
    ]


def _is_timestamped_heading(heading: str) -> bool:
    return bool(re.match(r"^\[?\d{1,2}:\d{2}(?::\d{2})?\]?\b", heading.strip()))


def _normalize_locator(value: str) -> str:
    return re.sub(r"[^\w]+", " ", value.casefold(), flags=re.UNICODE).strip()


def _locator_matches_any(heading: str, normalized_anchor_locators: set[str]) -> bool:
    normalized_heading = _normalize_locator(heading)
    return any(
        anchor == normalized_heading
        or (len(anchor) >= 5 and anchor in normalized_heading)
        or (len(normalized_heading) >= 5 and normalized_heading in anchor)
        for anchor in normalized_anchor_locators
    )


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _optional_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _summarize_extraction_coverage(results: list[StageResult]) -> dict[str, Any]:
    diagnostics: list[dict[str, Any]] = []
    for result in results:
        artifact = json.loads(result.artifact_path.read_text(encoding="utf-8"))
        coverage = (artifact.get("summary") or {}).get("coverage_diagnostics") or {}
        diagnostics.append(
            {
                "self_study_id": artifact.get("self_study_id"),
                "status": coverage.get("status"),
                "flags": coverage.get("flags") or [],
                "source_profile": coverage.get("source_profile") or {},
                "evidence_profile": coverage.get("evidence_profile") or {},
                "repaired": result.repaired,
            }
        )
    return {
        "schema_version": COVERAGE_DIAGNOSTICS_SCHEMA_VERSION,
        "reliable_count": sum(1 for item in diagnostics if item.get("status") == "reliable"),
        "repair_required_count": sum(1 for item in diagnostics if item.get("status") == "repair_required"),
        "repaired_pass_count": sum(1 for item in diagnostics if item.get("repaired")),
        "self_studies": diagnostics,
    }


def _build_model_input(
    *,
    cg_pipeline_root: Path,
    run_dir: Path,
    prompt_path: Path,
    prompt: str,
    source_ledger: dict[str, Any],
    lesson: dict[str, Any],
    self_study: dict[str, Any],
    current_ledger_fingerprint: str,
) -> dict[str, Any]:
    source_body = self_study.get("source_body") or {}
    source_body_path = resolve_source_body_path(
        source_body=source_body,
        self_study_id=str(self_study.get("self_study_id") or ""),
        run_dir=run_dir,
        cg_pipeline_root=cg_pipeline_root,
    )
    if source_body_path is None:
        raise StageBlockedError(
            f"Source Body {self_study.get('self_study_id')} is missing or does not match its ledger hash"
        )
    markdown = source_body_path.read_text(encoding="utf-8")
    source_profile = _build_source_profile(
        markdown,
        declared_word_count=source_body.get("word_count"),
    )
    coverage_expectation = _automatic_coverage_expectation(source_profile)
    allowed_image_urls = _extract_markdown_image_urls(markdown)
    return {
        "artifact_type": "self_study_extraction_input",
        "schema_version": "self_study_extraction_input.v0",
        "source_artifact": "source_ledger.json",
        "ledger_fingerprint": current_ledger_fingerprint,
        "prompt_path": str(prompt_path),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
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
            "coverage_profile": {
                **source_profile,
                "heading_locators": _markdown_heading_locators(markdown),
                "automatic_acceptance": coverage_expectation,
            },
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
        _stamp_from_model_input(payload, inputs)
        _stamp_coverage_diagnostics(
            payload,
            model_input=inputs["self_study_extraction_input.json"],
        )
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
    _stamp_from_model_input(artifact, inputs)
    _stamp_coverage_diagnostics(
        artifact,
        model_input=model_input,
    )
    return artifact


def _stamp_from_model_input(artifact: dict[str, Any], inputs: dict[str, Any]) -> None:
    model_input = inputs.get("self_study_extraction_input.json") or {}
    fingerprint = model_input.get("ledger_fingerprint")
    if fingerprint:
        stamp_ledger_fingerprint(artifact, fingerprint)
    prompt_hash = model_input.get("prompt_sha256")
    if prompt_hash:
        artifact["prompt_sha256"] = prompt_hash


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
