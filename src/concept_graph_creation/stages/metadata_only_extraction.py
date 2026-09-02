"""Compatibility contract for archived metadata-only extraction artifacts.

The metadata-only creation stage is intentionally not part of the Lesson pilot.
Lesson Reconciliation retains this validator so an archived artifact fails
explicitly instead of being trusted without checking its shape.
"""

from __future__ import annotations

from typing import Any


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


def validate_metadata_only_extraction(artifact: dict[str, Any]) -> list[str]:
    """Validate a legacy artifact without exposing the omitted generation stage."""

    errors: list[str] = []
    if artifact.get("artifact_type") != "metadata_only_extraction":
        errors.append(
            "metadata_only_extraction.artifact_type must be "
            "'metadata_only_extraction'"
        )
    self_study_id = str(artifact.get("self_study_id") or "")
    if not self_study_id:
        errors.append("metadata_only_extraction.self_study_id is required")
    if not artifact.get("lesson_id"):
        errors.append("metadata_only_extraction.lesson_id is required")
    _append_forbidden_key_errors(errors, "metadata_only_extraction", artifact)

    candidates = artifact.get("candidate_concepts")
    if not isinstance(candidates, list):
        errors.append(
            "metadata_only_extraction.candidate_concepts must be a list"
        )
        return errors
    if not candidates and artifact.get("excluded") is not True:
        errors.append(
            "metadata_only_extraction.candidate_concepts must not be empty "
            "unless excluded is true"
        )
    if artifact.get("excluded") is True and not str(
        artifact.get("exclusion_reason") or ""
    ).strip():
        errors.append(
            "metadata_only_extraction.exclusion_reason is required when excluded is true"
        )

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
        elif self_study_id and not candidate_id.startswith(
            f"metadata-candidate-{self_study_id}-"
        ):
            errors.append(
                f"{location}.candidate_id must be scoped to self-study {self_study_id}"
            )
        elif candidate_id in candidate_ids:
            errors.append(f"{location}.candidate_id is duplicated")
        candidate_ids.add(candidate_id)
        for field in ("label", "description"):
            if not str(candidate.get(field) or "").strip():
                errors.append(f"{location}.{field} is required")
        if not _non_empty_string_list(candidate.get("coverage_criteria")):
            errors.append(
                f"{location}.coverage_criteria must contain at least one string"
            )
        if candidate.get("evidence_type") != "workbook_metadata":
            errors.append(
                f"{location}.evidence_type must be 'workbook_metadata'"
            )
        if not _valid_anchors(candidate.get("metadata_anchors")):
            errors.append(
                f"{location}.metadata_anchors must contain at least one anchor "
                "with kind and locator"
            )
        reason = candidate.get("extraction_reason")
        if not isinstance(reason, dict):
            errors.append(f"{location}.extraction_reason must be an object")
        else:
            if not str(
                reason.get("metadata_grounded_rationale") or ""
            ).strip():
                errors.append(
                    f"{location}.extraction_reason.metadata_grounded_rationale is required"
                )
            if not str(reason.get("granularity_rationale") or "").strip():
                errors.append(
                    f"{location}.extraction_reason.granularity_rationale is required"
                )

    summary = artifact.get("summary") or {}
    if summary.get("candidate_count") != len(candidates):
        errors.append(
            "metadata_only_extraction.summary.candidate_count does not match "
            "candidate_concepts length"
        )
    return errors


def _append_forbidden_key_errors(
    errors: list[str],
    location: str,
    value: dict[str, Any],
) -> None:
    forbidden = sorted(key for key in value if key in FORBIDDEN_OUTPUT_KEYS)
    for key in forbidden:
        errors.append(
            f"{location}.{key} is forbidden in Metadata-only Extraction"
        )


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and any(
        isinstance(item, str) and item.strip() for item in value
    )


def _valid_anchors(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for anchor in value:
        if not isinstance(anchor, dict):
            return False
        if not str(anchor.get("kind") or "").strip() or not str(
            anchor.get("locator") or ""
        ).strip():
            return False
    return True
