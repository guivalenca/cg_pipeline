from pathlib import Path

from universe.syllabus import (
    curate_syllabus,
    get_syllabus_version,
    import_workbook,
    update_source_review,
)
from adalove_workbook import activity, write_adalove_workbook
from universe.syllabus_reconciliation import (
    apply_reconciliation,
    build_plan,
    create_reconciliation,
    get_reconciliation,
)


def _workbook(
    path: Path,
    *,
    description: str = "Descrição original",
    url: str = "https://example.com/original",
    include_orientation: bool = False,
) -> Path:
    lesson = activity(
        title="Aula de arquitetura",
        week=1,
        order=1,
        subject="COM",
        description="Descrição da aula",
        date="11/08/2026",
    )
    source = activity(
        title="Material principal",
        kind="Self-study",
        week=1,
        order=2,
        parent_uuid=lesson["Activity UUID"],
        parent_title=lesson["Title"],
        subject="COM",
        description=description,
        date="11/08/2026",
        url=url,
    )
    activities = [lesson, source]
    if include_orientation:
        activities.append(
            activity(
                title="Orientação descartada",
                kind="Orientation",
                week=1,
                order=3,
                subject=None,
            )
        )
    return write_adalove_workbook(path, activities)


def _manual_projection(detail: dict, *, url: str) -> list[dict]:
    lesson = detail["lessons"][0]
    source = lesson["sources"][0]
    return [
        {
            "id": lesson["id"],
            "week": lesson["week"],
            "kind": lesson["kind"],
            "title": lesson["title"],
            "subject": lesson["subject"],
            "date": str(lesson["date"]),
            "description": lesson["description"],
            "hidden": lesson["hidden"],
            "sources": [
                {
                    "reference_id": source["reference_id"],
                    "title": source["title"],
                    "description": source["description"],
                    "url": url,
                    "media_type": source["media_type"],
                    "resource_code": source["resource_code"],
                    "scope_kind": source["scope_kind"],
                    "scope_value": source["scope_value"],
                    "hidden": True,
                }
            ],
        }
    ]


def test_source_reordering_uses_incoming_order_without_creating_a_decision():
    def source(title: str, seq: int) -> dict:
        return {
            "seq": seq,
            "title": title,
            "description": f"Descrição {title}",
            "url": f"https://example.com/{title.casefold()}",
            "media_type": "article",
            "hidden": False,
        }

    def projection(sources: list[dict]) -> dict:
        return {
            "lessons": [
                {
                    "id": "lesson-current",
                    "week": 1,
                    "seq": 1,
                    "kind": "Class",
                    "title": "Aula",
                    "subject": "SI",
                    "date": "2026-08-11",
                    "description": "Descrição",
                    "hidden": False,
                    "sources": sources,
                }
            ]
        }

    baseline = projection([source("A", 1), source("B", 2)])
    current = projection([source("A", 1), source("B", 2)])
    incoming = projection([source("B", 1), source("A", 2)])

    plan = build_plan(baseline, current, incoming)

    assert plan["summary"]["action_count"] == 0
    assert [item["current"]["title"] for item in plan["lessons"][0]["sources"]] == [
        "B",
        "A",
    ]


def test_adalove_uuids_match_renamed_and_reordered_activities():
    def projection(
        lesson_title: str,
        source_title: str,
        *,
        week: int,
        lesson_order: int,
        source_order: int,
        url: str,
    ) -> dict:
        return {
            "lessons": [
                {
                    "activity_uuid": "lesson-stable-uuid",
                    "folder_uuid": "folder-stable-uuid",
                    "week_order": week,
                    "activity_order": lesson_order,
                    "week": week,
                    "seq": lesson_order,
                    "kind": "Class",
                    "title": lesson_title,
                    "subject": "COM",
                    "subjects": [],
                    "date": "2026-08-11",
                    "description": "Descrição",
                    "hidden": False,
                    "fields": {},
                    "sources": [
                        {
                            "activity_uuid": "source-stable-uuid",
                            "folder_uuid": "folder-stable-uuid",
                            "week_order": week,
                            "activity_order": source_order,
                            "parent_activity_uuid": "lesson-stable-uuid",
                            "parent_inference": "inferred_from_activity_order",
                            "seq": source_order,
                            "title": source_title,
                            "description": "Fonte",
                            "url": url,
                            "media_type": "article",
                            "hidden": False,
                            "fields": {
                                "adalove_material": {
                                    "Source path": "basic_activity_url"
                                }
                            },
                        }
                    ],
                }
            ]
        }

    baseline = projection(
        "Nome anterior",
        "Fonte anterior",
        week=1,
        lesson_order=1,
        source_order=2,
        url="https://example.com/antes",
    )
    incoming = projection(
        "Nome totalmente novo",
        "Fonte totalmente nova",
        week=3,
        lesson_order=14,
        source_order=15,
        url="https://example.com/depois",
    )

    plan = build_plan(baseline, baseline, incoming)

    assert plan["summary"]["lesson_count"] == 1
    assert plan["summary"]["source_count"] == 1
    assert plan["summary"]["action_count"] == 2
    assert plan["lessons"][0]["status"] == "changed"
    assert plan["lessons"][0]["sources"][0]["status"] == "changed"


def test_subject_changes_are_first_class_reconciliation_decisions():
    def projection(subjects: list[str]) -> dict:
        return {
            "lessons": [
                {
                    "id": "lesson-current",
                    "week": 1,
                    "seq": 1,
                    "kind": "Class",
                    "title": "Aula de arquitetura",
                    "subject": "SI",
                    "subjects": subjects,
                    "date": "2026-08-11",
                    "description": "Descrição",
                    "hidden": False,
                    "sources": [],
                }
            ]
        }

    baseline = projection(["Arquitetura de nuvem"])
    current = projection(["Arquitetura de nuvem"])
    incoming = projection(["Arquitetura de nuvem", "Serverless"])

    plan = build_plan(baseline, current, incoming)

    assert plan["summary"]["action_count"] == 1
    lesson = plan["lessons"][0]
    assert lesson["status"] == "changed"
    assert lesson["incoming"]["subjects"] == ["Arquitetura de nuvem", "Serverless"]


def test_identical_institutional_workbook_preserves_manual_overlay_without_review(
    db, tmp_path: Path
):
    original = _workbook(tmp_path / "recon-original.xlsx")
    incoming = _workbook(
        tmp_path / "recon-with-orientation.xlsx", include_orientation=True
    )
    imported = import_workbook(
        db, original, "Reconciliação 1", require_syllabus_metadata=False
    )
    initial = get_syllabus_version(db, imported["syllabus_id"])
    curated = curate_syllabus(
        db,
        imported["syllabus_id"],
        imported["version_id"],
        _manual_projection(initial, url="https://example.com/manual"),
        note="Preserva a curadoria manual.",
    )
    current = get_syllabus_version(db, imported["syllabus_id"])
    reference_id = current["lessons"][0]["sources"][0]["reference_id"]
    update_source_review(
        db,
        imported["syllabus_id"],
        reference_id,
        {"validated": True, "complexity": "complex"},
    )

    preview = create_reconciliation(db, imported["syllabus_id"], incoming)

    assert preview["base_version_id"] == curated["version_id"]
    assert preview["summary"]["action_count"] == 0
    assert preview["dropped_summary"] == {
        "orientation_count": 1,
        "orientation_self_study_count": 0,
        "total_count": 1,
    }
    source = preview["lessons"][0]["sources"][0]
    assert source["status"] == "unchanged"
    assert source["incoming"]["url"] == "https://example.com/manual"
    assert source["incoming"]["hidden"] is True
    assert source["incoming"]["review"] == {
        "validated": True,
        "complexity": "complex",
    }

    result = apply_reconciliation(
        db, imported["syllabus_id"], preview["id"], {}, {}
    )
    assert result["unchanged"] is True
    assert result["version_id"] == curated["version_id"]
    recorded = get_reconciliation(db, imported["syllabus_id"], preview["id"])
    assert recorded["status"] == "applied"


def test_transition_applies_only_changed_workbook_fields_over_manual_settings(
    db, tmp_path: Path
):
    original = _workbook(tmp_path / "recon-delta-original.xlsx")
    incoming = _workbook(
        tmp_path / "recon-delta-incoming.xlsx",
        description="Descrição institucional nova",
    )
    imported = import_workbook(
        db, original, "Reconciliação 2", require_syllabus_metadata=False
    )
    initial = get_syllabus_version(db, imported["syllabus_id"])
    curate_syllabus(
        db,
        imported["syllabus_id"],
        imported["version_id"],
        _manual_projection(initial, url="https://example.com/manual-preservado"),
        note="Preserva a fonte manual durante a reconciliação.",
    )
    current = get_syllabus_version(db, imported["syllabus_id"])
    reference_id = current["lessons"][0]["sources"][0]["reference_id"]
    update_source_review(
        db,
        imported["syllabus_id"],
        reference_id,
        {"validated": True, "complexity": "simple"},
    )

    preview = create_reconciliation(db, imported["syllabus_id"], incoming)
    actions = [
        item
        for lesson in preview["lessons"]
        for item in (lesson, *lesson["sources"])
        if item["status"] != "unchanged"
    ]
    assert [(item["kind"], item["status"]) for item in actions] == [
        ("source", "changed")
    ]
    changed = actions[0]
    assert changed["incoming"]["description"] == "Descrição institucional nova"
    assert changed["incoming"]["url"] == "https://example.com/manual-preservado"
    assert changed["incoming"]["hidden"] is True

    result = apply_reconciliation(
        db,
        imported["syllabus_id"],
        preview["id"],
        {changed["item_id"]: "transition"},
        {},
    )
    assert result["unchanged"] is False
    latest = get_syllabus_version(db, imported["syllabus_id"])
    source = latest["lessons"][0]["sources"][0]
    assert source["description"] == "Descrição institucional nova"
    assert source["url"] == "https://example.com/manual-preservado"
    assert source["hidden"] is True
    assert source["review"] == {"validated": False, "complexity": "simple"}

    repeated = apply_reconciliation(
        db,
        imported["syllabus_id"],
        preview["id"],
        {changed["item_id"]: "transition"},
        {},
    )
    assert repeated["already_applied"] is True
    assert repeated["version_id"] == result["version_id"]
