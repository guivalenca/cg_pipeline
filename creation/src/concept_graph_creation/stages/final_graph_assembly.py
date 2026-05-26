from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from concept_graph_creation.runtime.stage_runner import StageBlockedError


ALLOWED_KNOWLEDGE_TYPES = {"conceptual", "procedural", "factual", "applied"}
FINAL_GRAPH_DIR = "final_graph"


def run_final_graph_assembly_phase(*, run_dir: Path) -> dict[str, Any]:
    source_ledger = _required_json(run_dir / "source_ledger.json", "Final Graph Assembly requires source_ledger.json")
    subject_merge = _required_json(run_dir / "subject_merge.json", "Final Graph Assembly requires subject_merge.json")
    dependency_inference = _required_json(
        run_dir / "dependency_inference.json",
        "Final Graph Assembly requires dependency_inference.json from Phase 6",
    )
    segmentation_summary = _required_json(
        run_dir / "lesson_segmentation_summary.json",
        "Final Graph Assembly requires lesson_segmentation_summary.json from Phase 7",
    )
    knowledge_type_classification = _required_json(
        run_dir / "knowledge_type_classification_summary.json",
        "Final Graph Assembly requires knowledge_type_classification_summary.json from Phase 7b",
    )

    final_dir = run_dir / FINAL_GRAPH_DIR
    final_dir.mkdir(parents=True, exist_ok=True)

    lesson_segment_artifacts = _load_lesson_segment_artifacts(run_dir=run_dir, summary=segmentation_summary)
    validation_report = _validate_inputs(
        source_ledger=source_ledger,
        subject_merge=subject_merge,
        dependency_inference=dependency_inference,
        segmentation_summary=segmentation_summary,
        knowledge_type_classification=knowledge_type_classification,
        lesson_segment_artifacts=lesson_segment_artifacts,
    )
    _write_json(final_dir / "validation_report.json", validation_report)

    if validation_report["blocking_errors"]:
        raise StageBlockedError(
            "Final Graph Assembly blocked by validation: "
            + "; ".join(error["message"] for error in validation_report["blocking_errors"])
        )

    build_graph = _assemble_build_graph(
        source_ledger=source_ledger,
        subject_merge=subject_merge,
        dependency_inference=dependency_inference,
        segmentation_summary=segmentation_summary,
        knowledge_type_classification=knowledge_type_classification,
        lesson_segment_artifacts=lesson_segment_artifacts,
        validation_report=validation_report,
    )
    runtime_graph = _assemble_runtime_graph(build_graph)

    _write_json(final_dir / "build_graph.json", build_graph)
    _write_json(final_dir / "runtime_graph.json", runtime_graph)

    summary = {
        "concept_count": len(build_graph["concepts"]),
        "lesson_count": len(build_graph["lessons"]),
        "segmented_lesson_count": sum(1 for lesson in build_graph["lessons"] if lesson["segments"]),
        "runtime_lesson_count": len(runtime_graph["lessons"]),
        "dependency_edge_count": len(build_graph["dependency_edges"]),
        "blocking_error_count": len(validation_report["blocking_errors"]),
        "warning_count": len(validation_report["warnings"]),
    }
    return {
        "summary": summary,
        "artifact_path": final_dir / "runtime_graph.json",
        "artifact_paths": {
            "build_graph": f"{FINAL_GRAPH_DIR}/build_graph.json",
            "runtime_graph": f"{FINAL_GRAPH_DIR}/runtime_graph.json",
            "validation_report": f"{FINAL_GRAPH_DIR}/validation_report.json",
        },
    }


def _assemble_build_graph(
    *,
    source_ledger: dict[str, Any],
    subject_merge: dict[str, Any],
    dependency_inference: dict[str, Any],
    segmentation_summary: dict[str, Any],
    knowledge_type_classification: dict[str, Any],
    lesson_segment_artifacts: dict[str, dict[str, Any]],
    validation_report: dict[str, Any],
) -> dict[str, Any]:
    display_code_by_concept_id = _display_codes_for_concepts(subject_merge.get("concepts") or [], source_ledger)
    classifications_by_concept_id = _classifications_by_concept_id(knowledge_type_classification)
    return {
        "artifact_type": "build_graph",
        "schema_version": "build_graph.v0",
        "generated_at": _now(),
        "source_artifacts": {
            "source_ledger": "source_ledger.json",
            "subject_merge": "subject_merge.json",
            "dependency_inference": "dependency_inference.json",
            "lesson_segmentation_summary": "lesson_segmentation_summary.json",
            "knowledge_type_classification": "knowledge_type_classification_summary.json",
        },
        "subject": _subject_metadata(source_ledger=source_ledger, subject_merge=subject_merge),
        "source_inventory": _source_inventory(source_ledger),
        "concepts": [
            _build_concept(
                concept,
                display_code_by_concept_id=display_code_by_concept_id,
                knowledge_type_classification=classifications_by_concept_id[str(concept.get("concept_id") or "")],
            )
            for concept in subject_merge.get("concepts") or []
            if isinstance(concept, dict)
        ],
        "lessons": _build_lessons(
            source_ledger=source_ledger,
            lesson_segment_artifacts=lesson_segment_artifacts,
            display_code_by_concept_id=display_code_by_concept_id,
        ),
        "dependency_edges": deepcopy(dependency_inference.get("dependency_edges") or []),
        "dependency_deferral": {
            "deferred": bool(dependency_inference.get("deferred")),
            "deferral_reason": dependency_inference.get("deferral_reason"),
        },
        "quality": {
            "subject_merge_phase5b": subject_merge.get("phase5b_quality_audit"),
            "lesson_segmentation_summary": segmentation_summary.get("summary") or {},
            "knowledge_type_classification": {
                "status": knowledge_type_classification.get("status"),
                "summary": knowledge_type_classification.get("summary") or {},
                "quality_audit": knowledge_type_classification.get("quality_audit"),
            },
        },
        "validation": {
            "status": validation_report["status"],
            "blocking_error_count": len(validation_report["blocking_errors"]),
            "warning_count": len(validation_report["warnings"]),
        },
    }


def _assemble_runtime_graph(build_graph: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": "runtime_graph",
        "schema_version": "runtime_graph.v0",
        "generated_at": _now(),
        "subject": deepcopy(build_graph["subject"]),
        "concepts": [_runtime_concept(concept) for concept in build_graph.get("concepts") or []],
        "lessons": [_runtime_lesson(lesson) for lesson in build_graph.get("lessons") or []],
    }


def _build_concept(
    concept: dict[str, Any],
    *,
    display_code_by_concept_id: dict[str, str],
    knowledge_type_classification: dict[str, Any],
) -> dict[str, Any]:
    concept_id = str(concept.get("concept_id") or "")
    return {
        "concept_id": concept_id,
        "display_code": display_code_by_concept_id.get(concept_id),
        "label": concept.get("label"),
        "knowledge_type": knowledge_type_classification.get("knowledge_type"),
        "description": concept.get("teaching_description") or concept.get("description") or "",
        "coverage_criteria": [str(item) for item in concept.get("coverage_criteria") or [] if str(item).strip()],
        "common_misconceptions": deepcopy(concept.get("common_misconceptions") or []),
        "dependencies": {"blocking": [], "hard": [], "soft": []},
        "provenance": {
            "source_candidate_ids": deepcopy(concept.get("source_candidate_ids") or []),
            "lesson_reconciliation_refs": deepcopy(concept.get("lesson_reconciliation_refs") or []),
            "occurrences": deepcopy(concept.get("occurrences") or []),
            "depth": concept.get("depth"),
            "merge_rationale": concept.get("merge_rationale"),
            "knowledge_type_classification": deepcopy(knowledge_type_classification),
        },
    }


def _runtime_concept(concept: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept_id": concept["concept_id"],
        "display_code": concept.get("display_code"),
        "label": concept.get("label"),
        "knowledge_type": concept.get("knowledge_type"),
        "description": concept.get("description") or "",
        "coverage_criteria": deepcopy(concept.get("coverage_criteria") or []),
        "common_misconceptions": deepcopy(concept.get("common_misconceptions") or []),
        "dependencies": deepcopy(concept.get("dependencies") or {"blocking": [], "hard": [], "soft": []}),
    }


def _build_lessons(
    *,
    source_ledger: dict[str, Any],
    lesson_segment_artifacts: dict[str, dict[str, Any]],
    display_code_by_concept_id: dict[str, str],
) -> list[dict[str, Any]]:
    lessons: list[dict[str, Any]] = []
    for index, lesson in enumerate(source_ledger.get("lessons") or [], start=1):
        lesson_id = str(lesson.get("lesson_id") or "")
        display_code = str(lesson.get("display_code") or f"L{index:02d}")
        segments_artifact = lesson_segment_artifacts.get(lesson_id) or {}
        lessons.append(
            {
                "lesson_id": lesson_id,
                "display_code": display_code,
                "date": _normalize_date(lesson.get("date")),
                "title": lesson.get("title") or "",
                "description": lesson.get("description") or "",
                "professor": lesson.get("professor"),
                "workbook_metadata": {
                    "workbook_row_number": lesson.get("workbook_row_number"),
                    "axis": lesson.get("axis"),
                    "related_labels": deepcopy(lesson.get("related_labels") or []),
                },
                "segments": _build_segments(
                    lesson_display_code=display_code,
                    segments=segments_artifact.get("segments") or [],
                    display_code_by_concept_id=display_code_by_concept_id,
                ),
                "segmentation": {
                    "status": segments_artifact.get("status") or "skipped_no_concepts",
                    "repaired": bool(segments_artifact.get("repaired")),
                    "structural_warnings": deepcopy(segments_artifact.get("structural_warnings") or []),
                },
            }
        )
    return lessons


def _runtime_lesson(lesson: dict[str, Any]) -> dict[str, Any]:
    return {
        "lesson_id": lesson["lesson_id"],
        "display_code": lesson.get("display_code"),
        "date": lesson.get("date"),
        "title": lesson.get("title") or "",
        "description": lesson.get("description") or "",
        "segments": [
            {
                "segment_id": segment["segment_id"],
                "display_code": segment.get("display_code"),
                "label": segment.get("label") or "",
                "instructional_role": segment.get("instructional_role") or "teach",
                "concept_ids": deepcopy(segment.get("concept_ids") or []),
                "teaching_notes": segment.get("teaching_notes") or "",
            }
            for segment in lesson.get("segments") or []
        ],
    }


def _build_segments(
    *,
    lesson_display_code: str,
    segments: list[dict[str, Any]],
    display_code_by_concept_id: dict[str, str],
) -> list[dict[str, Any]]:
    final_segments = []
    for index, segment in enumerate(segments, start=1):
        concept_ids = [str(concept_id) for concept_id in segment.get("concept_ids") or []]
        final_segments.append(
            {
                "segment_id": segment.get("segment_id") or f"segment_{index:03d}",
                "display_code": f"{lesson_display_code}-S{index:02d}",
                "label": segment.get("label") or "",
                "instructional_role": segment.get("instructional_role") or "teach",
                "concept_ids": concept_ids,
                "concept_display_codes": [
                    display_code_by_concept_id[concept_id]
                    for concept_id in concept_ids
                    if concept_id in display_code_by_concept_id
                ],
                "teaching_notes": segment.get("teaching_notes") or "",
            }
        )
    return final_segments


def _validate_inputs(
    *,
    source_ledger: dict[str, Any],
    subject_merge: dict[str, Any],
    dependency_inference: dict[str, Any],
    segmentation_summary: dict[str, Any],
    knowledge_type_classification: dict[str, Any],
    lesson_segment_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    concepts = [concept for concept in subject_merge.get("concepts") or [] if isinstance(concept, dict)]
    concept_ids = [str(concept.get("concept_id") or "") for concept in concepts]
    concept_id_set = set(concept_ids)
    if len(concept_id_set) != len(concept_ids):
        errors.append({"code": "duplicate_concept_id", "message": "Concept IDs must be unique."})

    for concept in concepts:
        concept_id = str(concept.get("concept_id") or "")
        if not concept_id:
            errors.append({"code": "missing_concept_id", "message": "Concept is missing concept_id."})
            continue
        for field in ("label",):
            if not concept.get(field):
                errors.append({"code": f"missing_{field}", "message": f"Concept {concept_id} is missing {field}.", "concept_id": concept_id})
        if not (concept.get("teaching_description") or concept.get("description")):
            errors.append({"code": "missing_description", "message": f"Concept {concept_id} is missing description.", "concept_id": concept_id})
        if not concept.get("coverage_criteria"):
            errors.append({"code": "missing_coverage_criteria", "message": f"Concept {concept_id} is missing Coverage Criteria.", "concept_id": concept_id})

    _validate_knowledge_type_classification(
        knowledge_type_classification=knowledge_type_classification,
        concept_ids=concept_ids,
        errors=errors,
    )

    dependency_edges = dependency_inference.get("dependency_edges")
    if dependency_edges != []:
        errors.append({"code": "v0_dependencies_not_empty", "message": "V0 Runtime Graph Export requires an empty dependency edge list."})

    concepts_by_lesson = _concept_ids_by_lesson(concepts)
    summary_lessons_by_id = {
        str(item.get("lesson_id") or ""): item
        for item in segmentation_summary.get("lessons") or []
        if isinstance(item, dict)
    }
    if int((segmentation_summary.get("summary") or {}).get("unrepaired_count") or 0) > 0:
        errors.append({"code": "unrepaired_lesson_segmentation", "message": "Lesson Segmentation has unrepaired Lessons."})

    for lesson in source_ledger.get("lessons") or []:
        lesson_id = str(lesson.get("lesson_id") or "")
        lesson_concepts = concepts_by_lesson.get(lesson_id, set())
        summary_item = summary_lessons_by_id.get(lesson_id)
        segment_artifact = lesson_segment_artifacts.get(lesson_id)
        if not lesson_concepts:
            warnings.append(
                {
                    "code": "lesson_without_concepts",
                    "message": "Lesson has no Concepts and was exported without Segments.",
                    "lesson_id": lesson_id,
                }
            )
            continue
        if not summary_item or not segment_artifact:
            errors.append({"code": "missing_lesson_segments", "message": "Lesson has Concepts but no Lesson Segments artifact.", "lesson_id": lesson_id})
            continue
        segment_concept_ids = [
            str(concept_id)
            for segment in segment_artifact.get("segments") or []
            for concept_id in segment.get("concept_ids") or []
        ]
        segment_concept_id_set = set(segment_concept_ids)
        if len(segment_concept_ids) != len(segment_concept_id_set):
            errors.append({"code": "duplicate_segment_concept", "message": "Lesson Segments repeat a Concept ID.", "lesson_id": lesson_id})
        if segment_concept_id_set != lesson_concepts:
            errors.append({"code": "segment_concept_mismatch", "message": "Lesson Segments must cover every Lesson Concept exactly once.", "lesson_id": lesson_id})
        unknown_segment_concepts = sorted(segment_concept_id_set - concept_id_set)
        if unknown_segment_concepts:
            errors.append(
                {
                    "code": "unknown_segment_concept",
                    "message": "Lesson Segments reference unknown Concept IDs.",
                    "lesson_id": lesson_id,
                    "concept_ids": unknown_segment_concepts,
                }
            )
        for segment in segment_artifact.get("segments") or []:
            if not segment.get("concept_ids"):
                errors.append({"code": "empty_segment", "message": "Lesson Segment has no Concepts.", "lesson_id": lesson_id})
            if len(segment.get("concept_ids") or []) >= 5:
                warnings.append(
                    {
                        "code": "large_segment",
                        "message": "Lesson Segment has five or more Concepts.",
                        "lesson_id": lesson_id,
                        "segment_id": segment.get("segment_id"),
                    }
                )

    status = "failed" if errors else ("passed_with_warnings" if warnings else "passed")
    return {
        "artifact_type": "validation_report",
        "schema_version": "validation_report.v0",
        "generated_at": _now(),
        "status": status,
        "blocking_errors": errors,
        "warnings": warnings,
        "summary": {
            "blocking_error_count": len(errors),
            "warning_count": len(warnings),
        },
    }


def _load_lesson_segment_artifacts(*, run_dir: Path, summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for artifact_ref in summary.get("artifacts") or []:
        artifact_path = run_dir / str(artifact_ref)
        if not artifact_path.is_file():
            continue
        artifact = _read_json(artifact_path)
        lesson_id = str(artifact.get("lesson_id") or "")
        if lesson_id:
            artifacts[lesson_id] = artifact
    return artifacts


def _validate_knowledge_type_classification(
    *,
    knowledge_type_classification: dict[str, Any],
    concept_ids: list[str],
    errors: list[dict[str, Any]],
) -> None:
    if knowledge_type_classification.get("artifact_type") != "knowledge_type_classification_summary":
        errors.append(
            {
                "code": "invalid_knowledge_type_classification_artifact",
                "message": "Knowledge Type Classification artifact_type is invalid.",
            }
        )
    if knowledge_type_classification.get("schema_version") != "knowledge_type_classification_summary.v0":
        errors.append(
            {
                "code": "invalid_knowledge_type_classification_schema",
                "message": "Knowledge Type Classification schema_version is invalid.",
            }
        )
    if knowledge_type_classification.get("status") not in {"reliable", "repaired"}:
        errors.append(
            {
                "code": "unreliable_knowledge_type_classification",
                "message": "Knowledge Type Classification must be reliable or repaired.",
            }
        )
    if int((knowledge_type_classification.get("summary") or {}).get("unrepaired_count") or 0) > 0:
        errors.append(
            {
                "code": "unrepaired_knowledge_type_classification",
                "message": "Knowledge Type Classification has unrepaired Concepts.",
            }
        )

    classifications = knowledge_type_classification.get("classifications")
    if not isinstance(classifications, list):
        errors.append(
            {
                "code": "missing_knowledge_type_classifications",
                "message": "Knowledge Type Classification must include classifications.",
            }
        )
        return

    seen: list[str] = []
    concept_id_set = set(concept_ids)
    for classification in classifications:
        if not isinstance(classification, dict):
            errors.append(
                {
                    "code": "invalid_knowledge_type_classification",
                    "message": "Knowledge Type Classification entries must be objects.",
                }
            )
            continue
        concept_id = str(classification.get("concept_id") or "")
        if not concept_id:
            errors.append(
                {
                    "code": "missing_classified_concept_id",
                    "message": "Knowledge Type Classification entry is missing concept_id.",
                }
            )
            continue
        seen.append(concept_id)
        if concept_id not in concept_id_set:
            errors.append(
                {
                    "code": "unknown_classified_concept",
                    "message": "Knowledge Type Classification references an unknown Concept ID.",
                    "concept_id": concept_id,
                }
            )
        knowledge_type = classification.get("knowledge_type")
        if knowledge_type not in ALLOWED_KNOWLEDGE_TYPES:
            errors.append(
                {
                    "code": "invalid_knowledge_type",
                    "message": f"Concept {concept_id} has invalid classified knowledge_type.",
                    "concept_id": concept_id,
                }
            )
        if not str(classification.get("rationale") or "").strip():
            errors.append(
                {
                    "code": "missing_knowledge_type_rationale",
                    "message": f"Concept {concept_id} is missing knowledge_type classification rationale.",
                    "concept_id": concept_id,
                }
            )

    duplicates = sorted({concept_id for concept_id in seen if seen.count(concept_id) > 1})
    if duplicates:
        errors.append(
            {
                "code": "duplicate_knowledge_type_classification",
                "message": "Knowledge Type Classification repeats Concept IDs.",
                "concept_ids": duplicates,
            }
        )
    missing = [concept_id for concept_id in concept_ids if concept_id not in seen]
    if missing:
        errors.append(
            {
                "code": "missing_knowledge_type_classification",
                "message": "Knowledge Type Classification must classify every Concept.",
                "concept_ids": missing,
            }
        )


def _classifications_by_concept_id(knowledge_type_classification: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(classification.get("concept_id") or ""): classification
        for classification in knowledge_type_classification.get("classifications") or []
        if isinstance(classification, dict)
    }


def _concept_ids_by_lesson(concepts: list[dict[str, Any]]) -> dict[str, set[str]]:
    by_lesson: dict[str, set[str]] = {}
    for concept in concepts:
        concept_id = str(concept.get("concept_id") or "")
        if not concept_id:
            continue
        for occurrence in concept.get("occurrences") or []:
            lesson_id = str((occurrence.get("lesson") or {}).get("lesson_id") or "")
            if lesson_id:
                by_lesson.setdefault(lesson_id, set()).add(concept_id)
    return by_lesson


def _display_codes_for_concepts(concepts: list[dict[str, Any]], source_ledger: dict[str, Any]) -> dict[str, str]:
    subject_code = _subject_display_prefix(source_ledger)
    return {
        str(concept.get("concept_id")): f"{subject_code}-{index:03d}"
        for index, concept in enumerate(concepts, start=1)
        if concept.get("concept_id")
    }


def _subject_display_prefix(source_ledger: dict[str, Any]) -> str:
    subject_id = str(source_ledger.get("subject_id") or "CG")
    if subject_id.isupper() and len(subject_id) <= 6:
        return subject_id
    return re.sub(r"[^A-Z0-9]+", "", subject_id.upper())[:6] or "CG"


def _subject_metadata(*, source_ledger: dict[str, Any], subject_merge: dict[str, Any]) -> dict[str, Any]:
    professors = _stable_unique(
        [
            str(lesson.get("professor") or "").strip()
            for lesson in source_ledger.get("lessons") or []
            if str(lesson.get("professor") or "").strip()
        ]
    )
    return {
        "course_id": source_ledger.get("course_id") or subject_merge.get("course_id"),
        "module_id": source_ledger.get("module_id") or subject_merge.get("module_id"),
        "pipeline_subject_id": source_ledger.get("subject_id") or subject_merge.get("subject_id"),
        "title": _subject_title(source_ledger),
        "language": "pt-BR",
        "professors": professors,
    }


def _subject_title(source_ledger: dict[str, Any]) -> str:
    subject_id = str(source_ledger.get("subject_id") or "Concept Graph")
    if subject_id == "COM":
        return "Computacao"
    return subject_id


def _source_inventory(source_ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        "inputs": deepcopy(source_ledger.get("inputs") or {}),
        "summary": deepcopy(source_ledger.get("summary") or {}),
        "self_studies": deepcopy(source_ledger.get("self_studies") or []),
    }


def _normalize_date(value: Any) -> str:
    text = str(value or "").strip()
    match = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    return text


def _stable_unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _required_json(path: Path, message: str) -> dict[str, Any]:
    if not path.is_file():
        raise StageBlockedError(message)
    return _read_json(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
