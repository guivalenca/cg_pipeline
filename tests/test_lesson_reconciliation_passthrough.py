from copy import deepcopy

from concept_graph_creation.lesson_ledger import build_lesson_ledger


def _subject_ledger():
    return {
        "artifact_type": "source_ledger",
        "schema_version": "source_ledger.v0",
        "course_id": "cc",
        "module_id": "mod6",
        "subject_id": "COM",
        "lessons": [
            {"lesson_id": "adalove-lesson-a", "display_code": "L01", "title": "A"},
            {"lesson_id": "adalove-lesson-b", "display_code": "L02", "title": "B"},
        ],
        "self_studies": [],
    }


def _reconciliation():
    return {
        "artifact_type": "lesson_reconciliation",
        "schema_version": "lesson_reconciliation.v0",
        "lesson_id": "adalove-lesson-b",
        "reconciled_candidates": [
            {
                "reconciled_candidate_id": "reconciled-candidate-adalove-lesson-b-001",
                "label": "Busca em profundidade",
                "description": "Exploração sistemática de estados.",
                "coverage_criteria": ["Explicar a ordem da busca."],
                "source_candidate_ids": ["candidate-source-b-001"],
                "source_roles": ["introducing"],
                "evidence_types": ["source_body"],
                "evidence": [],
            }
        ],
    }


def test_concept_ids_use_stable_lesson_identity_instead_of_subject_ordinal():
    from concept_graph_creation.stages.lesson_reconciliation_passthrough import (
        build_lesson_reconciliation_passthrough,
    )

    before = _subject_ledger()
    reordered = deepcopy(before)
    reordered["lessons"].reverse()
    reordered["lessons"][0]["display_code"] = "L01"
    reordered["lessons"][1]["display_code"] = "L02"

    first = build_lesson_reconciliation_passthrough(
        source_ledger=build_lesson_ledger(before, "adalove-lesson-b"),
        lesson_reconciliation=_reconciliation(),
    )
    second = build_lesson_reconciliation_passthrough(
        source_ledger=build_lesson_ledger(reordered, "adalove-lesson-b"),
        lesson_reconciliation=_reconciliation(),
    )

    assert first["artifact_type"] == "subject_merge"
    assert first["concepts"][0]["concept_id"] == second["concepts"][0]["concept_id"]
    assert "adalove-lesson-b" in first["concepts"][0]["concept_id"]
    assert first["concepts"][0]["candidate_assignment_status"] == "used_in"
    assert first["concepts"][0]["lesson_reconciliation_refs"] == [
        {
            "artifact_path": (
                "lessons/adalove-lesson-b/lesson_reconciliation.json"
            ),
            "lesson_id": "adalove-lesson-b",
            "reconciled_candidate_id": (
                "reconciled-candidate-adalove-lesson-b-001"
            ),
            "label": "Busca em profundidade",
            "source_candidate_ids": ["candidate-source-b-001"],
            "evidence": [],
        }
    ]
    assert first["candidate_assignments"] == [
        {
            "candidate_id": "reconciled-candidate-adalove-lesson-b-001",
            "status": "used_in",
            "explanation": "Deterministic single-Lesson passthrough.",
            "accepted_concept_ids": [first["concepts"][0]["concept_id"]],
        }
    ]
