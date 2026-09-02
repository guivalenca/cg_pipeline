"""Deterministically adapt one Lesson Reconciliation to Subject Merge shape."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Any

from concept_graph_creation.runtime.generation import ledger_fingerprint
from concept_graph_creation.runtime.stage_runner import StageBlockedError


def build_lesson_reconciliation_passthrough(
    *,
    source_ledger: dict[str, Any],
    lesson_reconciliation: dict[str, Any],
) -> dict[str, Any]:
    """Produce downstream-compatible Subject Merge shape without merging Lessons."""

    errors = validate_lesson_reconciliation_passthrough_inputs(
        source_ledger=source_ledger,
        lesson_reconciliation=lesson_reconciliation,
    )
    if errors:
        raise StageBlockedError(
            "Lesson Reconciliation passthrough failed Stage Contract: "
            + "; ".join(errors)
        )

    lesson = deepcopy(source_ledger["lessons"][0])
    lesson_id = str(lesson["lesson_id"])
    concepts = [
        _concept_from_reconciled_candidate(
            lesson=lesson,
            candidate=candidate,
        )
        for candidate in lesson_reconciliation["reconciled_candidates"]
    ]
    return {
        "artifact_type": "subject_merge",
        "schema_version": "subject_merge.v0",
        "source_artifact": "source_ledger.json",
        "lesson_reconciliation_artifact": (
            f"lessons/{lesson_id}/lesson_reconciliation.json"
        ),
        "course_id": source_ledger.get("course_id"),
        "module_id": source_ledger.get("module_id"),
        "subject_id": source_ledger.get("subject_id"),
        "ledger_fingerprint": ledger_fingerprint(source_ledger),
        "concepts": concepts,
        "candidate_assignments": [
            {
                "candidate_id": concept["source_candidate_ids"][0],
                "status": "used_in",
                "explanation": "Deterministic single-Lesson passthrough.",
                "accepted_concept_ids": [concept["concept_id"]],
            }
            for concept in concepts
        ],
        "pruned_candidates": deepcopy(
            lesson_reconciliation.get("pruned_candidates") or []
        ),
        "review_candidates": deepcopy(
            lesson_reconciliation.get("review_candidates") or []
        ),
        "summary": {
            "concept_count": len(concepts),
            "input_candidate_count": len(
                lesson_reconciliation.get("reconciled_candidates") or []
            ),
            "pruned_candidate_count": len(
                lesson_reconciliation.get("pruned_candidates") or []
            ),
            "review_candidate_count": len(
                lesson_reconciliation.get("review_candidates") or []
            ),
            "lesson_count": 1,
            "subject_merge_omitted": True,
        },
    }


def run_lesson_reconciliation_passthrough_phase(*, run_dir: Path) -> dict[str, Any]:
    source_ledger = _read_json(run_dir / "source_ledger.json")
    lessons = source_ledger.get("lessons") or []
    if len(lessons) != 1 or not isinstance(lessons[0], dict):
        raise StageBlockedError(
            "Lesson Reconciliation passthrough requires a per-Lesson Source Ledger"
        )
    lesson_id = str(lessons[0].get("lesson_id") or "")
    reconciliation_path = (
        run_dir / "lessons" / lesson_id / "lesson_reconciliation.json"
    )
    if not reconciliation_path.is_file():
        raise StageBlockedError(
            "Lesson Reconciliation passthrough requires "
            f"lessons/{lesson_id}/lesson_reconciliation.json"
        )
    artifact = build_lesson_reconciliation_passthrough(
        source_ledger=source_ledger,
        lesson_reconciliation=_read_json(reconciliation_path),
    )
    output_path = run_dir / "subject_merge.json"
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "summary": artifact["summary"],
        "artifact_path": output_path,
        "ledger_fingerprint": artifact["ledger_fingerprint"],
    }


def validate_lesson_reconciliation_passthrough_inputs(
    *,
    source_ledger: dict[str, Any],
    lesson_reconciliation: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    lessons = source_ledger.get("lessons")
    if not isinstance(lessons, list) or len(lessons) != 1:
        return ["source_ledger.lessons must contain exactly one Lesson"]
    lesson = lessons[0]
    lesson_id = str(lesson.get("lesson_id") or "") if isinstance(lesson, dict) else ""
    if not lesson_id:
        errors.append("source_ledger Lesson requires its stable lesson_id")
    if lesson_reconciliation.get("artifact_type") != "lesson_reconciliation":
        errors.append(
            "lesson_reconciliation.artifact_type must be 'lesson_reconciliation'"
        )
    if str(lesson_reconciliation.get("lesson_id") or "") != lesson_id:
        errors.append(
            "lesson_reconciliation.lesson_id must match the Source Ledger Lesson"
        )
    candidates = lesson_reconciliation.get("reconciled_candidates")
    if not isinstance(candidates, list):
        errors.append("lesson_reconciliation.reconciled_candidates must be a list")
        return errors
    seen_ids: set[str] = set()
    for index, candidate in enumerate(candidates):
        location = f"lesson_reconciliation.reconciled_candidates[{index}]"
        if not isinstance(candidate, dict):
            errors.append(f"{location} must be an object")
            continue
        candidate_id = str(candidate.get("reconciled_candidate_id") or "")
        if not candidate_id:
            errors.append(f"{location}.reconciled_candidate_id is required")
        elif candidate_id in seen_ids:
            errors.append(f"{location}.reconciled_candidate_id is duplicated")
        seen_ids.add(candidate_id)
        for field in ("label", "description"):
            if not str(candidate.get(field) or "").strip():
                errors.append(f"{location}.{field} is required")
        coverage = candidate.get("coverage_criteria")
        if not isinstance(coverage, list) or not any(
            isinstance(item, str) and item.strip() for item in coverage
        ):
            errors.append(f"{location}.coverage_criteria must contain text")
    return errors


def _concept_from_reconciled_candidate(
    *,
    lesson: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    lesson_id = str(lesson["lesson_id"])
    candidate_id = str(candidate["reconciled_candidate_id"])
    concept_id = _concept_id(
        lesson_id=lesson_id,
        candidate_id=candidate_id,
        candidate=candidate,
    )
    return {
        "concept_id": concept_id,
        "label": candidate.get("label"),
        "description": candidate.get("description"),
        "coverage_criteria": deepcopy(candidate.get("coverage_criteria") or []),
        "common_misconceptions": deepcopy(
            candidate.get("common_misconceptions") or []
        ),
        "source_candidate_ids": [candidate_id],
        "candidate_assignment_status": "used_in",
        "lesson_reconciliation_refs": [
            {
                "artifact_path": f"lessons/{lesson_id}/lesson_reconciliation.json",
                "lesson_id": lesson_id,
                "reconciled_candidate_id": candidate_id,
                "label": candidate.get("label"),
                "source_candidate_ids": deepcopy(
                    candidate.get("source_candidate_ids") or []
                ),
                "evidence": deepcopy(candidate.get("evidence") or []),
            }
        ],
        "occurrences": [
            {
                "lesson": {
                    "lesson_id": lesson_id,
                    "title": lesson.get("title"),
                },
                "source_candidate_ids": deepcopy(
                    candidate.get("source_candidate_ids") or []
                ),
                "source_roles": deepcopy(candidate.get("source_roles") or []),
                "evidence_types": deepcopy(candidate.get("evidence_types") or []),
                "depth": candidate.get("depth"),
            }
        ],
        "depth": candidate.get("depth"),
        "merge_rationale": (
            "Deterministic per-Lesson passthrough; Subject Merge is omitted."
        ),
    }


def _concept_id(
    *,
    lesson_id: str,
    candidate_id: str,
    candidate: dict[str, Any],
) -> str:
    identity = {
        "lesson_id": lesson_id,
        "reconciled_candidate_id": candidate_id,
        "label": candidate.get("label"),
        "description": candidate.get("description"),
        "coverage_criteria": candidate.get("coverage_criteria") or [],
    }
    canonical = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:8]
    return f"concept-{_slug(lesson_id)}-{_slug(str(candidate.get('label') or 'concept'))}-{digest}"


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "concept"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
