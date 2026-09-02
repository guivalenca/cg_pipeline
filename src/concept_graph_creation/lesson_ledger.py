"""Adapt a Source Ledger to the per-Lesson creation boundary."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from concept_graph_creation.runtime.generation import ledger_fingerprint
from concept_graph_creation.runtime.stage_runner import StageBlockedError


def build_lesson_ledger(
    source_ledger: dict[str, Any],
    lesson_id: str,
) -> dict[str, Any]:
    """Return the one-Lesson ledger consumed by the vendored creation stages."""

    lessons = [
        lesson
        for lesson in source_ledger.get("lessons") or []
        if isinstance(lesson, dict) and str(lesson.get("lesson_id") or "") == lesson_id
    ]
    if len(lessons) != 1:
        raise StageBlockedError(
            f"Per-Lesson creation requires exactly one Lesson with stable id {lesson_id!r}"
        )

    self_studies = [
        self_study
        for self_study in source_ledger.get("self_studies") or []
        if isinstance(self_study, dict)
        and str(self_study.get("lesson_id") or "") == lesson_id
    ]
    lesson_ledger = deepcopy(source_ledger)
    lesson_ledger["lessons"] = deepcopy(lessons)
    lesson_ledger["self_studies"] = deepcopy(self_studies)
    summary = dict(lesson_ledger.get("summary") or {})
    summary.update(
        {
            "lesson_count": 1,
            "self_study_count": len(self_studies),
            "available_count": sum(
                self_study.get("source_body_status") == "usable_source_body"
                for self_study in self_studies
            ),
            "unavailable_count": sum(
                self_study.get("source_body_status") == "unavailable_source_body"
                for self_study in self_studies
            ),
        }
    )
    lesson_ledger["summary"] = summary
    return lesson_ledger


def lesson_ledger_fingerprint(
    source_ledger: dict[str, Any],
    lesson_id: str,
) -> str:
    """Fingerprint only the selected Lesson and its Source Publications."""

    return ledger_fingerprint(build_lesson_ledger(source_ledger, lesson_id))
