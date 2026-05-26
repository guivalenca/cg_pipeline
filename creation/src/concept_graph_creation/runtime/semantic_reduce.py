from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


CONTROLLED_PRUNING_REASONS = {
    "duplicate",
    "near_duplicate",
    "low_teaching_value",
    "incidental",
    "too_narrow",
    "too_broad",
    "unrelated",
    "unsupported_metadata_only",
    "unsupported_lesson_intent",
}
ASSIGNMENT_STATUSES = {"used_in", "merged_into", "pruned", "review"}


def build_candidate_registry(
    *,
    scope_id: str,
    source_artifact: str,
    candidate_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates: dict[str, dict[str, Any]] = {}
    order = 0

    for source in candidate_sources:
        namespace = str(source.get("namespace") or "").strip()
        if not namespace:
            raise ValueError("candidate source namespace is required")
        for index, candidate in enumerate(source.get("candidates") or [], start=1):
            order += 1
            compact_id = f"{namespace}_{index:03d}"
            if compact_id in candidates:
                raise ValueError(f"duplicate compact candidate id: {compact_id}")
            candidates[compact_id] = _registry_entry(
                source=source,
                candidate=candidate,
                compact_id=compact_id,
                order=order,
                scope_id=scope_id,
            )

    return {
        "artifact_type": "semantic_reduce_candidate_registry",
        "schema_version": "semantic_reduce_candidate_registry.v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_artifact": source_artifact,
        "scope_id": scope_id,
        "candidates": candidates,
        "summary": {"candidate_count": len(candidates)},
    }


def normalize_decision_output(
    *,
    raw: str,
    scope_id: str,
    stage_name: str,
    model_route: str,
    input_candidate_ids: list[str],
) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("semantic reduce model output must be a JSON object")
    accepted = payload.get("accepted_concepts", payload.get("accepted"))
    if not isinstance(accepted, list):
        raise ValueError("semantic reduce model output must include accepted_concepts")
    candidate_assignments = payload.get("candidate_assignments")
    if not isinstance(candidate_assignments, list):
        raise ValueError("semantic reduce model output must include candidate_assignments")

    normalized_assignments = [_normalize_assignment(item) for item in candidate_assignments]
    pruned = _pruned_from_assignments(normalized_assignments)
    return {
        "artifact_type": "semantic_reduce_decision",
        "schema_version": "semantic_reduce_decision.v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope_id": scope_id,
        "stage_name": stage_name,
        "model_route": model_route,
        "input_candidate_ids": input_candidate_ids,
        "accepted": accepted,
        "accepted_concepts": accepted,
        "candidate_assignments": normalized_assignments,
        "pruned": pruned,
        "summary": {
            "input_candidate_count": len(input_candidate_ids),
            "accepted_count": len(accepted),
            "pruned_count": len(pruned),
            "candidate_assignment_count": len(normalized_assignments),
            "review_count": sum(1 for item in normalized_assignments if item.get("status") == "review"),
        },
    }


def build_reduce_input(
    *,
    stage_name: str,
    scope: dict[str, Any],
    registry: dict[str, Any],
    input_candidate_ids: list[str],
    prompt: str,
    prompt_path: str,
    model_route: str,
) -> dict[str, Any]:
    registry_candidates = registry.get("candidates") or {}
    unknown_candidate_ids = [
        candidate_id
        for candidate_id in input_candidate_ids
        if candidate_id not in registry_candidates
    ]
    if unknown_candidate_ids:
        raise ValueError("unknown semantic reduce candidate IDs: " + ", ".join(unknown_candidate_ids))
    return {
        "artifact_type": "semantic_reduce_input",
        "schema_version": "semantic_reduce_input.v0",
        "source_artifact": registry.get("source_artifact"),
        "candidate_registry_artifact": "candidate_registry.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": stage_name,
        "model_route": model_route,
        "scope": scope,
        "input_candidate_ids": input_candidate_ids,
        "candidates": [
            _compact_candidate_view(registry_candidates[candidate_id])
            for candidate_id in input_candidate_ids
        ],
        "controlled_pruning_reasons": sorted(CONTROLLED_PRUNING_REASONS),
        "output_contract": _decision_output_contract(),
        "web_access_policy": {
            "web_search_allowed": False,
            "instruction": "Do not use web search or open URLs. Use only the provided candidate cards.",
        },
    }


def validate_reduce_decision(decision: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if decision.get("artifact_type") != "semantic_reduce_decision":
        errors.append("semantic_reduce_decision.artifact_type must be 'semantic_reduce_decision'")
    if decision.get("schema_version") != "semantic_reduce_decision.v0":
        errors.append("semantic_reduce_decision.schema_version must be 'semantic_reduce_decision.v0'")
    if decision.get("scope_id") != registry.get("scope_id"):
        errors.append("semantic_reduce_decision.scope_id must match registry.scope_id")

    registry_ids = set((registry.get("candidates") or {}).keys())
    input_ids = decision.get("input_candidate_ids")
    if not isinstance(input_ids, list) or not all(isinstance(item, str) and item for item in input_ids):
        errors.append("semantic_reduce_decision.input_candidate_ids must contain candidate IDs")
        input_ids = []
    input_id_set = set(input_ids)
    unknown_input_ids = sorted(input_id_set - registry_ids)
    if unknown_input_ids:
        errors.append(
            "semantic_reduce_decision.input_candidate_ids references unknown candidates: "
            + ", ".join(unknown_input_ids)
        )

    accepted = decision.get("accepted_concepts")
    if not isinstance(accepted, list):
        errors.append("semantic_reduce_decision.accepted_concepts must be a list")
        accepted = []
    if decision.get("accepted") != accepted:
        errors.append("semantic_reduce_decision.accepted must match accepted_concepts")

    accepted_ids: set[str] = set()
    accepted_source_ids_by_accepted_id: dict[str, list[str]] = {}
    accepted_ids_by_source: dict[str, list[str]] = {}
    for index, item in enumerate(accepted):
        location = f"accepted_concepts[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{location} must be an object")
            continue
        accepted_id = str(item.get("id") or "")
        if not accepted_id:
            errors.append(f"{location}.id is required")
        elif accepted_id in accepted_ids:
            errors.append(f"{location}.id is duplicated")
        if accepted_id:
            accepted_ids.add(accepted_id)
        for field in ("label", "description", "merge_rationale"):
            if not str(item.get(field) or "").strip():
                errors.append(f"{location}.{field} is required")
        if not _non_empty_string_list(item.get("coverage_criteria")):
            errors.append(f"{location}.coverage_criteria must contain at least one string")
        source_candidate_ids = item.get("source_candidate_ids")
        if not isinstance(source_candidate_ids, list) or not source_candidate_ids:
            errors.append(f"{location}.source_candidate_ids must contain candidate IDs")
            continue
        valid_source_ids: list[str] = []
        for candidate_id in source_candidate_ids:
            if not isinstance(candidate_id, str) or not candidate_id:
                errors.append(f"{location}.source_candidate_ids must contain candidate IDs")
            elif candidate_id not in input_id_set:
                errors.append(f"{location}.source_candidate_ids references unknown candidate {candidate_id}")
            else:
                valid_source_ids.append(candidate_id)
                accepted_ids_by_source.setdefault(candidate_id, []).append(accepted_id)
        duplicated_source_ids = _duplicates(valid_source_ids)
        if duplicated_source_ids:
            errors.append(
                f"{location}.source_candidate_ids contains duplicates: "
                + ", ".join(duplicated_source_ids)
            )
        if accepted_id:
            accepted_source_ids_by_accepted_id[accepted_id] = valid_source_ids

    assignments = decision.get("candidate_assignments")
    if not isinstance(assignments, list):
        errors.append("semantic_reduce_decision.candidate_assignments must be a list")
        assignments = []
    assignment_ids: list[str] = []
    assignment_pruned_ids: list[str] = []
    assignment_review_ids: list[str] = []
    accepted_source_ids = set(accepted_ids_by_source)
    for index, item in enumerate(assignments):
        location = f"candidate_assignments[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{location} must be an object")
            continue
        candidate_id = str(item.get("candidate_id") or "")
        if not candidate_id:
            errors.append(f"{location}.candidate_id is required")
        elif candidate_id not in input_id_set:
            errors.append(f"{location}.candidate_id references unknown candidate {candidate_id}")
        else:
            assignment_ids.append(candidate_id)
        status = str(item.get("status") or "")
        if status not in ASSIGNMENT_STATUSES:
            errors.append(f"{location}.status must be one of " + ", ".join(sorted(ASSIGNMENT_STATUSES)))
            continue

        accepted_refs = _assignment_accepted_ids(item)
        if status == "used_in":
            if not accepted_refs:
                errors.append(f"{location}.accepted_ids must reference at least one accepted concept")
        elif status == "merged_into":
            merged_into = str(item.get("merged_into") or "")
            if not merged_into:
                errors.append(f"{location}.merged_into is required")
            accepted_refs = [merged_into] if merged_into else []
        elif status == "pruned":
            assignment_pruned_ids.append(candidate_id)
            if str(item.get("reason") or "") not in CONTROLLED_PRUNING_REASONS:
                errors.append(f"{location}.reason must be a controlled Candidate Pruning Reason")
            if not str(item.get("explanation") or "").strip():
                errors.append(f"{location}.explanation is required")
            if candidate_id in accepted_source_ids:
                errors.append(f"{location}.candidate_id cannot be pruned because it is used as accepted evidence")
        elif status == "review":
            assignment_review_ids.append(candidate_id)
            if not str(item.get("explanation") or "").strip():
                errors.append(f"{location}.explanation is required")
            if candidate_id in accepted_source_ids:
                errors.append(f"{location}.candidate_id cannot require review because it is used as accepted evidence")

        for accepted_ref in accepted_refs:
            if accepted_ref not in accepted_ids:
                errors.append(f"{location} references unknown accepted concept {accepted_ref}")
                continue
            if candidate_id and candidate_id not in accepted_source_ids_by_accepted_id.get(accepted_ref, []):
                errors.append(
                    f"{location}.candidate_id must appear in accepted_concepts source_candidate_ids for {accepted_ref}"
                )

    duplicated_assignment_ids = _duplicates(assignment_ids)
    if duplicated_assignment_ids:
        errors.append(
            "semantic_reduce_decision.candidate_assignments candidate_id values are duplicated: "
            + ", ".join(duplicated_assignment_ids)
        )
    missing = sorted(input_id_set - set(assignment_ids))
    if missing:
        errors.append("semantic_reduce_decision every input candidate must have one assignment: " + ", ".join(missing))

    pruned = decision.get("pruned")
    if not isinstance(pruned, list):
        errors.append("semantic_reduce_decision.pruned must be a list")
        pruned = []
    pruned_ids = [str(item.get("candidate_id") or "") for item in pruned if isinstance(item, dict)]
    if set(pruned_ids) != set(assignment_pruned_ids):
        errors.append("semantic_reduce_decision.pruned must match candidate_assignments with status pruned")

    summary = decision.get("summary") or {}
    if summary.get("input_candidate_count") != len(input_ids):
        errors.append("semantic_reduce_decision.summary.input_candidate_count does not match input_candidate_ids length")
    if summary.get("accepted_count") != len(accepted):
        errors.append("semantic_reduce_decision.summary.accepted_count does not match accepted_concepts length")
    if summary.get("pruned_count") != len(pruned):
        errors.append("semantic_reduce_decision.summary.pruned_count does not match pruned length")
    if summary.get("candidate_assignment_count") != len(assignments):
        errors.append(
            "semantic_reduce_decision.summary.candidate_assignment_count does not match candidate_assignments length"
        )
    if summary.get("review_count") != len(assignment_review_ids):
        errors.append("semantic_reduce_decision.summary.review_count does not match review assignment length")
    return errors


def _registry_entry(
    *,
    source: dict[str, Any],
    candidate: dict[str, Any],
    compact_id: str,
    order: int,
    scope_id: str,
) -> dict[str, Any]:
    evidence_type = str(candidate.get("evidence_type") or source.get("evidence_type") or "")
    return {
        "compact_id": compact_id,
        "order": order,
        "artifact_type": source.get("artifact_type"),
        "artifact_path": source.get("artifact_path"),
        "original_candidate_id": str(candidate.get("candidate_id") or ""),
        "scope_id": scope_id,
        "lesson_id": source.get("lesson_id"),
        "self_study_id": source.get("self_study_id"),
        "model_route": source.get("model_route"),
        "evidence_type": evidence_type,
        "label": candidate.get("label"),
        "description": candidate.get("description"),
        "coverage_criteria": candidate.get("coverage_criteria") or [],
        "source_roles": candidate.get("source_roles") or [],
        "anchors": _candidate_anchors(candidate),
        "extraction_reason": candidate.get("extraction_reason") or {},
        "source_metadata": source.get("source_metadata") or {},
        "original_candidate": candidate,
        "candidate_ref": _candidate_ref(source=source, candidate=candidate, evidence_type=evidence_type),
    }


def _candidate_ref(
    *,
    source: dict[str, Any],
    candidate: dict[str, Any],
    evidence_type: str,
) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "artifact_path": source.get("artifact_path"),
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "evidence_type": evidence_type,
            "model_route": source.get("model_route"),
            "lesson_id": source.get("lesson_id"),
            "self_study_id": source.get("self_study_id"),
            "pass_id": source.get("pass_id"),
        }.items()
        if value is not None
    }


def _candidate_anchors(candidate: dict[str, Any]) -> list[Any]:
    anchors = candidate.get("source_anchors")
    if anchors is None:
        anchors = candidate.get("metadata_anchors")
    if isinstance(anchors, list):
        return anchors
    return []


def _compact_candidate_view(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry.get("compact_id"),
        "label": entry.get("label"),
        "description": entry.get("description"),
        "coverage_criteria": entry.get("coverage_criteria") or [],
        "source_roles": entry.get("source_roles") or [],
        "evidence_type": entry.get("evidence_type"),
        "rationale": _compact_rationale(entry.get("extraction_reason") or {}),
        "anchors": _compact_anchors(entry.get("anchors") or []),
    }


def _compact_rationale(extraction_reason: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in extraction_reason.items()
        if isinstance(value, (str, int, float)) and str(value).strip()
    }


def _compact_anchors(anchors: list[Any]) -> list[str]:
    compact: list[str] = []
    for anchor in anchors[:5]:
        if isinstance(anchor, dict):
            locator = str(anchor.get("locator") or "").strip()
            if locator:
                compact.append(locator)
        elif isinstance(anchor, str) and anchor.strip():
            compact.append(anchor.strip())
    return compact


def _decision_output_contract() -> dict[str, Any]:
    return {
        "candidate_assignment_rule": (
            "Return clean concepts separately from candidate assignments. Every input candidate ID must appear "
            "exactly once in candidate_assignments. If a candidate is represented by a stronger concept, cite it "
            "in that accepted concept's source_candidate_ids and mark the assignment as merged_into or used_in. "
            "Use status pruned only when the candidate should not influence the graph."
        ),
        "accepted_concepts": [
            {
                "id": "stage-local-id",
                "label": "Specific teachable idea",
                "description": "What the student needs to understand.",
                "coverage_criteria": ["Observable check in one to three focused questions."],
                "source_candidate_ids": ["compact-candidate-id", "represented-compact-candidate-id"],
                "merge_rationale": "Why these candidates belong together.",
            }
        ],
        "candidate_assignments": [
            {
                "candidate_id": "compact-candidate-id",
                "status": "used_in",
                "accepted_ids": ["stage-local-id"],
            },
            {
                "candidate_id": "represented-compact-candidate-id",
                "status": "merged_into",
                "merged_into": "stage-local-id",
                "explanation": "Why it should not stand alone but is represented by the accepted concept.",
            },
            {
                "candidate_id": "discarded-compact-candidate-id",
                "status": "pruned",
                "reason": "low_teaching_value",
                "explanation": "Why this candidate should not influence the graph.",
            },
            {
                "candidate_id": "unclear-compact-candidate-id",
                "status": "review",
                "explanation": "Why compact inputs are insufficient to decide safely.",
            },
        ],
    }


def _normalize_assignment(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    normalized = dict(item)
    if "status" not in normalized and "disposition" in normalized:
        normalized["status"] = normalized["disposition"]
    if "accepted_ids" not in normalized:
        for alias in ("used_in", "accepted_concept_ids", "accepted_concepts"):
            if alias in normalized:
                value = normalized[alias]
                normalized["accepted_ids"] = value if isinstance(value, list) else [value]
                break
    if "merged_into" not in normalized and "accepted_id" in normalized:
        normalized["merged_into"] = normalized["accepted_id"]
    if "reason" not in normalized and "pruning_reason" in normalized:
        normalized["reason"] = normalized["pruning_reason"]
    return normalized


def _pruned_from_assignments(assignments: list[Any]) -> list[dict[str, Any]]:
    pruned: list[dict[str, Any]] = []
    for assignment in assignments:
        if not isinstance(assignment, dict) or assignment.get("status") != "pruned":
            continue
        pruned.append(
            {
                "candidate_id": assignment.get("candidate_id"),
                "reason": assignment.get("reason"),
                "explanation": assignment.get("explanation"),
            }
        )
    return pruned


def _assignment_accepted_ids(item: dict[str, Any]) -> list[str]:
    accepted_ids = item.get("accepted_ids")
    if not isinstance(accepted_ids, list):
        return []
    return [accepted_id for accepted_id in accepted_ids if isinstance(accepted_id, str) and accepted_id]


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value)


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicated: list[str] = []
    for value in values:
        if value in seen and value not in duplicated:
            duplicated.append(value)
        seen.add(value)
    return duplicated
