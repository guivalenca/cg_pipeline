from __future__ import annotations

import concurrent.futures
import json
import re
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


ALLOWED_KNOWLEDGE_TYPES = {"conceptual", "procedural", "factual", "applied"}

_PROMPT_FILES = {
    "classify": "classify.md",
    "quality_audit": "quality_audit.md",
    "quality_repair": "quality_repair.md",
}

_AUDIT_SCORE_FIELDS = (
    "taxonomy_fit",
    "teaching_mode_alignment",
    "segment_consistency",
    "factual_boundary",
    "applied_boundary",
)

_AUDIT_FLAGS = {
    "definition_as_procedural",
    "tool_execution_as_conceptual",
    "historical_name_as_applied",
    "applied_underuse",
    "factual_absence",
    "segment_inconsistency",
    "cross_segment_conflict",
    "taxonomy_mismatch",
}

_REPAIR_REASONS = {
    "cross_segment_conflict",
    "taxonomy_mismatch",
    "definition_as_procedural",
    "tool_execution_as_conceptual",
    "historical_name_as_applied",
    "applied_underuse",
    "factual_absence",
    "segment_inconsistency",
}


@dataclass(frozen=True)
class _KnowledgeTypePrompt:
    text: str
    path_ref: str


@dataclass(frozen=True)
class _SegmentClassificationTask:
    order: int
    lesson_id: str
    segment_id: str
    segment_label: str
    run_dir: Path
    segment_dir: Path
    artifact_path: str
    lesson: dict[str, Any]
    concept_ids: list[str]
    concepts: list[dict[str, Any]]


@dataclass(frozen=True)
class _SegmentClassificationResult:
    order: int
    lesson_id: str
    segment_id: str
    segment_label: str
    artifact_path: Path
    artifact_path_ref: str
    artifact: dict[str, Any]
    repaired: bool


def run_knowledge_type_classification_phase(
    *,
    run_dir: Path,
    model_call: ModelCall,
    router: ModelRouter | None = None,
    prompt_path: Path | None = None,
    classification_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    audit_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    quality_repair_model_route: str = PRO_ROUTE_ALIAS,
    format_repair_model_route: str = FLASH_ROUTE_ALIAS,
    concurrency: int = 6,
) -> dict[str, Any]:
    source_ledger_path = run_dir / "source_ledger.json"
    subject_merge_path = run_dir / "subject_merge.json"
    segmentation_summary_path = run_dir / "lesson_segmentation_summary.json"
    if not source_ledger_path.is_file():
        raise StageBlockedError("Knowledge Type Classification requires source_ledger.json")
    if not subject_merge_path.is_file():
        raise StageBlockedError("Knowledge Type Classification requires subject_merge.json from Phase 5")
    if not segmentation_summary_path.is_file():
        raise StageBlockedError(
            "Knowledge Type Classification requires lesson_segmentation_summary.json from Phase 7"
        )

    source_ledger = _read_json(source_ledger_path)
    subject_merge = _read_json(subject_merge_path)
    segmentation_summary = _read_json(segmentation_summary_path)
    prompts = _load_prompts(prompt_path)
    taxonomy = _load_knowledge_type_taxonomy()
    runner = StageRunner(router=router or ModelRouter.default(), model_call=model_call)

    lesson_segment_artifacts = _load_lesson_segment_artifacts(run_dir=run_dir, summary=segmentation_summary)
    tasks = _build_segment_classification_tasks(
        run_dir=run_dir,
        source_ledger=source_ledger,
        subject_merge=subject_merge,
        lesson_segment_artifacts=lesson_segment_artifacts,
    )
    if not tasks and _subject_concepts(subject_merge):
        raise StageBlockedError("Knowledge Type Classification requires at least one Lesson Segment")

    segment_results = _run_segment_classification_tasks(
        tasks=tasks,
        runner=runner,
        prompt=prompts["classify"],
        taxonomy=taxonomy,
        model_route=classification_model_route,
        format_repair_model_route=format_repair_model_route,
        concurrency=concurrency,
    )
    aggregate = _aggregate_segment_classifications(
        subject_merge=subject_merge,
        segment_results=segment_results,
    )
    audit_count = 0
    repair_count = 0
    repaired = False

    audit = _run_quality_audit(
        run_dir=run_dir,
        aggregate=aggregate,
        taxonomy=taxonomy,
        prompt=prompts["quality_audit"],
        runner=runner,
        model_route=audit_model_route,
        format_repair_model_route=format_repair_model_route,
    )
    audit_count += 1

    repair_artifact_path: Path | None = None
    max_quality_repair_rounds = 3
    while audit["reliability"] == "repair_required" and repair_count < max_quality_repair_rounds:
        target_concept_ids = _target_concept_ids_from_audit(audit=audit, aggregate=aggregate)
        if not target_concept_ids:
            break
        repair_artifact_path = _run_quality_repair(
            run_dir=run_dir,
            aggregate=aggregate,
            target_concept_ids=target_concept_ids,
            quality_audit=audit,
            taxonomy=taxonomy,
            prompt=prompts["quality_repair"],
            runner=runner,
            model_route=quality_repair_model_route,
            format_repair_model_route=format_repair_model_route,
        )
        aggregate = _apply_quality_repair(
            aggregate=aggregate,
            repair_decision=_read_json(repair_artifact_path),
            repair_artifact_path=str(repair_artifact_path.relative_to(run_dir)),
        )
        repaired = True
        repair_count += 1
        audit = _run_quality_audit(
            run_dir=run_dir,
            aggregate=aggregate,
            taxonomy=taxonomy,
            prompt=prompts["quality_audit"],
            runner=runner,
            model_route=audit_model_route,
            format_repair_model_route=format_repair_model_route,
        )
        audit_count += 1

    status = "reliable" if audit["reliability"] == "reliable" else "repair_required"
    if repaired and status == "reliable":
        status = "repaired"

    summary_artifact = _build_summary_artifact(
        aggregate=aggregate,
        taxonomy=taxonomy,
        prompts=prompts,
        segment_results=segment_results,
        status=status,
        audit=audit,
        audit_count=audit_count,
        repair_count=repair_count,
        repair_artifact_path=str(repair_artifact_path.relative_to(run_dir)) if repair_artifact_path else None,
        classification_model_route=classification_model_route,
        audit_model_route=audit_model_route,
        quality_repair_model_route=quality_repair_model_route,
        concurrency=concurrency,
    )
    output_path = run_dir / "knowledge_type_classification_summary.json"
    output_path.write_text(json.dumps(summary_artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "summary": summary_artifact["summary"],
        "artifact_path": output_path,
        "classification_model_route": classification_model_route,
        "audit_model_route": audit_model_route,
        "quality_repair_model_route": quality_repair_model_route,
        "concurrency": concurrency,
        "status": status,
    }


def _build_segment_classification_tasks(
    *,
    run_dir: Path,
    source_ledger: dict[str, Any],
    subject_merge: dict[str, Any],
    lesson_segment_artifacts: dict[str, dict[str, Any]],
) -> list[_SegmentClassificationTask]:
    concepts_by_id = _concepts_by_id(subject_merge)
    lessons_by_id = _lessons_by_id(source_ledger)
    tasks: list[_SegmentClassificationTask] = []
    order = 0
    for lesson_id in sorted(lesson_segment_artifacts):
        lesson_segments = lesson_segment_artifacts[lesson_id]
        lesson = lessons_by_id.get(lesson_id) or {"lesson_id": lesson_id, "title": ""}
        for segment in lesson_segments.get("segments") or []:
            if not isinstance(segment, dict):
                continue
            segment_id = str(segment.get("segment_id") or "")
            if not segment_id:
                raise StageBlockedError(f"Knowledge Type Classification found a Segment without segment_id")
            concept_ids = [str(concept_id) for concept_id in segment.get("concept_ids") or [] if str(concept_id)]
            if not concept_ids:
                continue
            unknown = [concept_id for concept_id in concept_ids if concept_id not in concepts_by_id]
            if unknown:
                raise StageBlockedError(
                    "Knowledge Type Classification Segment references unknown Concept IDs: " + ", ".join(unknown)
                )
            order += 1
            segment_dir = run_dir / "lessons" / lesson_id / "knowledge_type_segments" / segment_id
            segment_dir.mkdir(parents=True, exist_ok=True)
            tasks.append(
                _SegmentClassificationTask(
                    order=order,
                    lesson_id=lesson_id,
                    segment_id=segment_id,
                    segment_label=str(segment.get("label") or ""),
                    run_dir=run_dir,
                    segment_dir=segment_dir,
                    artifact_path=str(
                        (run_dir / "lessons" / lesson_id / "lesson_segments.json").relative_to(run_dir)
                    ),
                    lesson=_compact_lesson(lesson),
                    concept_ids=concept_ids,
                    concepts=[
                        _compact_concept_for_classification(concepts_by_id[concept_id]) for concept_id in concept_ids
                    ],
                )
            )
    return tasks


def _run_segment_classification_tasks(
    *,
    tasks: list[_SegmentClassificationTask],
    runner: StageRunner,
    prompt: _KnowledgeTypePrompt,
    taxonomy: dict[str, Any],
    model_route: str,
    format_repair_model_route: str,
    concurrency: int,
) -> list[_SegmentClassificationResult]:
    if concurrency <= 1 or len(tasks) <= 1:
        return [
            _run_segment_classification_task(
                task=task,
                runner=runner,
                prompt=prompt,
                taxonomy=taxonomy,
                model_route=model_route,
                format_repair_model_route=format_repair_model_route,
            )
            for task in tasks
        ]

    results_by_order: dict[int, _SegmentClassificationResult] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {
            executor.submit(
                _run_segment_classification_task,
                task=task,
                runner=runner,
                prompt=prompt,
                taxonomy=taxonomy,
                model_route=model_route,
                format_repair_model_route=format_repair_model_route,
            ): task.order
            for task in tasks
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results_by_order[result.order] = result
    return [results_by_order[task.order] for task in tasks]


def _run_segment_classification_task(
    *,
    task: _SegmentClassificationTask,
    runner: StageRunner,
    prompt: _KnowledgeTypePrompt,
    taxonomy: dict[str, Any],
    model_route: str,
    format_repair_model_route: str,
) -> _SegmentClassificationResult:
    model_input = {
        "artifact_type": "knowledge_type_classification_input",
        "schema_version": "knowledge_type_classification_input.v0",
        "source_artifacts": {
            "source_ledger": "source_ledger.json",
            "subject_merge": "subject_merge.json",
            "lesson_segments": task.artifact_path,
        },
        "taxonomy": taxonomy,
        "prompt_path": prompt.path_ref,
        "prompt": prompt.text,
        "task": "knowledge_type_classification",
        "model_route": model_route,
        "lesson": task.lesson,
        "segment": {
            "segment_id": task.segment_id,
            "label": task.segment_label,
            "concept_ids": task.concept_ids,
        },
        "concepts": task.concepts,
        "output_contract": _classification_output_contract(),
        "web_access_policy": _no_web_policy(),
    }
    (task.segment_dir / "knowledge_type_classification_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = runner.run(
        StageContract(
            name="knowledge_type_classification",
            required_inputs=["knowledge_type_classification_input.json"],
            output_artifact="knowledge_type_classification.json",
            model_route=model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=lambda artifact: _validate_classification_artifact(
                artifact=artifact,
                expected_concept_ids=task.concept_ids,
                artifact_type="knowledge_type_segment_classification",
                schema_version="knowledge_type_segment_classification.v0",
            ),
            normalizer=lambda raw, inputs: _normalize_classification_output(
                raw,
                inputs,
                input_key="knowledge_type_classification_input.json",
                artifact_type="knowledge_type_segment_classification",
                schema_version="knowledge_type_segment_classification.v0",
            ),
        ),
        run_dir=task.segment_dir,
    )
    artifact = _read_json(result.artifact_path)
    return _SegmentClassificationResult(
        order=task.order,
        lesson_id=task.lesson_id,
        segment_id=task.segment_id,
        segment_label=task.segment_label,
        artifact_path=result.artifact_path,
        artifact_path_ref=str(result.artifact_path.relative_to(task.run_dir)),
        artifact=artifact,
        repaired=result.repaired,
    )


def _aggregate_segment_classifications(
    *,
    subject_merge: dict[str, Any],
    segment_results: list[_SegmentClassificationResult],
) -> dict[str, Any]:
    subject_concepts = _subject_concepts(subject_merge)
    concept_ids = [str(concept.get("concept_id") or "") for concept in subject_concepts]
    evidence_by_concept_id: dict[str, list[dict[str, Any]]] = {concept_id: [] for concept_id in concept_ids}

    for result in segment_results:
        for classification in result.artifact.get("classifications") or []:
            concept_id = str(classification.get("concept_id") or "")
            if concept_id not in evidence_by_concept_id:
                continue
            evidence_by_concept_id[concept_id].append(
                {
                    "knowledge_type": classification.get("knowledge_type"),
                    "rationale": classification.get("rationale"),
                    "confidence": classification.get("confidence"),
                    "lesson_id": result.lesson_id,
                    "segment_id": result.segment_id,
                    "segment_label": result.segment_label,
                    "classification_artifact": result.artifact_path_ref,
                }
            )

    missing = [concept_id for concept_id in concept_ids if not evidence_by_concept_id.get(concept_id)]
    if missing:
        raise StageBlockedError(
            "Knowledge Type Classification requires Segment evidence for every Concept: " + ", ".join(missing)
        )

    classifications = []
    conflicts = []
    for concept in subject_concepts:
        concept_id = str(concept.get("concept_id") or "")
        evidence = evidence_by_concept_id.get(concept_id) or []
        type_order = _stable_unique([str(item.get("knowledge_type") or "") for item in evidence])
        first = evidence[0]
        source = "segment_consensus"
        rationale = str(first.get("rationale") or "")
        if len(type_order) > 1:
            source = "segment_conflict_unresolved"
            rationale = "Segment-level classifications disagree and require quality repair."
            conflicts.append(
                {
                    "concept_id": concept_id,
                    "knowledge_types": type_order,
                    "segment_evidence": evidence,
                }
            )
        classification = {
            "concept_id": concept_id,
            "knowledge_type": type_order[0],
            "rationale": rationale,
            "source": source,
            "segment_refs": [
                {
                    "lesson_id": item["lesson_id"],
                    "segment_id": item["segment_id"],
                    "segment_label": item["segment_label"],
                    "classification_artifact": item["classification_artifact"],
                    "knowledge_type": item["knowledge_type"],
                    "rationale": item["rationale"],
                    "confidence": item.get("confidence"),
                }
                for item in evidence
            ],
        }
        if first.get("confidence") is not None:
            classification["confidence"] = first.get("confidence")
        classifications.append(classification)

    return {
        "artifact_type": "knowledge_type_classification_aggregate",
        "schema_version": "knowledge_type_classification_aggregate.v0",
        "generated_at": _now(),
        "classifications": classifications,
        "conflicts": conflicts,
        "segment_classification_artifacts": [result.artifact_path_ref for result in segment_results],
    }


def _run_quality_audit(
    *,
    run_dir: Path,
    aggregate: dict[str, Any],
    taxonomy: dict[str, Any],
    prompt: _KnowledgeTypePrompt,
    runner: StageRunner,
    model_route: str,
    format_repair_model_route: str,
) -> dict[str, Any]:
    model_input = {
        "artifact_type": "knowledge_type_quality_audit_input",
        "schema_version": "knowledge_type_quality_audit_input.v0",
        "source_artifact": "knowledge_type_classification_summary.json",
        "taxonomy": taxonomy,
        "prompt_path": prompt.path_ref,
        "prompt": prompt.text,
        "task": "knowledge_type_quality_audit",
        "model_route": model_route,
        "current_classifications": aggregate.get("classifications") or [],
        "conflicts": aggregate.get("conflicts") or [],
        "distribution": _knowledge_type_distribution(aggregate.get("classifications") or []),
        "output_contract": _quality_audit_output_contract(),
        "web_access_policy": _no_web_policy(),
    }
    (run_dir / "knowledge_type_quality_audit_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = runner.run(
        StageContract(
            name="knowledge_type_quality_audit",
            required_inputs=["knowledge_type_quality_audit_input.json"],
            output_artifact="knowledge_type_quality_audit.json",
            model_route=model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=_validate_quality_audit,
            normalizer=_normalize_quality_audit_output,
        ),
        run_dir=run_dir,
    )
    audit = _apply_quality_guardrails(_read_json(result.artifact_path), aggregate=aggregate)
    result.artifact_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit


def _run_quality_repair(
    *,
    run_dir: Path,
    aggregate: dict[str, Any],
    target_concept_ids: list[str],
    quality_audit: dict[str, Any],
    taxonomy: dict[str, Any],
    prompt: _KnowledgeTypePrompt,
    runner: StageRunner,
    model_route: str,
    format_repair_model_route: str,
) -> Path:
    model_input = {
        "artifact_type": "knowledge_type_quality_repair_input",
        "schema_version": "knowledge_type_quality_repair_input.v0",
        "source_artifact": "knowledge_type_classification_summary.json",
        "quality_audit_artifact": "knowledge_type_quality_audit.json",
        "taxonomy": taxonomy,
        "prompt_path": prompt.path_ref,
        "prompt": prompt.text,
        "task": "knowledge_type_quality_repair",
        "model_route": model_route,
        "target_concept_ids": target_concept_ids,
        "current_classifications": [
            classification
            for classification in aggregate.get("classifications") or []
            if classification.get("concept_id") in set(target_concept_ids)
        ],
        "quality_audit": quality_audit,
        "output_contract": _classification_output_contract(),
        "web_access_policy": _no_web_policy(),
    }
    (run_dir / "knowledge_type_quality_repair_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = runner.run(
        StageContract(
            name="knowledge_type_quality_repair",
            required_inputs=["knowledge_type_quality_repair_input.json"],
            output_artifact="knowledge_type_quality_repair_decision.json",
            model_route=model_route,
            repair_model_route=format_repair_model_route,
            contextual_repair_model_route=format_repair_model_route,
            validator=lambda artifact: _validate_classification_artifact(
                artifact=artifact,
                expected_concept_ids=target_concept_ids,
                artifact_type="knowledge_type_quality_repair_decision",
                schema_version="knowledge_type_quality_repair_decision.v0",
            ),
            normalizer=lambda raw, inputs: _normalize_classification_output(
                raw,
                inputs,
                input_key="knowledge_type_quality_repair_input.json",
                artifact_type="knowledge_type_quality_repair_decision",
                schema_version="knowledge_type_quality_repair_decision.v0",
            ),
        ),
        run_dir=run_dir,
    )
    return result.artifact_path


def _apply_quality_repair(
    *,
    aggregate: dict[str, Any],
    repair_decision: dict[str, Any],
    repair_artifact_path: str,
) -> dict[str, Any]:
    repaired_by_id = {
        str(item.get("concept_id") or ""): item
        for item in repair_decision.get("classifications") or []
        if isinstance(item, dict)
    }
    repaired = json.loads(json.dumps(aggregate, ensure_ascii=False))
    for classification in repaired.get("classifications") or []:
        concept_id = str(classification.get("concept_id") or "")
        repair = repaired_by_id.get(concept_id)
        if not repair:
            continue
        classification["knowledge_type"] = repair["knowledge_type"]
        classification["rationale"] = repair["rationale"]
        classification["source"] = "quality_repair"
        classification["repair_decision_artifact"] = repair_artifact_path
        if repair.get("confidence") is not None:
            classification["confidence"] = repair.get("confidence")
    repaired["conflicts"] = [
        conflict
        for conflict in repaired.get("conflicts") or []
        if str(conflict.get("concept_id") or "") not in repaired_by_id
    ]
    return repaired


def _build_summary_artifact(
    *,
    aggregate: dict[str, Any],
    taxonomy: dict[str, Any],
    prompts: dict[str, _KnowledgeTypePrompt],
    segment_results: list[_SegmentClassificationResult],
    status: str,
    audit: dict[str, Any],
    audit_count: int,
    repair_count: int,
    repair_artifact_path: str | None,
    classification_model_route: str,
    audit_model_route: str,
    quality_repair_model_route: str,
    concurrency: int,
) -> dict[str, Any]:
    classifications = aggregate.get("classifications") or []
    conflicts = aggregate.get("conflicts") or []
    summary = {
        "concept_count": len(classifications),
        "classified_concept_count": len(classifications),
        "segment_classification_count": len(segment_results),
        "conflict_count": len(conflicts),
        "audit_count": audit_count,
        "repair_count": repair_count,
        "unrepaired_count": 0 if status in {"reliable", "repaired"} else 1,
        "distribution": _knowledge_type_distribution(classifications),
    }
    artifact = {
        "artifact_type": "knowledge_type_classification_summary",
        "schema_version": "knowledge_type_classification_summary.v0",
        "generated_at": _now(),
        "status": status,
        "source_artifacts": {
            "source_ledger": "source_ledger.json",
            "subject_merge": "subject_merge.json",
            "lesson_segmentation_summary": "lesson_segmentation_summary.json",
        },
        "taxonomy": taxonomy,
        "prompts": {key: prompt.path_ref for key, prompt in prompts.items()},
        "model_routes": {
            "classification": classification_model_route,
            "audit": audit_model_route,
            "quality_repair": quality_repair_model_route,
        },
        "concurrency": concurrency,
        "summary": summary,
        "artifacts": [result.artifact_path_ref for result in segment_results],
        "quality_audit_artifact": "knowledge_type_quality_audit.json",
        "repair_decision_artifact": repair_artifact_path,
        "classifications": classifications,
        "conflicts": conflicts,
        "quality_audit": audit,
    }
    return artifact


def _normalize_classification_output(
    raw: str,
    inputs: dict[str, Any],
    *,
    input_key: str,
    artifact_type: str,
    schema_version: str,
) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("knowledge type classification output must be a JSON object")
    model_input = inputs[input_key]
    classifications = []
    for item in payload.get("classifications") or []:
        if not isinstance(item, dict):
            continue
        normalized = {
            "concept_id": str(item.get("concept_id") or "").strip(),
            "knowledge_type": str(item.get("knowledge_type") or "").strip().lower(),
            "rationale": str(item.get("rationale") or "").strip(),
        }
        if item.get("confidence") is not None:
            normalized["confidence"] = item.get("confidence")
        classifications.append(normalized)
    return {
        "artifact_type": artifact_type,
        "schema_version": schema_version,
        "generated_at": _now(),
        "model_route": model_input.get("model_route"),
        "lesson_id": (model_input.get("lesson") or {}).get("lesson_id"),
        "segment_id": (model_input.get("segment") or {}).get("segment_id"),
        "classifications": classifications,
    }


def _validate_classification_artifact(
    *,
    artifact: dict[str, Any],
    expected_concept_ids: list[str],
    artifact_type: str,
    schema_version: str,
) -> list[str]:
    errors = []
    if artifact.get("artifact_type") != artifact_type:
        errors.append(f"{artifact_type}.artifact_type must be '{artifact_type}'")
    if artifact.get("schema_version") != schema_version:
        errors.append(f"{artifact_type}.schema_version must be '{schema_version}'")
    classifications = artifact.get("classifications")
    if not isinstance(classifications, list) or not classifications:
        errors.append(f"{artifact_type}.classifications must not be empty")
        return errors
    seen: list[str] = []
    expected_set = set(expected_concept_ids)
    for index, classification in enumerate(classifications):
        location = f"{artifact_type}.classifications[{index}]"
        if not isinstance(classification, dict):
            errors.append(f"{location} must be an object")
            continue
        concept_id = str(classification.get("concept_id") or "")
        if not concept_id:
            errors.append(f"{location}.concept_id is required")
        elif concept_id not in expected_set:
            errors.append(f"{location}.concept_id references unknown Concept ID: {concept_id}")
        seen.append(concept_id)
        if classification.get("knowledge_type") not in ALLOWED_KNOWLEDGE_TYPES:
            errors.append(f"{location}.knowledge_type must be one of: {_allowed_knowledge_types_text()}")
        if not str(classification.get("rationale") or "").strip():
            errors.append(f"{location}.rationale is required")
        confidence = classification.get("confidence")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                errors.append(f"{location}.confidence must be a number from 0.0 to 1.0")
    duplicates = sorted({concept_id for concept_id in seen if seen.count(concept_id) > 1})
    if duplicates:
        errors.append(f"{artifact_type}.classifications repeat Concept IDs: " + ", ".join(duplicates))
    missing = [concept_id for concept_id in expected_concept_ids if concept_id not in seen]
    if missing:
        errors.append(f"{artifact_type}.classifications are missing Concept IDs: " + ", ".join(missing))
    return errors


def _normalize_quality_audit_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("knowledge type quality audit output must be a JSON object")
    model_input = inputs["knowledge_type_quality_audit_input.json"]
    return {
        "artifact_type": "knowledge_type_quality_audit",
        "schema_version": "knowledge_type_quality_audit.v0",
        "generated_at": _now(),
        "model_route": model_input.get("model_route"),
        "scores": payload.get("scores") or {},
        "reliability": payload.get("reliability"),
        "flags": payload.get("flags") or [],
        "findings": payload.get("findings") or [],
        "repair_plan": payload.get("repair_plan") or [],
    }


def _validate_quality_audit(artifact: dict[str, Any]) -> list[str]:
    errors = []
    if artifact.get("artifact_type") != "knowledge_type_quality_audit":
        errors.append("knowledge_type_quality_audit.artifact_type must be 'knowledge_type_quality_audit'")
    if artifact.get("schema_version") != "knowledge_type_quality_audit.v0":
        errors.append("knowledge_type_quality_audit.schema_version must be 'knowledge_type_quality_audit.v0'")
    scores = artifact.get("scores")
    if not isinstance(scores, dict):
        errors.append("knowledge_type_quality_audit.scores must be an object")
        scores = {}
    for field in _AUDIT_SCORE_FIELDS:
        value = scores.get(field)
        if not isinstance(value, int) or value < 0 or value > 3:
            errors.append(f"knowledge_type_quality_audit.scores.{field} must be an integer from 0 to 3")
    reliability = artifact.get("reliability")
    if reliability not in {"reliable", "repair_required"}:
        errors.append("knowledge_type_quality_audit.reliability must be reliable or repair_required")
    flags = artifact.get("flags")
    if not isinstance(flags, list):
        errors.append("knowledge_type_quality_audit.flags must be a list")
        flags = []
    for flag in flags:
        if flag not in _AUDIT_FLAGS:
            errors.append(f"knowledge_type_quality_audit.flags contains unknown flag: {flag}")
    findings = artifact.get("findings")
    if not isinstance(findings, list):
        errors.append("knowledge_type_quality_audit.findings must be a list")
    repair_plan = artifact.get("repair_plan")
    if not isinstance(repair_plan, list):
        errors.append("knowledge_type_quality_audit.repair_plan must be a list")
        repair_plan = []
    if reliability == "repair_required" and not repair_plan:
        errors.append("knowledge_type_quality_audit.repair_required requires repair_plan")
    for index, item in enumerate(repair_plan):
        location = f"knowledge_type_quality_audit.repair_plan[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{location} must be an object")
            continue
        concept_ids = item.get("concept_ids")
        if not isinstance(concept_ids, list) or not concept_ids:
            errors.append(f"{location}.concept_ids must not be empty")
        repair_reason = item.get("repair_reason")
        if not isinstance(repair_reason, str) or repair_reason not in _REPAIR_REASONS:
            errors.append(f"{location}.repair_reason must be one of: {', '.join(sorted(_REPAIR_REASONS))}")
        if not str(item.get("explanation") or "").strip():
            errors.append(f"{location}.explanation is required")
    return errors


def _apply_quality_guardrails(audit: dict[str, Any], *, aggregate: dict[str, Any]) -> dict[str, Any]:
    conflicts = aggregate.get("conflicts") or []
    if not conflicts:
        return audit
    guarded = json.loads(json.dumps(audit, ensure_ascii=False))
    guarded["reliability"] = "repair_required"
    flags = guarded.setdefault("flags", [])
    if "cross_segment_conflict" not in flags:
        flags.append("cross_segment_conflict")
    findings = guarded.setdefault("findings", [])
    repair_plan = guarded.setdefault("repair_plan", [])
    planned = {
        concept_id
        for plan in repair_plan
        if isinstance(plan, dict)
        for concept_id in plan.get("concept_ids") or []
    }
    for conflict in conflicts:
        concept_id = str(conflict.get("concept_id") or "")
        if not concept_id:
            continue
        findings.append(
            {
                "issue": "cross_segment_conflict",
                "concept_ids": [concept_id],
                "explanation": "Segment-level classifications disagree for this Concept.",
            }
        )
        if concept_id not in planned:
            repair_plan.append(
                {
                    "concept_ids": [concept_id],
                    "repair_reason": "cross_segment_conflict",
                    "explanation": "Choose one primary teaching mode from the conflicting Segment evidence.",
                }
            )
    return guarded


def _target_concept_ids_from_audit(*, audit: dict[str, Any], aggregate: dict[str, Any]) -> list[str]:
    known_ids = {str(item.get("concept_id") or "") for item in aggregate.get("classifications") or []}
    target_ids = []
    for plan in audit.get("repair_plan") or []:
        if not isinstance(plan, dict):
            continue
        for concept_id in plan.get("concept_ids") or []:
            concept_id = str(concept_id or "")
            if concept_id and concept_id in known_ids and concept_id not in target_ids:
                target_ids.append(concept_id)
    return target_ids


def _classification_output_contract() -> dict[str, Any]:
    return {
        "classifications": [
            {
                "concept_id": "Every input Concept ID exactly once.",
                "knowledge_type": _allowed_knowledge_types_text(),
                "rationale": "Short explanation citing the deciding clue.",
                "confidence": "Optional number from 0.0 to 1.0.",
            }
        ]
    }


def _quality_audit_output_contract() -> dict[str, Any]:
    return {
        "scores": {field: "integer 0-3" for field in _AUDIT_SCORE_FIELDS},
        "reliability": "reliable or repair_required",
        "flags": sorted(_AUDIT_FLAGS),
        "findings": [
            {
                "issue": "Short issue name.",
                "concept_ids": ["Relevant Concept IDs."],
                "explanation": "Concrete classification problem.",
            }
        ],
        "repair_plan": [
            {
                "concept_ids": ["Target Concept IDs."],
                "repair_reason": sorted(_REPAIR_REASONS),
                "explanation": "Why these Concepts need relabeling.",
            }
        ],
    }


def _compact_concept_for_classification(concept: dict[str, Any]) -> dict[str, Any]:
    concept_id = str(concept.get("concept_id") or "")
    if not concept_id:
        raise StageBlockedError("Knowledge Type Classification found a Concept without concept_id")
    label = str(concept.get("label") or "").strip()
    description = str(concept.get("teaching_description") or concept.get("description") or "").strip()
    coverage_criteria = [str(item).strip() for item in concept.get("coverage_criteria") or [] if str(item).strip()]
    if not label:
        raise StageBlockedError(f"Knowledge Type Classification requires label for Concept {concept_id}")
    if not description:
        raise StageBlockedError(f"Knowledge Type Classification requires teaching description for Concept {concept_id}")
    if not coverage_criteria:
        raise StageBlockedError(f"Knowledge Type Classification requires Coverage Criteria for Concept {concept_id}")
    return {
        "concept_id": concept_id,
        "label": label,
        "teaching_description": description,
        "coverage_criteria": coverage_criteria,
        "source_candidate_ids": [str(item) for item in concept.get("source_candidate_ids") or [] if str(item)],
    }


def _compact_lesson(lesson: dict[str, Any]) -> dict[str, Any]:
    return {
        "lesson_id": lesson.get("lesson_id"),
        "title": lesson.get("title"),
    }


def _knowledge_type_distribution(classifications: list[dict[str, Any]]) -> dict[str, int]:
    return {
        knowledge_type: sum(1 for item in classifications if item.get("knowledge_type") == knowledge_type)
        for knowledge_type in sorted(ALLOWED_KNOWLEDGE_TYPES)
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


def _load_prompts(prompt_path: Path | None) -> dict[str, _KnowledgeTypePrompt]:
    prompts_root = Path(__file__).resolve().parents[3] / "prompts"
    selected = prompt_path or prompts_root / "knowledge_type_classification"
    if selected.is_file():
        text = selected.read_text(encoding="utf-8")
        path_ref = _prompt_path_ref(selected, prompts_root)
        return {task: _KnowledgeTypePrompt(text=text, path_ref=path_ref) for task in _PROMPT_FILES}
    if not selected.is_dir():
        raise StageBlockedError(f"Knowledge Type Classification prompt path does not exist: {selected}")
    prompts: dict[str, _KnowledgeTypePrompt] = {}
    for task, filename in _PROMPT_FILES.items():
        path = selected / filename
        if not path.is_file():
            raise StageBlockedError(f"Knowledge Type Classification missing task prompt: {path}")
        prompts[task] = _KnowledgeTypePrompt(
            text=path.read_text(encoding="utf-8"),
            path_ref=_prompt_path_ref(path, prompts_root),
        )
    return prompts


def _load_knowledge_type_taxonomy() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[4]
    system_prompt_path = repo_root / "prompts" / "system_prompt.txt"
    if not system_prompt_path.is_file():
        raise StageBlockedError(f"Knowledge Type Classification requires taxonomy source: {system_prompt_path}")
    text = system_prompt_path.read_text(encoding="utf-8")
    definitions = {}
    for knowledge_type, heading in {
        "conceptual": "CONCEPTUAL",
        "procedural": "PROCEDURAL",
        "factual": "FACTUAL",
        "applied": "APPLIED",
    }.items():
        match = re.search(rf"^{heading} \(([^)]*)\):", text, flags=re.MULTILINE)
        if not match:
            raise StageBlockedError(f"Knowledge Type Classification could not read {heading} taxonomy definition")
        definitions[knowledge_type] = match.group(1)
    return {
        "source_artifact": _path_ref(system_prompt_path, repo_root),
        "definitions": definitions,
    }


def _concepts_by_id(subject_merge: dict[str, Any]) -> dict[str, dict[str, Any]]:
    concepts = {}
    for concept in _subject_concepts(subject_merge):
        concept_id = str(concept.get("concept_id") or "")
        if concept_id in concepts:
            raise StageBlockedError(f"Knowledge Type Classification found duplicate Concept ID: {concept_id}")
        concepts[concept_id] = concept
    return concepts


def _subject_concepts(subject_merge: dict[str, Any]) -> list[dict[str, Any]]:
    return [concept for concept in subject_merge.get("concepts") or [] if isinstance(concept, dict)]


def _lessons_by_id(source_ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(lesson.get("lesson_id") or ""): lesson
        for lesson in source_ledger.get("lessons") or []
        if isinstance(lesson, dict) and str(lesson.get("lesson_id") or "")
    }


def _stable_unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _prompt_path_ref(path: Path, prompts_root: Path) -> str:
    return _path_ref(path, prompts_root)


def _path_ref(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _allowed_knowledge_types_text() -> str:
    return ", ".join(sorted(ALLOWED_KNOWLEDGE_TYPES))


def _no_web_policy() -> dict[str, Any]:
    return {
        "web_access": "disabled",
        "reason": "Knowledge Type Classification must use only provided Concept and Segment context.",
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
