from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from concept_graph_creation.runtime.generation import (
    ledger_fingerprint,
    matches_ledger_fingerprint,
)
from concept_graph_creation.runtime.stage_runner import StageBlockedError
from concept_graph_creation.stages.source_ledger import read_workbook_source_extracted_at


ALLOWED_KNOWLEDGE_TYPES = {"conceptual", "procedural", "factual", "applied"}
FINAL_GRAPH_DIR = "final_graph"
SELF_STUDY_RESOURCE_ID_PREFIX = "self-study-"
_SELF_STUDY_PATH_RE = re.compile(r"(?:^|/)self_studies/([^/]+)/")
_BOOK_NAVIGATION_PATTERNS = (
    re.compile(r"\bcap[íi]tulo\s+\d+[^.;)]*", re.IGNORECASE),
    re.compile(r"\bexerc[íi]cio\s+\d+[^;.)]*", re.IGNORECASE),
    re.compile(r"\bp[áa]g(?:ina|\.|:)?\s*\d+(?:\s*(?:a|até|-)\s*\d+)?", re.IGNORECASE),
)


def run_final_graph_assembly_phase(*, run_dir: Path, cg_pipeline_root: Path | None = None) -> dict[str, Any]:
    source_ledger = _required_json(run_dir / "source_ledger.json", "Final Graph Assembly requires source_ledger.json")
    current_ledger_fingerprint = ledger_fingerprint(source_ledger)
    source_ledger = _source_ledger_with_source_extracted_at(
        source_ledger,
        cg_pipeline_root=cg_pipeline_root,
    )
    subject_merge = _required_json(run_dir / "subject_merge.json", "Final Graph Assembly requires subject_merge.json")
    dependency_inference = _required_json(
        run_dir / "dependency_inference.json",
        "Final Graph Assembly requires dependency_inference.json from 07-dependency",
    )
    segmentation_summary = _required_json(
        run_dir / "lesson_segmentation_summary.json",
        "Final Graph Assembly requires lesson_segmentation_summary.json from 08-lesson-segmentation",
    )
    knowledge_type_classification = _required_json(
        run_dir / "knowledge_type_classification_summary.json",
        "Final Graph Assembly requires knowledge_type_classification_summary.json from 09-knowledge-type",
    )

    final_dir = run_dir / FINAL_GRAPH_DIR
    final_dir.mkdir(parents=True, exist_ok=True)

    lesson_segment_artifacts = _load_lesson_segment_artifacts(run_dir=run_dir, summary=segmentation_summary)
    _ensure_current_ledger_generation(
        current_ledger_fingerprint=current_ledger_fingerprint,
        subject_merge=subject_merge,
        knowledge_type_classification=knowledge_type_classification,
        lesson_segment_artifacts=lesson_segment_artifacts,
    )
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
        current_ledger_fingerprint=current_ledger_fingerprint,
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
        "ledger_fingerprint": current_ledger_fingerprint,
        "artifact_path": final_dir / "runtime_graph.json",
        "artifact_paths": {
            "build_graph": f"{FINAL_GRAPH_DIR}/build_graph.json",
            "runtime_graph": f"{FINAL_GRAPH_DIR}/runtime_graph.json",
            "validation_report": f"{FINAL_GRAPH_DIR}/validation_report.json",
        },
    }


def _ensure_current_ledger_generation(
    *,
    current_ledger_fingerprint: str,
    subject_merge: dict[str, Any],
    knowledge_type_classification: dict[str, Any],
    lesson_segment_artifacts: dict[str, dict[str, Any]],
) -> None:
    stale_artifacts: list[str] = []
    if not matches_ledger_fingerprint(subject_merge, current_ledger_fingerprint):
        stale_artifacts.append("subject_merge.json")
    for lesson_id in sorted(lesson_segment_artifacts):
        if not matches_ledger_fingerprint(lesson_segment_artifacts[lesson_id], current_ledger_fingerprint):
            stale_artifacts.append(f"lessons/{lesson_id}/lesson_segments.json")
    if not matches_ledger_fingerprint(knowledge_type_classification, current_ledger_fingerprint):
        stale_artifacts.append("knowledge_type_classification_summary.json")
    if stale_artifacts:
        raise StageBlockedError(
            "Final Graph Assembly found artifacts from a different source ledger generation "
            f"(expected ledger_fingerprint {current_ledger_fingerprint}): "
            + ", ".join(stale_artifacts)
            + ". Wipe the creation artifacts for this run or rerun the producing phases "
            "(06-subject-merge, 08-lesson-segmentation, 09-knowledge-type) before assembling."
        )


def _assemble_build_graph(
    *,
    source_ledger: dict[str, Any],
    subject_merge: dict[str, Any],
    dependency_inference: dict[str, Any],
    segmentation_summary: dict[str, Any],
    knowledge_type_classification: dict[str, Any],
    lesson_segment_artifacts: dict[str, dict[str, Any]],
    validation_report: dict[str, Any],
    current_ledger_fingerprint: str,
) -> dict[str, Any]:
    display_code_by_concept_id = _display_codes_for_concepts(subject_merge.get("concepts") or [], source_ledger)
    classifications_by_concept_id = _classifications_by_concept_id(knowledge_type_classification)
    return {
        "artifact_type": "build_graph",
        "schema_version": "build_graph.v0",
        "generated_at": _now(),
        "ledger_fingerprint": current_ledger_fingerprint,
        "source_extracted_at": source_ledger.get("source_extracted_at"),
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


def assemble_runtime_graph_from_build_graph(
    build_graph: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return _assemble_runtime_graph(build_graph, generated_at=generated_at)


def _assemble_runtime_graph(build_graph: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    resources_by_id = _self_study_resources_by_id(build_graph)
    resource_refs_by_concept_id = _self_study_resource_refs_by_concept_id(
        build_graph,
        resources_by_id=resources_by_id,
    )
    runtime_lessons = [
        _runtime_lesson(
            lesson,
            resource_refs_by_concept_id=resource_refs_by_concept_id,
            resources_by_id=resources_by_id,
        )
        for lesson in build_graph.get("lessons") or []
    ]
    source_extracted_at = _source_extracted_at_from_build_graph(build_graph)
    used_resource_ids = {
        resource_id
        for lesson in runtime_lessons
        for segment in lesson.get("segments") or []
        for resource_id in segment.get("self_study_resource_ids") or []
    }
    return {
        "artifact_type": "runtime_graph",
        "schema_version": "runtime_graph.v0",
        "generated_at": generated_at or _now(),
        **(
            {"ledger_fingerprint": build_graph["ledger_fingerprint"]}
            if build_graph.get("ledger_fingerprint")
            else {}
        ),
        **({"source_extracted_at": source_extracted_at} if source_extracted_at else {}),
        "subject": deepcopy(build_graph["subject"]),
        "concepts": [_runtime_concept(concept) for concept in build_graph.get("concepts") or []],
        "lessons": runtime_lessons,
        "self_study_resources": [
            resources_by_id[resource_id]
            for resource_id in sorted(used_resource_ids, key=lambda item: _resource_sort_key(resources_by_id[item]))
        ],
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


def _runtime_lesson(
    lesson: dict[str, Any],
    *,
    resource_refs_by_concept_id: dict[str, list[dict[str, Any]]],
    resources_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "lesson_id": lesson["lesson_id"],
        "display_code": lesson.get("display_code"),
        "date": lesson.get("date"),
        "title": lesson.get("title") or "",
        "description": lesson.get("description") or "",
        "segments": [
            _runtime_segment(
                segment,
                resource_refs_by_concept_id=resource_refs_by_concept_id,
                resources_by_id=resources_by_id,
            )
            for segment in lesson.get("segments") or []
        ],
    }


def _runtime_segment(
    segment: dict[str, Any],
    *,
    resource_refs_by_concept_id: dict[str, list[dict[str, Any]]],
    resources_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    resource_refs = _segment_self_study_resource_refs(
        segment,
        resource_refs_by_concept_id=resource_refs_by_concept_id,
        resources_by_id=resources_by_id,
    )
    return {
        "segment_id": segment["segment_id"],
        "display_code": segment.get("display_code"),
        "label": segment.get("label") or "",
        "instructional_role": segment.get("instructional_role") or "teach",
        "concept_ids": deepcopy(segment.get("concept_ids") or []),
        "teaching_notes": segment.get("teaching_notes") or "",
        "self_study_resource_ids": [ref["resource_id"] for ref in resource_refs],
        "self_study_resource_refs": resource_refs,
    }


def _self_study_resources_by_id(build_graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    resources: dict[str, dict[str, Any]] = {}
    inventory = build_graph.get("source_inventory") or {}
    for self_study in inventory.get("self_studies") or []:
        if not isinstance(self_study, dict):
            continue
        self_study_id = str(self_study.get("self_study_id") or "").strip()
        if not self_study_id:
            continue
        if self_study.get("source_body_status") == "excluded_activity_only_self_study":
            continue
        if self_study.get("exclusion_reason"):
            continue

        metadata = self_study.get("workbook_metadata") if isinstance(self_study.get("workbook_metadata"), dict) else {}
        source_body = self_study.get("source_body") if isinstance(self_study.get("source_body"), dict) else {}
        resource_code = str(metadata.get("resource_code") or "").strip()
        source_type = str(source_body.get("type") or "").strip()
        if not source_type:
            source_type = "book" if resource_code else _resource_type_from_url(metadata.get("url"))

        url = _clean_resource_url(metadata.get("url"))
        if not url and not resource_code:
            continue

        resource: dict[str, Any] = {
            "resource_id": _self_study_resource_id(self_study_id),
            "self_study_id": self_study_id,
            "title": str(metadata.get("title") or source_body.get("source_name") or f"Self-study {self_study_id}").strip(),
            "source_type": source_type or "resource",
        }
        if url:
            resource["url"] = url
        if resource_code:
            resource["resource_code"] = resource_code
            navigation_hint = _book_navigation_hint(metadata)
            if navigation_hint:
                resource["navigation_hint"] = navigation_hint

        optional_fields = {
            "week": metadata.get("week"),
            "sort": metadata.get("sort"),
            "required": metadata.get("required"),
            "grade_weight": metadata.get("grade_weight"),
            "related_labels": metadata.get("related_labels"),
        }
        for key, value in optional_fields.items():
            if value not in (None, "", []):
                resource[key] = deepcopy(value)

        resources[resource["resource_id"]] = resource
    return resources


def _self_study_resource_refs_by_concept_id(
    build_graph: dict[str, Any],
    *,
    resources_by_id: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    refs_by_concept_id: dict[str, list[dict[str, Any]]] = {}
    for concept in build_graph.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        concept_id = str(concept.get("concept_id") or "").strip()
        if not concept_id:
            continue
        refs_by_resource_id: dict[str, dict[str, Any]] = {}
        provenance = concept.get("provenance") if isinstance(concept.get("provenance"), dict) else {}
        for reconciliation_ref in provenance.get("lesson_reconciliation_refs") or []:
            if not isinstance(reconciliation_ref, dict):
                continue
            for evidence in reconciliation_ref.get("evidence") or []:
                if not isinstance(evidence, dict):
                    continue
                resource_id = _evidence_resource_id(evidence)
                if not resource_id or resource_id not in resources_by_id:
                    continue
                ref = refs_by_resource_id.setdefault(
                    resource_id,
                    {
                        "resource_id": resource_id,
                        "concept_ids": [],
                        "evidence_types": [],
                        "locators": [],
                    },
                )
                _append_unique(ref["concept_ids"], concept_id)
                evidence_type = evidence.get("evidence_type") or (evidence.get("candidate_ref") or {}).get("evidence_type")
                if evidence_type:
                    _append_unique(ref["evidence_types"], str(evidence_type))
                for anchor in evidence.get("anchors") or evidence.get("metadata_anchors") or []:
                    locator = _runtime_locator(anchor)
                    if locator and locator not in ref["locators"]:
                        ref["locators"].append(locator)
        refs_by_concept_id[concept_id] = [
            _compact_resource_ref(ref)
            for ref in sorted(
                refs_by_resource_id.values(),
                key=lambda item: _resource_sort_key(resources_by_id[item["resource_id"]]),
            )
        ]
    return refs_by_concept_id


def _segment_self_study_resource_refs(
    segment: dict[str, Any],
    *,
    resource_refs_by_concept_id: dict[str, list[dict[str, Any]]],
    resources_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    refs_by_resource_id: dict[str, dict[str, Any]] = {}
    for concept_id in [str(item) for item in segment.get("concept_ids") or []]:
        for concept_ref in resource_refs_by_concept_id.get(concept_id) or []:
            resource_id = concept_ref["resource_id"]
            ref = refs_by_resource_id.setdefault(
                resource_id,
                {
                    "resource_id": resource_id,
                    "concept_ids": [],
                    "evidence_types": [],
                    "locators": [],
                },
            )
            for ref_concept_id in concept_ref.get("concept_ids") or []:
                _append_unique(ref["concept_ids"], str(ref_concept_id))
            for evidence_type in concept_ref.get("evidence_types") or []:
                _append_unique(ref["evidence_types"], str(evidence_type))
            for locator in concept_ref.get("locators") or []:
                if locator not in ref["locators"]:
                    ref["locators"].append(deepcopy(locator))
    return [
        _compact_resource_ref(ref)
        for ref in sorted(
            refs_by_resource_id.values(),
            key=lambda item: _resource_sort_key(resources_by_id[item["resource_id"]]),
        )
    ]


def _compact_resource_ref(ref: dict[str, Any]) -> dict[str, Any]:
    compact = {"resource_id": ref["resource_id"]}
    if ref.get("concept_ids"):
        compact["concept_ids"] = ref["concept_ids"]
    if ref.get("evidence_types"):
        compact["evidence_types"] = ref["evidence_types"]
    if ref.get("locators"):
        compact["locators"] = ref["locators"]
    return compact


def _evidence_resource_id(evidence: dict[str, Any]) -> str | None:
    candidate_ref = evidence.get("candidate_ref") if isinstance(evidence.get("candidate_ref"), dict) else {}
    self_study_id = str(candidate_ref.get("self_study_id") or "").strip()
    if not self_study_id:
        self_study_id = _self_study_id_from_paths(candidate_ref, evidence)
    if not self_study_id:
        return None
    return _self_study_resource_id(self_study_id)


def _self_study_id_from_paths(*items: Any) -> str:
    for item in items:
        if not isinstance(item, dict):
            continue
        for path_field in ("artifact_path", "path"):
            match = _SELF_STUDY_PATH_RE.search(str(item.get(path_field) or ""))
            if match:
                return match.group(1)
    return ""


def _self_study_resource_id(self_study_id: str) -> str:
    return f"{SELF_STUDY_RESOURCE_ID_PREFIX}{self_study_id}"


def _runtime_locator(anchor: Any) -> dict[str, str] | None:
    if not isinstance(anchor, dict):
        return None
    kind = str(anchor.get("kind") or "").strip()
    locator = str(anchor.get("locator") or "").strip()
    if not kind or not locator:
        return None
    return {"kind": kind, "locator": locator}


def _clean_resource_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith(("http://", "https://")) and "?" in text:
        base, query = text.split("?", 1)
        query = re.sub(r"\s+e\s+(?=[A-Za-z0-9_.%-]+=)", "&", query)
        text = f"{base}?{query}"
    return text


def _resource_type_from_url(value: Any) -> str:
    url = str(value or "").lower()
    if "youtube.com" in url or "youtu.be" in url:
        return "video"
    if url:
        return "article"
    return "resource"


def _book_navigation_hint(metadata: dict[str, Any]) -> str:
    text = " ".join(
        str(metadata.get(field) or "").strip()
        for field in ("title", "description")
        if str(metadata.get(field) or "").strip()
    )
    hints: list[str] = []
    spans: list[tuple[int, int]] = []
    for pattern in _BOOK_NAVIGATION_PATTERNS:
        for match in pattern.finditer(text):
            span = match.span()
            if any(span[0] >= existing[0] and span[1] <= existing[1] for existing in spans):
                continue
            spans.append(span)
            _append_unique(hints, re.sub(r"\s+", " ", match.group(0)).strip(" ;,.-"))
    return "; ".join(hints)


def _resource_sort_key(resource: dict[str, Any]) -> tuple[int, int, str, str]:
    return (
        _sort_number(resource.get("week"), default=999),
        _sort_number(resource.get("sort"), default=999),
        str(resource.get("title") or ""),
        str(resource.get("resource_id") or ""),
    )


def _sort_number(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _append_unique(values: list[Any], value: Any) -> None:
    if value in values:
        return
    values.append(value)


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
    notices: list[dict[str, Any]] = []

    if not source_ledger.get("source_extracted_at"):
        errors.append(
            {
                "code": "missing_source_extracted_at",
                "message": "Source Ledger must include source_extracted_at before final graph export.",
            }
        )

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
    elif dependency_inference.get("deferred") is True:
        notices.append(
            {
                "code": "v0_dependency_inference_deferred",
                "message": (
                    "Dependency inference was intentionally deferred for v0; no "
                    "dependency edges were created. University Lesson order remains "
                    "the prerequisite structure."
                ),
                "dependency_edge_count": 0,
            }
        )

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
        "notices": notices,
        "summary": {
            "blocking_error_count": len(errors),
            "warning_count": len(warnings),
            "notice_count": len(notices),
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
        if not isinstance(knowledge_type, str) or not knowledge_type.strip():
            errors.append(
                {
                    "code": "missing_knowledge_type",
                    "message": f"Concept {concept_id} is missing knowledge_type.",
                    "concept_id": concept_id,
                }
            )
        elif knowledge_type not in ALLOWED_KNOWLEDGE_TYPES:
            errors.append(
                {
                    "code": "unsupported_knowledge_type",
                    "message": (
                        f"Concept {concept_id} has unsupported knowledge_type "
                        f"{knowledge_type!r}."
                    ),
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
        "source_extracted_at": source_ledger.get("source_extracted_at"),
        "inputs": deepcopy(source_ledger.get("inputs") or {}),
        "summary": deepcopy(source_ledger.get("summary") or {}),
        "self_studies": deepcopy(source_ledger.get("self_studies") or []),
    }


def _source_ledger_with_source_extracted_at(
    source_ledger: dict[str, Any],
    *,
    cg_pipeline_root: Path | None,
) -> dict[str, Any]:
    if source_ledger.get("source_extracted_at"):
        return source_ledger
    if cg_pipeline_root is None:
        return source_ledger

    workbook_path_value = (source_ledger.get("inputs") or {}).get("workbook_path")
    if not workbook_path_value:
        return source_ledger

    workbook_path = Path(str(workbook_path_value))
    if not workbook_path.is_absolute():
        workbook_path = cg_pipeline_root / workbook_path

    source_ledger = deepcopy(source_ledger)
    try:
        source_ledger["source_extracted_at"] = read_workbook_source_extracted_at(workbook_path)
    except Exception as exc:
        raise StageBlockedError(
            f"Final Graph Assembly could not read source workbook creation date: {workbook_path}"
        ) from exc
    return source_ledger


def _source_extracted_at_from_build_graph(build_graph: dict[str, Any]) -> str | None:
    source_extracted_at = build_graph.get("source_extracted_at")
    if source_extracted_at:
        return str(source_extracted_at)
    source_inventory = build_graph.get("source_inventory")
    if isinstance(source_inventory, dict) and source_inventory.get("source_extracted_at"):
        return str(source_inventory["source_extracted_at"])
    return None


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
