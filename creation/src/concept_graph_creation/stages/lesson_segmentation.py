from __future__ import annotations

import concurrent.futures
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
) -> dict[str, Any]:
    source_ledger_path = run_dir / "source_ledger.json"
    subject_merge_path = run_dir / "subject_merge.json"
    if not source_ledger_path.is_file():
        raise StageBlockedError("Lesson Segmentation requires source_ledger.json")
    if not subject_merge_path.is_file():
        raise StageBlockedError("Lesson Segmentation requires subject_merge.json from Phase 5")

    source_ledger = _read_json(source_ledger_path)
    subject_merge = _read_json(subject_merge_path)
    prompts = _load_lesson_segmentation_prompts(prompt_path)
    runner = StageRunner(router=router or ModelRouter.default(), model_call=model_call)

    lessons = [
        lesson
        for lesson in source_ledger.get("lessons") or []
        if isinstance(lesson, dict) and str(lesson.get("lesson_id") or "")
    ]
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
) -> list[dict[str, Any]]:
    if concurrency <= 1 or len(lessons) <= 1:
        return [
            _run_lesson_segmentation_task(
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
            )
            for lesson in lessons
        ]

    results_by_index: dict[int, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {
            executor.submit(
                _run_lesson_segmentation_task,
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
            ): index
            for index, lesson in enumerate(lessons)
        }
        for future in concurrent.futures.as_completed(futures):
            results_by_index[futures[future]] = future.result()
    return [results_by_index[index] for index in range(len(lessons))]


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

    planner_input = _build_lesson_segment_planner_input(
        lesson=lesson,
        concepts=concepts,
        prompt=prompts["segment_planner"].text,
        prompt_path=prompts["segment_planner"].path_ref,
        model_route=planner_model_route,
    )
    (lesson_dir / "lesson_segment_planner_input.json").write_text(
        json.dumps(planner_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    planner_result = runner.run(
        StageContract(
            name="lesson_segment_planner",
            required_inputs=["lesson_segment_planner_input.json"],
            output_artifact="lesson_segment_planner_decision.json",
            model_route=planner_model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=lambda artifact: _validate_segment_decision(
                artifact,
                expected_concept_ids=[concept["concept_id"] for concept in concepts],
                artifact_type="lesson_segment_planner_decision",
                schema_version="lesson_segment_planner_decision.v0",
            ),
            normalizer=lambda raw, inputs: _normalize_segment_decision(
                raw,
                inputs,
                input_key="lesson_segment_planner_input.json",
                artifact_type="lesson_segment_planner_decision",
                schema_version="lesson_segment_planner_decision.v0",
            ),
        ),
        run_dir=lesson_dir,
    )
    planner_decision = _read_json(planner_result.artifact_path)

    orderer_input = _build_lesson_segment_orderer_input(
        lesson=lesson,
        concepts=concepts,
        planner_decision=planner_decision,
        prompt=prompts["concept_orderer"].text,
        prompt_path=prompts["concept_orderer"].path_ref,
        model_route=orderer_model_route,
    )
    (lesson_dir / "lesson_segment_concept_orderer_input.json").write_text(
        json.dumps(orderer_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    orderer_result = runner.run(
        StageContract(
            name="lesson_segment_concept_orderer",
            required_inputs=["lesson_segment_concept_orderer_input.json"],
            output_artifact="lesson_segment_concept_orderer_decision.json",
            model_route=orderer_model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=lambda artifact: _validate_orderer_decision(artifact, planner_decision=planner_decision),
            normalizer=lambda raw, inputs: _normalize_segment_decision(
                raw,
                inputs,
                input_key="lesson_segment_concept_orderer_input.json",
                artifact_type="lesson_segment_concept_orderer_decision",
                schema_version="lesson_segment_concept_orderer_decision.v0",
            ),
        ),
        run_dir=lesson_dir,
    )
    ordered_decision = _read_json(orderer_result.artifact_path)

    audit = _run_lesson_segmentation_audit(
        lesson_dir=lesson_dir,
        lesson=lesson,
        concepts=concepts,
        segments=ordered_decision["segments"],
        prompt=prompts["quality_audit"].text,
        prompt_path=prompts["quality_audit"].path_ref,
        runner=runner,
        model_route=audit_model_route,
        format_repair_model_route=format_repair_model_route,
    )

    repaired = False
    if audit["reliability"] == "repair_required":
        repaired = True
        ordered_decision = _run_lesson_segmentation_repair(
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
        )
        audit = _run_lesson_segmentation_audit(
            lesson_dir=lesson_dir,
            lesson=lesson,
            concepts=concepts,
            segments=ordered_decision["segments"],
            prompt=prompts["quality_audit"].text,
            prompt_path=prompts["quality_audit"].path_ref,
            runner=runner,
            model_route=audit_model_route,
            format_repair_model_route=format_repair_model_route,
        )

    status = "reliable" if audit["reliability"] == "reliable" else "repair_unstable"
    artifact = _assemble_lesson_segments_artifact(
        lesson_id=lesson_id,
        segments=ordered_decision["segments"],
        status=status,
        repaired=repaired,
        structural_warnings=ordered_decision.get("structural_warnings") or [],
    )
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
) -> dict[str, Any]:
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
    (lesson_dir / "lesson_segmentation_quality_audit_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = runner.run(
        StageContract(
            name="lesson_segmentation_quality_audit",
            required_inputs=["lesson_segmentation_quality_audit_input.json"],
            output_artifact="lesson_segmentation_quality_audit.json",
            model_route=model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=_validate_quality_audit,
            normalizer=_normalize_quality_audit_output,
        ),
        run_dir=lesson_dir,
    )
    return _read_json(result.artifact_path)


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
) -> dict[str, Any]:
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
    (lesson_dir / "lesson_segmentation_quality_repair_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    expected_concept_ids = [concept["concept_id"] for concept in concepts]
    result = runner.run(
        StageContract(
            name="lesson_segmentation_quality_repair",
            required_inputs=["lesson_segmentation_quality_repair_input.json"],
            output_artifact="lesson_segmentation_quality_repair_decision.json",
            model_route=model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=lambda artifact: _validate_segment_decision(
                artifact,
                expected_concept_ids=expected_concept_ids,
                artifact_type="lesson_segmentation_quality_repair_decision",
                schema_version="lesson_segmentation_quality_repair_decision.v0",
            ),
            normalizer=lambda raw, inputs: _normalize_segment_decision(
                raw,
                inputs,
                input_key="lesson_segmentation_quality_repair_input.json",
                artifact_type="lesson_segmentation_quality_repair_decision",
                schema_version="lesson_segmentation_quality_repair_decision.v0",
            ),
        ),
        run_dir=lesson_dir,
    )
    return _read_json(result.artifact_path)


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
