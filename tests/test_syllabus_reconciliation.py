from pathlib import Path

from openpyxl import Workbook

from universe.syllabus import (
    LEGACY_COLUMNS,
    curate_syllabus,
    get_syllabus_version,
    import_workbook,
    parse_workbook,
    update_source_review,
)
from universe.syllabus_reconciliation import (
    apply_reconciliation,
    build_plan,
    create_reconciliation,
    get_reconciliation,
)


def _workbook(path: Path, *, description: str = "Descrição original", url: str = "https://example.com/original") -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "All"
    sheet.append(LEGACY_COLUMNS)
    lesson = {
        "Week": 1,
        "Sort": 1,
        "Type": "Class",
        "Title": "Aula de arquitetura",
        "Date": "11/08/2026",
        "Axis": "SI",
        "Description": "Descrição da aula",
    }
    source = {
        "Week": 1,
        "Sort": 2,
        "Type": "Self-study",
        "Title": "Material principal",
        "Date": "11/08/2026",
        "Parent class": "Aula de arquitetura",
        "Axis": "SI",
        "Description": description,
        "URL": url,
    }
    sheet.append([lesson.get(column) for column in LEGACY_COLUMNS])
    sheet.append([source.get(column) for column in LEGACY_COLUMNS])
    workbook.save(path)
    workbook.close()
    return path


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


def test_related_workbook_infers_one_unambiguous_orphan_source_parent(tmp_path: Path):
    path = tmp_path / "orphan-with-institutional-metadata.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "All"
    sheet.append(LEGACY_COLUMNS)
    source = {
        "Week": 1,
        "Sort": 1,
        "Type": "Self-study",
        "Title": "Fonte órfã",
        "Professor": "Professora Única",
        "Axis": "COM",
        "URL": "https://example.com/orphan",
    }
    lesson = {
        "Week": 1,
        "Sort": 8,
        "Type": "Class",
        "Title": "Aula inferida",
        "Date": "11/08/2026",
        "Professor": "Professora Única",
        "Axis": "COM",
    }
    sheet.append([source.get(column) for column in LEGACY_COLUMNS])
    sheet.append([lesson.get(column) for column in LEGACY_COLUMNS])
    workbook.save(path)
    workbook.close()

    parsed = parse_workbook(path)

    assert parsed["lessons"][0]["title"] == "Aula inferida"
    assert [item["title"] for item in parsed["lessons"][0]["source_references"]] == [
        "Fonte órfã"
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
    imported = import_workbook(db, original, "Reconciliação 1")
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

    preview = create_reconciliation(db, imported["syllabus_id"], original)

    assert preview["base_version_id"] == curated["version_id"]
    assert preview["summary"]["action_count"] == 0
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
    imported = import_workbook(db, original, "Reconciliação 2")
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
