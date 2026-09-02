from copy import deepcopy


def _subject_ledger():
    return {
        "artifact_type": "source_ledger",
        "schema_version": "source_ledger.v0",
        "course_id": "cc",
        "module_id": "mod6",
        "subject_id": "COM",
        "lessons": [
            {"lesson_id": "lesson-a", "title": "A"},
            {"lesson_id": "lesson-b", "title": "B"},
        ],
        "self_studies": [
            {"self_study_id": "source-a", "lesson_id": "lesson-a"},
            {"self_study_id": "source-b", "lesson_id": "lesson-b"},
        ],
    }


def test_changing_one_lesson_does_not_invalidate_another_lesson_ledger():
    from concept_graph_creation.lesson_ledger import lesson_ledger_fingerprint

    before = _subject_ledger()
    after = deepcopy(before)
    after["lessons"][1]["title"] = "B revisada"
    after["self_studies"][1]["source_body"] = {"sha256": "new-publication"}

    assert lesson_ledger_fingerprint(before, "lesson-a") == lesson_ledger_fingerprint(
        after, "lesson-a"
    )
    assert lesson_ledger_fingerprint(before, "lesson-b") != lesson_ledger_fingerprint(
        after, "lesson-b"
    )
