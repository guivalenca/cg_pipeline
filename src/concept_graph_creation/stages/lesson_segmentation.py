from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from concept_graph_creation.runtime.derivation import (
    DerivedArtifact,
    VOLATILE_DERIVATION_KEYS,
    canonical_revision,
    derivation_artifact_succeeded,
    derivation_key,
    model_execution_identity,
    run_cached_stage,
    stage_derivation_identity,
)
from concept_graph_creation.runtime.generation import ledger_fingerprint, matches_ledger_fingerprint
from concept_graph_creation.runtime.model_work_queue import (
    ModelWorkControl,
    format_active_model_work,
    run_bounded_model_work,
    safe_model_work_activity,
)
from concept_graph_creation.runtime.provider_errors import is_transient_provider_error
from concept_graph_creation.runtime.stage_runner import (
    FLASH_ROUTE_ALIAS,
    ModelCall,
    ModelRouter,
    PRO_ROUTE_ALIAS,
    PRO_THINKING_ROUTE_ALIAS,
    StageBlockedError,
    StageContract,
    StageRunner,
)


_AUDIT_SCORE_FIELDS = (
    "segment_coherence",
    "segment_order",
    "concept_order",
    "label_quality",
    "focus_window_size",
)


@dataclass(frozen=True)
class _LessonSegmentationPrompt:
    text: str
    path_ref: str


_LESSON_SEGMENTATION_PROMPT_FILES = {
    "segment_planner": "segment_planner.md",
    "concept_orderer": "concept_orderer.md",
    "quality_audit": "quality_audit.md",
    "quality_repair": "quality_repair.md",
}


def run_lesson_segmentation_phase(
    *,
    run_dir: Path,
    model_call: ModelCall,
    router: ModelRouter | None = None,
    prompt_path: Path | None = None,
    planner_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    orderer_model_route: str = PRO_ROUTE_ALIAS,
    audit_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    quality_repair_model_route: str = PRO_ROUTE_ALIAS,
    format_repair_model_route: str = FLASH_ROUTE_ALIAS,
    concurrency: int = 6,
    provider_retry_limit: int = 2,
    provider_retry_backoff_seconds: float = 10.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    source_ledger_path = run_dir / "source_ledger.json"
    subject_merge_path = run_dir / "subject_merge.json"
    if not source_ledger_path.is_file():
        raise StageBlockedError("Lesson Segmentation requires source_ledger.json")
    if not subject_merge_path.is_file():
        raise StageBlockedError("Lesson Segmentation requires subject_merge.json from 06-subject-merge")

    source_ledger = _read_json(source_ledger_path)
    current_ledger_fingerprint = ledger_fingerprint(source_ledger)
    subject_merge = _read_json(subject_merge_path)
    prompts = _load_lesson_segmentation_prompts(prompt_path)
    resolved_router = router or ModelRouter.default()
    runner = StageRunner(router=resolved_router, model_call=model_call)
    execution_identity = model_execution_identity(
        router=resolved_router,
        model_call=model_call,
        routes={
            "planner": planner_model_route,
            "orderer": orderer_model_route,
            "audit": audit_model_route,
            "quality_repair": quality_repair_model_route,
            "format_repair": format_repair_model_route,
        },
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        schema_version="lesson_segmentation_execution.v1",
        extra_config={"quality_repair_round_limit": 1},
    )
    stage_execution_identities = {
        role: model_execution_identity(
            router=resolved_router,
            model_call=model_call,
            routes={role: route_alias, "format_repair": format_repair_model_route},
            provider_retry_limit=provider_retry_limit,
            provider_retry_backoff_seconds=provider_retry_backoff_seconds,
            schema_version=f"lesson_segmentation_{role}_execution.v1",
        )
        for role, route_alias in {
            "planner": planner_model_route,
            "orderer": orderer_model_route,
            "audit": audit_model_route,
            "quality_repair": quality_repair_model_route,
        }.items()
    }
    source_ledger_revision = canonical_revision(
        source_ledger,
        ignored_keys=VOLATILE_DERIVATION_KEYS,
    )
    subject_merge_revision = canonical_revision(
        subject_merge,
        ignored_keys=VOLATILE_DERIVATION_KEYS,
    )

    lessons = [
        lesson
        for lesson in source_ledger.get("lessons") or []
        if isinstance(lesson, dict) and str(lesson.get("lesson_id") or "")
    ]
    _emit_lesson_segmentation_progress(
        progress_callback,
        current=0,
        total=len(lessons),
    )
    lesson_results = _run_lesson_segmentation_tasks(
        lessons=lessons,
        run_dir=run_dir,
        subject_merge=subject_merge,
        prompts=prompts,
        runner=runner,
        planner_model_route=planner_model_route,
        orderer_model_route=orderer_model_route,
        audit_model_route=audit_model_route,
        quality_repair_model_route=quality_repair_model_route,
        format_repair_model_route=format_repair_model_route,
        concurrency=concurrency,
        current_ledger_fingerprint=current_ledger_fingerprint,
        source_ledger_revision=source_ledger_revision,
        subject_merge_revision=subject_merge_revision,
        execution_identity=execution_identity,
        stage_execution_identities=stage_execution_identities,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        progress_callback=progress_callback,
    )

    if not lesson_results:
        raise StageBlockedError("Lesson Segmentation requires at least one Lesson")

    summary = {
        "lesson_count": len(lesson_results),
        "segmented_lesson_count": sum(1 for result in lesson_results if result["status"] == "reliable"),
        "segment_count": sum(result["segment_count"] for result in lesson_results),
        "repair_count": sum(1 for result in lesson_results if result["repaired"]),
        "unrepaired_count": sum(1 for result in lesson_results if result["status"] == "repair_unstable"),
        "skipped_no_concept_lesson_count": sum(
            1 for result in lesson_results if result["status"] == "skipped_no_concepts"
        ),
    }
    summary_artifact = {
        "artifact_type": "lesson_segmentation_summary",
        "schema_version": "lesson_segmentation_summary.v0",
        "generated_at": _now(),
        "source_artifact": "source_ledger.json",
        "subject_merge_artifact": "subject_merge.json",
        "summary": summary,
        "artifacts": [result["artifact_path"] for result in lesson_results if result.get("artifact_path")],
        "lessons": lesson_results,
    }
    (run_dir / "lesson_segmentation_summary.json").write_text(
        json.dumps(summary_artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "summary": summary,
        "artifact_path": run_dir / "lesson_segmentation_summary.json",
        "planner_model_route": planner_model_route,
        "orderer_model_route": orderer_model_route,
        "audit_model_route": audit_model_route,
        "quality_repair_model_route": quality_repair_model_route,
        "concurrency": concurrency,
        "provider_retries": {
            "limit": provider_retry_limit,
            "backoff_seconds": provider_retry_backoff_seconds,
        },
    }


def _run_lesson_segmentation_tasks(
    *,
    lessons: list[dict[str, Any]],
    run_dir: Path,
    subject_merge: dict[str, Any],
    prompts: dict[str, _LessonSegmentationPrompt],
    runner: StageRunner,
    planner_model_route: str,
    orderer_model_route: str,
    audit_model_route: str,
    quality_repair_model_route: str,
    format_repair_model_route: str,
    concurrency: int,
    current_ledger_fingerprint: str,
    source_ledger_revision: str = "",
    subject_merge_revision: str = "",
    execution_identity: dict[str, Any] | None = None,
    stage_execution_identities: dict[str, dict[str, Any]] | None = None,
    provider_retry_limit: int = 2,
    provider_retry_backoff_seconds: float = 10.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    return run_bounded_model_work(
        lessons,
        worker=lambda lesson, control: _run_lesson_segmentation_task(
            run_dir=run_dir,
            lesson=lesson,
            subject_merge=subject_merge,
            prompts=prompts,
            runner=runner,
            planner_model_route=planner_model_route,
            orderer_model_route=orderer_model_route,
            audit_model_route=audit_model_route,
            quality_repair_model_route=quality_repair_model_route,
            format_repair_model_route=format_repair_model_route,
            current_ledger_fingerprint=current_ledger_fingerprint,
            source_ledger_revision=source_ledger_revision,
            subject_merge_revision=subject_merge_revision,
            execution_identity=execution_identity or {},
            stage_execution_identities=stage_execution_identities or {},
            provider_retry_limit=provider_retry_limit,
            provider_retry_backoff_seconds=provider_retry_backoff_seconds,
            control=control,
        ),
        concurrency=concurrency,
        on_result=lambda result, current, total: _emit_lesson_segmentation_progress(
            progress_callback,
            current=current,
            total=total,
            result=result,
        ),
        on_activity=lambda activity: _emit_lesson_segmentation_activity(
            progress_callback,
            safe_model_work_activity(
                activity,
                item_type="Lesson",
                item_ids=[str(lesson.get("lesson_id") or "") for lesson in lessons],
            ),
        ),
    )


def _emit_lesson_segmentation_progress(
    callback: Callable[[dict[str, Any]], None] | None,
    *,
    current: int,
    total: int,
    result: dict[str, Any] | None = None,
) -> None:
    if callback is None:
        return
    details: dict[str, Any] = {"progress_unit": "lessons"}
    message = f"{current}/{total} lessons processadas"
    if result is not None:
        lesson_id = str(result.get("lesson_id") or "")
        details.update(
            {
                "completed_lesson_id": lesson_id,
                "status": result.get("status"),
                "segment_count": result.get("segment_count"),
            }
        )
        message += f" · última: Lesson {lesson_id}"
    callback(
        {
            "current": current,
            "total": total,
            "message": message,
            "details": details,
        }
    )


def _emit_lesson_segmentation_activity(
    callback: Callable[[dict[str, Any]], None] | None,
    activity: dict[str, object],
) -> None:
    if callback is None or int(activity.get("active_item_count") or 0) <= 0:
        return
    callback(
        {
            "current": int(activity["current"]),
            "total": int(activity["total"]),
            "message": (
                f"{activity['current']}/{activity['total']} lessons processadas · "
                f"{format_active_model_work(activity)}"
            ),
            "details": {
                "progress_unit": "lessons",
                "active_item_count": activity["active_item_count"],
                "active_items": activity["active_items"],
                "queued_item_count": activity["queued_item_count"],
            },
        }
    )


def _run_lesson_segmentation_task(
    *,
    run_dir: Path,
    lesson: dict[str, Any],
    subject_merge: dict[str, Any],
    prompts: dict[str, _LessonSegmentationPrompt],
    runner: StageRunner,
    planner_model_route: str,
    orderer_model_route: str,
    audit_model_route: str,
    quality_repair_model_route: str,
    format_repair_model_route: str,
    current_ledger_fingerprint: str,
    source_ledger_revision: str,
    subject_merge_revision: str,
    execution_identity: dict[str, Any],
    stage_execution_identities: dict[str, dict[str, Any]],
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
    control: ModelWorkControl | None = None,
) -> dict[str, Any]:
    lesson_id = str(lesson["lesson_id"])
    lesson_dir = run_dir / "lessons" / lesson_id
    lesson_dir.mkdir(parents=True, exist_ok=True)
    concepts = _lesson_concepts(subject_merge=subject_merge, lesson_id=lesson_id)
    if not concepts:
        return {
            "lesson_id": lesson_id,
            "artifact_path": None,
            "status": "skipped_no_concepts",
            "repaired": False,
            "segment_count": 0,
            "quality_audit_artifact": None,
        }

    chain_identity = _lesson_segmentation_chain_identity(
        lesson=lesson,
        concepts=concepts,
        prompts=prompts,
        source_ledger_revision=source_ledger_revision,
        subject_merge_revision=subject_merge_revision,
        execution_identity=execution_identity,
    )
    chain_key = derivation_key(chain_identity)

    existing_result = _existing_lesson_segments_result(
        run_dir=run_dir,
        lesson_dir=lesson_dir,
        lesson_id=lesson_id,
        current_ledger_fingerprint=current_ledger_fingerprint,
        expected_chain_key=chain_key,
    )
    if existing_result:
        return existing_result

    planner_input = _build_lesson_segment_planner_input(
        lesson=lesson,
        concepts=concepts,
        prompt=prompts["segment_planner"].text,
        prompt_path=prompts["segment_planner"].path_ref,
        model_route=planner_model_route,
    )
    expected_concept_ids = [concept["concept_id"] for concept in concepts]
    planner_validator = lambda artifact: _validate_segment_decision(
        artifact,
        expected_concept_ids=expected_concept_ids,
        artifact_type="lesson_segment_planner_decision",
        schema_version="lesson_segment_planner_decision.v0",
    )
    planner_contract = StageContract(
            name="lesson_segment_planner",
            required_inputs=["lesson_segment_planner_input.json"],
            output_artifact="lesson_segment_planner_decision.json",
            model_route=planner_model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=planner_validator,
            normalizer=lambda raw, inputs: _normalize_segment_decision(
                raw,
                inputs,
                input_key="lesson_segment_planner_input.json",
                artifact_type="lesson_segment_planner_decision",
                schema_version="lesson_segment_planner_decision.v0",
            ),
        )
    planner_result = _run_cached_lesson_stage(
        lesson_dir=lesson_dir,
        stage_group="planners",
        input_filename="lesson_segment_planner_input.json",
        output_filename="lesson_segment_planner_decision.json",
        model_input=planner_input,
        identity=stage_derivation_identity(
            stage_name="lesson_segment_planner",
            model_input=planner_input,
            execution_identity=stage_execution_identities["planner"],
            input_revisions={
                "source_ledger": source_ledger_revision,
                "subject_merge": subject_merge_revision,
                "lesson": canonical_revision(lesson, ignored_keys=VOLATILE_DERIVATION_KEYS),
                "concepts": canonical_revision(concepts, ignored_keys=VOLATILE_DERIVATION_KEYS),
            },
        ),
        validator=planner_validator,
        runner=runner,
        contract=planner_contract,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        control=control,
    )
    planner_decision = planner_result.artifact

    orderer_input = _build_lesson_segment_orderer_input(
        lesson=lesson,
        concepts=concepts,
        planner_decision=planner_decision,
        prompt=prompts["concept_orderer"].text,
        prompt_path=prompts["concept_orderer"].path_ref,
        model_route=orderer_model_route,
    )
    orderer_validator = lambda artifact: _validate_orderer_decision(
        artifact,
        planner_decision=planner_decision,
    )
    orderer_contract = StageContract(
            name="lesson_segment_concept_orderer",
            required_inputs=["lesson_segment_concept_orderer_input.json"],
            output_artifact="lesson_segment_concept_orderer_decision.json",
            model_route=orderer_model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=orderer_validator,
            normalizer=lambda raw, inputs: _normalize_segment_decision(
                raw,
                inputs,
                input_key="lesson_segment_concept_orderer_input.json",
                artifact_type="lesson_segment_concept_orderer_decision",
                schema_version="lesson_segment_concept_orderer_decision.v0",
            ),
        )
    orderer_result = _run_cached_lesson_stage(
        lesson_dir=lesson_dir,
        stage_group="orderers",
        input_filename="lesson_segment_concept_orderer_input.json",
        output_filename="lesson_segment_concept_orderer_decision.json",
        model_input=orderer_input,
        identity=stage_derivation_identity(
            stage_name="lesson_segment_concept_orderer",
            model_input=orderer_input,
            execution_identity=stage_execution_identities["orderer"],
            input_revisions={
                "planner": canonical_revision(
                    planner_decision,
                    ignored_keys=VOLATILE_DERIVATION_KEYS,
                ),
                "planner_derivation_key": planner_result.derivation_key,
            },
        ),
        validator=orderer_validator,
        runner=runner,
        contract=orderer_contract,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        control=control,
    )
    ordered_decision = orderer_result.artifact

    if control is not None:
        control.raise_if_stopped()
    first_audit_result = _run_lesson_segmentation_audit(
        lesson_dir=lesson_dir,
        lesson=lesson,
        concepts=concepts,
        segments=ordered_decision["segments"],
        prompt=prompts["quality_audit"].text,
        prompt_path=prompts["quality_audit"].path_ref,
        runner=runner,
        model_route=audit_model_route,
        format_repair_model_route=format_repair_model_route,
        execution_identity=stage_execution_identities["audit"],
        source_ledger_revision=source_ledger_revision,
        subject_merge_revision=subject_merge_revision,
        upstream_derivation_key=orderer_result.derivation_key,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        control=control,
    )
    audit = first_audit_result.artifact
    final_audit_result = first_audit_result

    repaired = False
    repair_result: DerivedArtifact | None = None
    structural_warnings = ordered_decision.get("structural_warnings") or []
    if audit["reliability"] == "repair_required":
        try:
            if control is not None:
                control.raise_if_stopped()
            repair_result = _run_lesson_segmentation_repair(
                lesson_dir=lesson_dir,
                lesson=lesson,
                concepts=concepts,
                segments=ordered_decision["segments"],
                audit=audit,
                prompt=prompts["quality_repair"].text,
                prompt_path=prompts["quality_repair"].path_ref,
                runner=runner,
                model_route=quality_repair_model_route,
                format_repair_model_route=format_repair_model_route,
                execution_identity=stage_execution_identities["quality_repair"],
                source_ledger_revision=source_ledger_revision,
                subject_merge_revision=subject_merge_revision,
                upstream_derivation_key=first_audit_result.derivation_key,
                provider_retry_limit=provider_retry_limit,
                provider_retry_backoff_seconds=provider_retry_backoff_seconds,
                control=control,
            )
            ordered_decision = repair_result.artifact
            repaired = True
            structural_warnings = ordered_decision.get("structural_warnings") or []
        except StageBlockedError as exc:
            if is_transient_provider_error(exc):
                raise
            _write_quality_repair_failure(
                lesson_dir=lesson_dir,
                lesson_id=lesson_id,
                error=str(exc),
                audit=audit,
            )
            structural_warnings = [
                *structural_warnings,
                {
                    "type": "lesson_segmentation_quality_repair_failed",
                    "message": str(exc),
                },
            ]
        if repair_result is not None:
            final_audit_result = _run_lesson_segmentation_audit(
                lesson_dir=lesson_dir,
                lesson=lesson,
                concepts=concepts,
                segments=ordered_decision["segments"],
                prompt=prompts["quality_audit"].text,
                prompt_path=prompts["quality_audit"].path_ref,
                runner=runner,
                model_route=audit_model_route,
                format_repair_model_route=format_repair_model_route,
                execution_identity=stage_execution_identities["audit"],
                source_ledger_revision=source_ledger_revision,
                subject_merge_revision=subject_merge_revision,
                upstream_derivation_key=repair_result.derivation_key,
                provider_retry_limit=provider_retry_limit,
                provider_retry_backoff_seconds=provider_retry_backoff_seconds,
                control=control,
            )
            audit = final_audit_result.artifact

    status = "reliable" if audit["reliability"] == "reliable" else "repair_unstable"
    artifact = _assemble_lesson_segments_artifact(
        lesson_id=lesson_id,
        segments=ordered_decision["segments"],
        status=status,
        repaired=repaired,
        structural_warnings=structural_warnings,
        current_ledger_fingerprint=current_ledger_fingerprint,
    )
    artifact["derivation"] = {
        "schema_version": "lesson_segmentation_derivation.v1",
        "status": "succeeded",
        "key": chain_key,
        "completed_at": _now(),
        "identity": chain_identity,
        "output_revision": _lesson_segments_output_revision(artifact),
        "planner_artifact": str(planner_result.artifact_path.relative_to(run_dir)),
        "planner_derivation_key": planner_result.derivation_key,
        "orderer_artifact": str(orderer_result.artifact_path.relative_to(run_dir)),
        "orderer_derivation_key": orderer_result.derivation_key,
        "first_audit_artifact": str(first_audit_result.artifact_path.relative_to(run_dir)),
        "first_audit_derivation_key": first_audit_result.derivation_key,
        "final_audit_artifact": str(final_audit_result.artifact_path.relative_to(run_dir)),
        "final_audit_derivation_key": final_audit_result.derivation_key,
        "repair_artifact": (
            str(repair_result.artifact_path.relative_to(run_dir)) if repair_result is not None else None
        ),
        "repair_derivation_key": repair_result.derivation_key if repair_result is not None else None,
        "execution": execution_identity,
    }
    artifact_path = lesson_dir / "lesson_segments.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "lesson_id": lesson_id,
        "artifact_path": str(artifact_path.relative_to(run_dir)),
        "status": status,
        "repaired": repaired,
        "segment_count": len(artifact["segments"]),
        "quality_audit_artifact": f"lessons/{lesson_id}/lesson_segmentation_quality_audit.json",
    }


def _existing_lesson_segments_result(
    *,
    run_dir: Path,
    lesson_dir: Path,
    lesson_id: str,
    current_ledger_fingerprint: str,
    expected_chain_key: str,
) -> dict[str, Any] | None:
    artifact_path = lesson_dir / "lesson_segments.json"
    if not artifact_path.is_file():
        return None
    try:
        artifact = _read_json(artifact_path)
    except json.JSONDecodeError:
        return None
    if not matches_ledger_fingerprint(artifact, current_ledger_fingerprint):
        return None
    if artifact.get("artifact_type") != "lesson_segments":
        return None
    if artifact.get("schema_version") != "lesson_segments.v0":
        return None
    if artifact.get("lesson_id") != lesson_id:
        return None
    segments = artifact.get("segments")
    if not isinstance(segments, list):
        return None
    status = str(artifact.get("status") or "")
    if status not in {"reliable", "repair_unstable"}:
        return None
    provenance = artifact.get("derivation")
    if not isinstance(provenance, dict):
        return None
    if (
        provenance.get("schema_version") != "lesson_segmentation_derivation.v1"
        or provenance.get("status") != "succeeded"
        or provenance.get("key") != expected_chain_key
        or not isinstance(provenance.get("identity"), dict)
        or derivation_key(provenance["identity"]) != expected_chain_key
        or provenance.get("output_revision") != _lesson_segments_output_revision(artifact)
    ):
        return None
    expected_ids = [
        str(concept_id)
        for segment in segments
        if isinstance(segment, dict)
        for concept_id in segment.get("concept_ids") or []
        if str(concept_id)
    ]
    stage_validations = (
        (
            "planner_artifact",
            "planner_derivation_key",
            lambda value: _validate_segment_decision(
                value,
                expected_concept_ids=expected_ids,
                artifact_type="lesson_segment_planner_decision",
                schema_version="lesson_segment_planner_decision.v0",
            ),
        ),
        (
            "orderer_artifact",
            "orderer_derivation_key",
            lambda value: _validate_segment_decision(
                value,
                expected_concept_ids=expected_ids,
                artifact_type="lesson_segment_concept_orderer_decision",
                schema_version="lesson_segment_concept_orderer_decision.v0",
            ),
        ),
        ("first_audit_artifact", "first_audit_derivation_key", _validate_quality_audit),
        ("final_audit_artifact", "final_audit_derivation_key", _validate_quality_audit),
    )
    for artifact_field, key_field, validator in stage_validations:
        artifact_ref = provenance.get(artifact_field)
        expected_key = provenance.get(key_field)
        if not isinstance(artifact_ref, str) or not isinstance(expected_key, str):
            return None
        if not derivation_artifact_succeeded(
            artifact_path=run_dir / artifact_ref,
            expected_key=expected_key,
            validator=validator,
        ):
            return None
    repair_ref = provenance.get("repair_artifact")
    repair_key = provenance.get("repair_derivation_key")
    if repair_ref is not None or repair_key is not None:
        if not isinstance(repair_ref, str) or not isinstance(repair_key, str):
            return None
        if not derivation_artifact_succeeded(
            artifact_path=run_dir / repair_ref,
            expected_key=repair_key,
            validator=lambda value: _validate_segment_decision(
                value,
                expected_concept_ids=expected_ids,
                artifact_type="lesson_segmentation_quality_repair_decision",
                schema_version="lesson_segmentation_quality_repair_decision.v0",
            ),
        ):
            return None
    final_audit_ref = provenance["final_audit_artifact"]
    _write_compatibility_artifact(
        lesson_dir / "lesson_segmentation_quality_audit.json",
        _read_json(run_dir / final_audit_ref),
    )
    quality_audit_path = lesson_dir / "lesson_segmentation_quality_audit.json"
    return {
        "lesson_id": lesson_id,
        "artifact_path": str(artifact_path.relative_to(run_dir)),
        "status": status,
        "repaired": bool(artifact.get("repaired")),
        "segment_count": len(segments),
        "quality_audit_artifact": (
            f"lessons/{lesson_id}/lesson_segmentation_quality_audit.json"
            if quality_audit_path.is_file()
            else None
        ),
    }


def _build_lesson_segment_planner_input(
    *,
    lesson: dict[str, Any],
    concepts: list[dict[str, Any]],
    prompt: str,
    prompt_path: str,
    model_route: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "lesson_segment_planner_input",
        "schema_version": "lesson_segment_planner_input.v0",
        "source_artifact": "source_ledger.json",
        "subject_merge_artifact": "subject_merge.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "lesson_segment_planner",
        "model_route": model_route,
        "lesson": _compact_lesson(lesson),
        "concepts": concepts,
        "output_contract": _segment_decision_output_contract(),
        "web_access_policy": _no_web_policy(),
    }


def _build_lesson_segment_orderer_input(
    *,
    lesson: dict[str, Any],
    concepts: list[dict[str, Any]],
    planner_decision: dict[str, Any],
    prompt: str,
    prompt_path: str,
    model_route: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "lesson_segment_concept_orderer_input",
        "schema_version": "lesson_segment_concept_orderer_input.v0",
        "source_artifact": "source_ledger.json",
        "subject_merge_artifact": "subject_merge.json",
        "planner_decision_artifact": "lesson_segment_planner_decision.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "lesson_segment_concept_orderer",
        "model_route": model_route,
        "lesson": _compact_lesson(lesson),
        "concepts": concepts,
        "segments": [
            {"label": segment["label"], "concept_ids": segment["concept_ids"]}
            for segment in planner_decision.get("segments") or []
        ],
        "output_contract": _segment_decision_output_contract(),
        "web_access_policy": _no_web_policy(),
    }


def _run_lesson_segmentation_audit(
    *,
    lesson_dir: Path,
    lesson: dict[str, Any],
    concepts: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    prompt: str,
    prompt_path: str,
    runner: StageRunner,
    model_route: str,
    format_repair_model_route: str,
    execution_identity: dict[str, Any],
    source_ledger_revision: str,
    subject_merge_revision: str,
    upstream_derivation_key: str,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
    control: ModelWorkControl | None,
) -> DerivedArtifact:
    model_input = {
        "artifact_type": "lesson_segmentation_quality_audit_input",
        "schema_version": "lesson_segmentation_quality_audit_input.v0",
        "source_artifact": "source_ledger.json",
        "subject_merge_artifact": "subject_merge.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "lesson_segmentation_quality_audit",
        "model_route": model_route,
        "lesson": _compact_lesson(lesson),
        "concepts": concepts,
        "segments": segments,
        "output_contract": _quality_audit_output_contract(),
        "web_access_policy": _no_web_policy(),
    }
    contract = StageContract(
            name="lesson_segmentation_quality_audit",
            required_inputs=["lesson_segmentation_quality_audit_input.json"],
            output_artifact="lesson_segmentation_quality_audit.json",
            model_route=model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=_validate_quality_audit,
            normalizer=_normalize_quality_audit_output,
        )
    return _run_cached_lesson_stage(
        lesson_dir=lesson_dir,
        stage_group="audits",
        input_filename="lesson_segmentation_quality_audit_input.json",
        output_filename="lesson_segmentation_quality_audit.json",
        model_input=model_input,
        identity=stage_derivation_identity(
            stage_name="lesson_segmentation_quality_audit",
            model_input=model_input,
            execution_identity=execution_identity,
            input_revisions={
                "source_ledger": source_ledger_revision,
                "subject_merge": subject_merge_revision,
                "upstream_derivation_key": upstream_derivation_key,
                "segments": canonical_revision(
                    segments,
                    ignored_keys=VOLATILE_DERIVATION_KEYS,
                ),
            },
        ),
        validator=_validate_quality_audit,
        runner=runner,
        contract=contract,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        control=control,
    )


def _write_quality_repair_failure(
    *,
    lesson_dir: Path,
    lesson_id: str,
    error: str,
    audit: dict[str, Any],
) -> None:
    payload = {
        "artifact_type": "lesson_segmentation_quality_repair_failure",
        "schema_version": "lesson_segmentation_quality_repair_failure.v0",
        "generated_at": _now(),
        "lesson_id": lesson_id,
        "quality_audit_artifact": "lesson_segmentation_quality_audit.json",
        "quality_audit_reliability": audit.get("reliability"),
        "error": error,
    }
    (lesson_dir / "lesson_segmentation_quality_repair_failure.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _run_lesson_segmentation_repair(
    *,
    lesson_dir: Path,
    lesson: dict[str, Any],
    concepts: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    audit: dict[str, Any],
    prompt: str,
    prompt_path: str,
    runner: StageRunner,
    model_route: str,
    format_repair_model_route: str,
    execution_identity: dict[str, Any],
    source_ledger_revision: str,
    subject_merge_revision: str,
    upstream_derivation_key: str,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
    control: ModelWorkControl | None,
) -> DerivedArtifact:
    model_input = {
        "artifact_type": "lesson_segmentation_quality_repair_input",
        "schema_version": "lesson_segmentation_quality_repair_input.v0",
        "source_artifact": "source_ledger.json",
        "subject_merge_artifact": "subject_merge.json",
        "quality_audit_artifact": "lesson_segmentation_quality_audit.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "lesson_segmentation_quality_repair",
        "model_route": model_route,
        "lesson": _compact_lesson(lesson),
        "concepts": concepts,
        "current_segments": segments,
        "quality_audit": audit,
        "output_contract": _segment_decision_output_contract(),
        "web_access_policy": _no_web_policy(),
    }
    expected_concept_ids = [concept["concept_id"] for concept in concepts]
    validator = lambda artifact: _validate_segment_decision(
        artifact,
        expected_concept_ids=expected_concept_ids,
        artifact_type="lesson_segmentation_quality_repair_decision",
        schema_version="lesson_segmentation_quality_repair_decision.v0",
    )
    contract = StageContract(
            name="lesson_segmentation_quality_repair",
            required_inputs=["lesson_segmentation_quality_repair_input.json"],
            output_artifact="lesson_segmentation_quality_repair_decision.json",
            model_route=model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=validator,
            normalizer=lambda raw, inputs: _normalize_segment_decision(
                raw,
                inputs,
                input_key="lesson_segmentation_quality_repair_input.json",
                artifact_type="lesson_segmentation_quality_repair_decision",
                schema_version="lesson_segmentation_quality_repair_decision.v0",
            ),
        )
    return _run_cached_lesson_stage(
        lesson_dir=lesson_dir,
        stage_group="repairs",
        input_filename="lesson_segmentation_quality_repair_input.json",
        output_filename="lesson_segmentation_quality_repair_decision.json",
        model_input=model_input,
        identity=stage_derivation_identity(
            stage_name="lesson_segmentation_quality_repair",
            model_input=model_input,
            execution_identity=execution_identity,
            input_revisions={
                "source_ledger": source_ledger_revision,
                "subject_merge": subject_merge_revision,
                "upstream_derivation_key": upstream_derivation_key,
                "quality_audit": canonical_revision(
                    audit,
                    ignored_keys=VOLATILE_DERIVATION_KEYS,
                ),
                "segments": canonical_revision(
                    segments,
                    ignored_keys=VOLATILE_DERIVATION_KEYS,
                ),
            },
        ),
        validator=validator,
        runner=runner,
        contract=contract,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        control=control,
    )


def _run_cached_lesson_stage(
    *,
    lesson_dir: Path,
    stage_group: str,
    input_filename: str,
    output_filename: str,
    model_input: dict[str, Any],
    identity: dict[str, Any],
    validator: Callable[[dict[str, Any]], list[str]],
    runner: StageRunner,
    contract: StageContract,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
    control: ModelWorkControl | None,
) -> DerivedArtifact:
    result = run_cached_stage(
        cache_root=lesson_dir / "lesson_segmentation_derivations",
        stage_group=stage_group,
        input_filename=input_filename,
        output_filename=output_filename,
        model_input=model_input,
        identity=identity,
        validator=validator,
        execute=lambda stage_dir: _run_stage_with_provider_retry(
            runner=runner,
            contract=contract,
            run_dir=stage_dir,
            provider_retry_limit=provider_retry_limit,
            provider_retry_backoff_seconds=provider_retry_backoff_seconds,
            control=control,
        ),
    )
    _write_compatibility_artifact(lesson_dir / input_filename, model_input)
    _write_compatibility_artifact(lesson_dir / output_filename, result.artifact)
    return result


def _run_stage_with_provider_retry(
    *,
    runner: StageRunner,
    contract: StageContract,
    run_dir: Path,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
    control: ModelWorkControl | None,
) -> Any:
    for attempt in range(provider_retry_limit + 1):
        if control is not None:
            control.raise_if_stopped()
        try:
            return runner.run(contract, run_dir=run_dir)
        except StageBlockedError as exc:
            if not is_transient_provider_error(exc) or attempt >= provider_retry_limit:
                raise
            retry_delay = provider_retry_backoff_seconds * (attempt + 1)
            if retry_delay <= 0:
                continue
            if control is None:
                time.sleep(retry_delay)
            elif control.wait_for_stop(retry_delay):
                control.raise_if_stopped()
    raise StageBlockedError(f"{contract.name} exceeded provider retry limit")


def _lesson_segmentation_chain_identity(
    *,
    lesson: dict[str, Any],
    concepts: list[dict[str, Any]],
    prompts: dict[str, _LessonSegmentationPrompt],
    source_ledger_revision: str,
    subject_merge_revision: str,
    execution_identity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "lesson_segmentation_derivation.v1",
        "source_ledger_revision": source_ledger_revision,
        "subject_merge_revision": subject_merge_revision,
        "lesson_revision": canonical_revision(
            lesson,
            ignored_keys=VOLATILE_DERIVATION_KEYS,
        ),
        "concepts_revision": canonical_revision(
            concepts,
            ignored_keys=VOLATILE_DERIVATION_KEYS,
        ),
        "prompts_revision": canonical_revision(
            {
                name: {"path": prompt.path_ref, "content": prompt.text}
                for name, prompt in sorted(prompts.items())
            }
        ),
        "contracts_revision": canonical_revision(
            {
                "planner": _segment_decision_output_contract(),
                "orderer": _segment_decision_output_contract(),
                "audit": _quality_audit_output_contract(),
                "repair": _segment_decision_output_contract(),
            }
        ),
        "execution": execution_identity,
    }


def _lesson_segments_output_revision(artifact: dict[str, Any]) -> str:
    payload = json.loads(json.dumps(artifact, ensure_ascii=False))
    payload.pop("derivation", None)
    return canonical_revision(payload, ignored_keys=VOLATILE_DERIVATION_KEYS)


def _write_compatibility_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _lesson_concepts(*, subject_merge: dict[str, Any], lesson_id: str) -> list[dict[str, Any]]:
    concepts = []
    for concept in subject_merge.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        if not _concept_occurs_in_lesson(concept, lesson_id=lesson_id):
            continue
        concepts.append(_compact_lesson_concept(concept, lesson_id=lesson_id))
    return concepts


def _compact_lesson_concept(concept: dict[str, Any], *, lesson_id: str) -> dict[str, Any]:
    concept_id = str(concept.get("concept_id") or "")
    if not concept_id:
        raise StageBlockedError(f"Lesson {lesson_id} has a Concept without concept_id")
    label = str(concept.get("label") or "").strip()
    description = str(concept.get("teaching_description") or concept.get("description") or "").strip()
    coverage_criteria = [str(item).strip() for item in concept.get("coverage_criteria") or [] if str(item).strip()]
    if not label:
        raise StageBlockedError(f"Lesson Segmentation requires label for Concept {concept_id}")
    if not description:
        raise StageBlockedError(f"Lesson Segmentation requires teaching description for Concept {concept_id}")
    if not coverage_criteria:
        raise StageBlockedError(f"Lesson Segmentation requires Coverage Criteria for Concept {concept_id}")
    return {
        "concept_id": concept_id,
        "label": label,
        "teaching_description": description,
        "coverage_criteria": coverage_criteria,
    }


def _concept_occurs_in_lesson(concept: dict[str, Any], *, lesson_id: str) -> bool:
    for occurrence in concept.get("occurrences") or []:
        if not isinstance(occurrence, dict):
            continue
        lesson = occurrence.get("lesson") or {}
        if lesson.get("lesson_id") == lesson_id:
            return True
    return False


def _compact_lesson(lesson: dict[str, Any]) -> dict[str, Any]:
    return {
        "lesson_id": lesson.get("lesson_id"),
        "title": lesson.get("title"),
    }


def _assemble_lesson_segments_artifact(
    *,
    lesson_id: str,
    segments: list[dict[str, Any]],
    status: str,
    repaired: bool,
    structural_warnings: list[dict[str, Any]],
    current_ledger_fingerprint: str,
) -> dict[str, Any]:
    final_segments = []
    for index, segment in enumerate(segments, start=1):
        final_segments.append(
            {
                "segment_id": f"segment_{index:03d}",
                "label": segment["label"],
                "instructional_role": "teach",
                "concept_ids": segment["concept_ids"],
            }
        )
    return {
        "artifact_type": "lesson_segments",
        "schema_version": "lesson_segments.v0",
        "generated_at": _now(),
        "source_artifact": "source_ledger.json",
        "subject_merge_artifact": "subject_merge.json",
        "ledger_fingerprint": current_ledger_fingerprint,
        "lesson_id": lesson_id,
        "status": status,
        "repaired": repaired,
        "segments": final_segments,
        "structural_warnings": structural_warnings,
        "summary": {
            "segment_count": len(final_segments),
            "largest_segment_concept_count": max((len(segment["concept_ids"]) for segment in final_segments), default=0),
        },
    }


def _normalize_segment_decision(
    raw: str,
    inputs: dict[str, Any],
    *,
    input_key: str,
    artifact_type: str,
    schema_version: str,
) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("lesson segmentation model output must be a JSON object")
    model_input = inputs[input_key]
    lesson = model_input.get("lesson") or {}
    segments = _normalize_segments(payload.get("segments"))
    return {
        "artifact_type": artifact_type,
        "schema_version": schema_version,
        "generated_at": _now(),
        "lesson_id": lesson.get("lesson_id"),
        "model_route": model_input.get("model_route"),
        "segments": segments,
        "structural_warnings": _segment_warnings(segments),
    }


def _normalize_segments(raw_segments: Any) -> list[dict[str, Any]]:
    segments = []
    if not isinstance(raw_segments, list):
        return segments
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        concept_ids = [str(concept_id).strip() for concept_id in item.get("concept_ids") or [] if str(concept_id).strip()]
        segments.append({"label": label, "concept_ids": concept_ids})
    return segments


def _validate_segment_decision(
    artifact: dict[str, Any],
    *,
    expected_concept_ids: list[str],
    artifact_type: str,
    schema_version: str,
) -> list[str]:
    errors = []
    if artifact.get("artifact_type") != artifact_type:
        errors.append(f"{artifact_type}.artifact_type must be '{artifact_type}'")
    if artifact.get("schema_version") != schema_version:
        errors.append(f"{artifact_type}.schema_version must be '{schema_version}'")
    segments = artifact.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append(f"{artifact_type}.segments must not be empty")
        return errors
    seen: list[str] = []
    expected_set = set(expected_concept_ids)
    for index, segment in enumerate(segments):
        location = f"{artifact_type}.segments[{index}]"
        if not isinstance(segment, dict):
            errors.append(f"{location} must be an object")
            continue
        if not str(segment.get("label") or "").strip():
            errors.append(f"{location}.label is required")
        concept_ids = segment.get("concept_ids")
        if not isinstance(concept_ids, list) or not concept_ids:
            errors.append(f"{location}.concept_ids must not be empty")
            continue
        for concept_id in concept_ids:
            if not isinstance(concept_id, str) or not concept_id:
                errors.append(f"{location}.concept_ids must contain Concept IDs")
                continue
            if concept_id not in expected_set:
                errors.append(f"{location}.concept_ids references unknown Concept ID: {concept_id}")
            seen.append(concept_id)
    duplicates = sorted({concept_id for concept_id in seen if seen.count(concept_id) > 1})
    if duplicates:
        errors.append(f"{artifact_type}.segments repeat Concept IDs: " + ", ".join(duplicates))
    missing = [concept_id for concept_id in expected_concept_ids if concept_id not in seen]
    if missing:
        errors.append(f"{artifact_type}.segments are missing Concept IDs: " + ", ".join(missing))
    extra = [concept_id for concept_id in seen if concept_id not in expected_set]
    if extra:
        errors.append(f"{artifact_type}.segments include extra Concept IDs: " + ", ".join(sorted(set(extra))))
    return errors


def _validate_orderer_decision(artifact: dict[str, Any], *, planner_decision: dict[str, Any]) -> list[str]:
    expected_concept_ids = [
        concept_id
        for segment in planner_decision.get("segments") or []
        for concept_id in segment.get("concept_ids") or []
    ]
    errors = _validate_segment_decision(
        artifact,
        expected_concept_ids=expected_concept_ids,
        artifact_type="lesson_segment_concept_orderer_decision",
        schema_version="lesson_segment_concept_orderer_decision.v0",
    )
    planner_segments = planner_decision.get("segments") or []
    segments = artifact.get("segments") or []
    if len(segments) != len(planner_segments):
        errors.append("lesson_segment_concept_orderer_decision must preserve Segment count")
        return errors
    for index, (planned, ordered) in enumerate(zip(planner_segments, segments)):
        location = f"lesson_segment_concept_orderer_decision.segments[{index}]"
        if planned.get("label") != ordered.get("label"):
            errors.append(f"{location}.label must preserve the planner label")
        if set(planned.get("concept_ids") or []) != set(ordered.get("concept_ids") or []):
            errors.append(f"{location}.concept_ids must preserve the planner Segment membership")
    return errors


def _normalize_quality_audit_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("lesson segmentation quality audit output must be a JSON object")
    model_input = inputs["lesson_segmentation_quality_audit_input.json"]
    return {
        "artifact_type": "lesson_segmentation_quality_audit",
        "schema_version": "lesson_segmentation_quality_audit.v0",
        "generated_at": _now(),
        "lesson_id": (model_input.get("lesson") or {}).get("lesson_id"),
        "model_route": model_input.get("model_route"),
        "scores": payload.get("scores") or {},
        "reliability": payload.get("reliability"),
        "findings": payload.get("findings") or [],
        "repair_instructions": payload.get("repair_instructions") or [],
    }


def _validate_quality_audit(artifact: dict[str, Any]) -> list[str]:
    errors = []
    if artifact.get("artifact_type") != "lesson_segmentation_quality_audit":
        errors.append("lesson_segmentation_quality_audit.artifact_type must be 'lesson_segmentation_quality_audit'")
    if artifact.get("schema_version") != "lesson_segmentation_quality_audit.v0":
        errors.append("lesson_segmentation_quality_audit.schema_version must be 'lesson_segmentation_quality_audit.v0'")
    scores = artifact.get("scores")
    if not isinstance(scores, dict):
        errors.append("lesson_segmentation_quality_audit.scores must be an object")
        scores = {}
    for field in _AUDIT_SCORE_FIELDS:
        value = scores.get(field)
        if not isinstance(value, int) or value < 0 or value > 3:
            errors.append(f"lesson_segmentation_quality_audit.scores.{field} must be an integer from 0 to 3")
    reliability = artifact.get("reliability")
    if reliability not in {"reliable", "repair_required"}:
        errors.append("lesson_segmentation_quality_audit.reliability must be reliable or repair_required")
    findings = artifact.get("findings")
    if not isinstance(findings, list):
        errors.append("lesson_segmentation_quality_audit.findings must be a list")
    repair_instructions = artifact.get("repair_instructions")
    if not isinstance(repair_instructions, list):
        errors.append("lesson_segmentation_quality_audit.repair_instructions must be a list")
    if reliability == "repair_required" and not repair_instructions:
        errors.append("lesson_segmentation_quality_audit.repair_required requires repair_instructions")
    return errors


def _segment_warnings(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    warnings = []
    for index, segment in enumerate(segments, start=1):
        concept_count = len(segment.get("concept_ids") or [])
        if concept_count >= 5:
            warnings.append(
                {
                    "warning": "large_segment",
                    "segment_index": index,
                    "label": segment.get("label"),
                    "concept_count": concept_count,
                    "message": "Segment has 5 or more Concepts and should usually be split.",
                }
            )
    return warnings


def _segment_decision_output_contract() -> dict[str, Any]:
    return {
        "segments": [
            {
                "label": "Short human-readable teaching label.",
                "concept_ids": ["Every provided Concept ID exactly once across all Segments."],
            }
        ],
        "rules": [
            "Return only valid JSON.",
            "Do not create Segment IDs.",
            "Do not create instructional roles.",
            "Every Concept must appear exactly once.",
        ],
    }


def _quality_audit_output_contract() -> dict[str, Any]:
    return {
        "scores": {field: "integer 0-3" for field in _AUDIT_SCORE_FIELDS},
        "reliability": "reliable or repair_required",
        "findings": [
            {
                "issue": "Short issue name.",
                "segment_labels": ["Relevant Segment labels, if any."],
                "concept_ids": ["Relevant Concept IDs, if any."],
                "explanation": "Concrete problem with the proposed segmentation.",
            }
        ],
        "repair_instructions": ["Targeted instructions for a Pro repair call, required only when repair_required."],
    }


def _load_lesson_segmentation_prompts(prompt_path: Path | None) -> dict[str, _LessonSegmentationPrompt]:
    prompts_root = Path(__file__).resolve().parents[3] / "prompts"
    selected = prompt_path or prompts_root / "lesson_segmentation"
    if selected.is_file():
        text = selected.read_text(encoding="utf-8")
        path_ref = _prompt_path_ref(selected, prompts_root)
        return {
            task: _LessonSegmentationPrompt(text=text, path_ref=path_ref)
            for task in _LESSON_SEGMENTATION_PROMPT_FILES
        }
    if not selected.is_dir():
        raise StageBlockedError(f"Lesson Segmentation prompt path does not exist: {selected}")
    prompts: dict[str, _LessonSegmentationPrompt] = {}
    for task, filename in _LESSON_SEGMENTATION_PROMPT_FILES.items():
        path = selected / filename
        if not path.is_file():
            raise StageBlockedError(f"Lesson Segmentation missing task prompt: {path}")
        prompts[task] = _LessonSegmentationPrompt(
            text=path.read_text(encoding="utf-8"),
            path_ref=_prompt_path_ref(path, prompts_root),
        )
    return prompts


def _prompt_path_ref(path: Path, prompts_root: Path) -> str:
    try:
        return str(path.relative_to(prompts_root))
    except ValueError:
        return str(path)


def _no_web_policy() -> dict[str, Any]:
    return {
        "web_access": "disabled",
        "reason": "Lesson Segmentation must use only the provided Lesson Concepts.",
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
