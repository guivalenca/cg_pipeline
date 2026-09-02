"""Curation edits: founder corrections overlay syllabus facts, never rewrite them."""

import pytest

from universe.curation import edit_history, effective_fields, record_edit
from universe.syllabus import import_workbook
from adalove_workbook import activity, write_adalove_workbook


def _row(project, week, seq, title, kind="Autoestudo", description="Desc", url=None):
    return {
        "project": project,
        "week": week,
        "seq": seq,
        "title": title,
        "description": description,
        "url": url,
    }


def _save(path, rows):
    project = rows[0]["project"]
    week = rows[0]["week"]
    lesson = activity(title="Lesson", week=week, order=1, subject="COM")
    sources = [
        activity(
            title=row["title"],
            kind="Self-study",
            week=row["week"],
            order=row["seq"] + 1,
            parent_uuid=lesson["Activity UUID"],
            parent_title=lesson["Title"],
            description=row["description"],
            url=row["url"],
        )
        for row in rows
    ]
    write_adalove_workbook(path, [lesson, *sources], project=project)


class TestRecordEdit:
    """Append edit events and read them back as overlay and history."""

    def test_title_edit_overlays_without_touching_fact(self, db, tmp_path):
        path = tmp_path / "cur-title.xlsx"
        _save(path, [_row("TEST-CURA-TITLE", 1, 1, "Original title",
                          url="https://curation.test/title")])
        version_id = import_workbook(
            db, path, "TEST-CURA-TITLE", require_syllabus_metadata=False
        )["version_id"]
        item_id = f"{version_id}:source:0001"

        event = record_edit(db, item_id, "title", "Fixed title", "founder", "typo fix")

        assert event["old"] == "Original title"
        assert event["new"] == "Fixed title"
        assert effective_fields(db, [item_id]) == {item_id: {"title": "Fixed title"}}
        history = edit_history(db, [item_id])[item_id]
        assert [(e["field"], e["old"], e["new"], e["note"]) for e in history] == [
            ("title", "Original title", "Fixed title", "typo fix")
        ]
        # The imported workbook fact stays exactly as received.
        stored = db.execute(
            "SELECT title FROM syllabus_item WHERE id = %s", (item_id,)
        ).fetchone()
        assert stored == ("Original title",)

    def test_edits_chain_from_the_effective_value(self, db, tmp_path):
        path = tmp_path / "cur-chain.xlsx"
        _save(path, [_row("TEST-CURA-CHAIN", 1, 1, "First",
                          url="https://curation.test/chain")])
        version_id = import_workbook(
            db, path, "TEST-CURA-CHAIN", require_syllabus_metadata=False
        )["version_id"]
        item_id = f"{version_id}:source:0001"

        record_edit(db, item_id, "title", "Second", "founder")
        record_edit(db, item_id, "title", "Third", "founder")

        assert effective_fields(db, [item_id])[item_id]["title"] == "Third"
        history = edit_history(db, [item_id])[item_id]
        assert [(e["old"], e["new"]) for e in history] == [
            ("Second", "Third"),  # newest first, old read at write time
            ("First", "Second"),
        ]

    def test_url_edit_relinks_item_to_resolved_source(self, db, tmp_path):
        path = tmp_path / "cur-url.xlsx"
        _save(path, [_row("TEST-CURA-URL", 1, 1, "Reading",
                          url="https://curation.test/before")])
        version_id = import_workbook(
            db, path, "TEST-CURA-URL", require_syllabus_metadata=False
        )["version_id"]
        item_id = f"{version_id}:source:0001"
        original_source = db.execute(
            "SELECT source_id FROM syllabus_item WHERE id = %s", (item_id,)
        ).fetchone()[0]

        event = record_edit(
            db, item_id, "url",
            "https://curation.test/after?utm_source=mail", "founder",
        )

        overlay = effective_fields(db, [item_id])[item_id]
        assert overlay["url"] == "https://curation.test/after?utm_source=mail"
        assert overlay["source_id"] == event["source_id"]
        assert overlay["source_id"] != original_source
        # The event minted (or resolved) the canonical source row.
        identity = db.execute(
            "SELECT identity FROM source WHERE id = %s", (event["source_id"],)
        ).fetchone()[0]
        assert identity == {"canonical_url": "https://curation.test/after"}
        # The stored item still carries the workbook's url and source link.
        stored = db.execute(
            "SELECT url, source_id FROM syllabus_item WHERE id = %s", (item_id,)
        ).fetchone()
        assert stored == ("https://curation.test/before", original_source)

    def test_rejects_unknown_field_value_and_item(self, db, tmp_path):
        path = tmp_path / "cur-reject.xlsx"
        _save(path, [_row("TEST-CURA-REJECT", 1, 1, "Lesson",
                          url="https://curation.test/reject")])
        version_id = import_workbook(
            db, path, "TEST-CURA-REJECT", require_syllabus_metadata=False
        )["version_id"]
        item_id = f"{version_id}:source:0001"

        with pytest.raises(ValueError, match="field must be one of"):
            record_edit(db, item_id, "week", "2", "founder")
        with pytest.raises(ValueError, match="non-empty string"):
            record_edit(db, item_id, "title", "   ", "founder")
        with pytest.raises(LookupError, match="unknown syllabus item"):
            record_edit(db, "test-cura-missing:v0001:0001", "title", "X", "founder")


class TestEditsBesideImport:
    """Edits live beside the versioned workbook facts, not inside them."""

    def test_reupload_of_unchanged_workbook_records_nothing(self, db, tmp_path):
        path = tmp_path / "cur-reup.xlsx"
        _save(path, [_row("TEST-CURA-REUP", 1, 1, "Lesson",
                          url="https://curation.test/reup")])
        first = import_workbook(
            db, path, "TEST-CURA-REUP", require_syllabus_metadata=False
        )
        item_id = f"{first['version_id']}:source:0001"
        record_edit(db, item_id, "title", "Edited", "founder")

        again = import_workbook(
            db, path, "TEST-CURA-REUP", require_syllabus_metadata=False
        )

        assert again["unchanged"] is True
        assert again["version_id"] == first["version_id"]
        versions = db.execute(
            "SELECT count(*) FROM syllabus_version WHERE syllabus_id = %s",
            ("test-cura-reup",),
        ).fetchone()[0]
        assert versions == 1
        uploads = db.execute(
            "SELECT count(*) FROM curation_event"
            " WHERE action = 'syllabus_upload' AND subject->>'syllabus_id' = %s",
            ("test-cura-reup",),
        ).fetchone()[0]
        assert uploads == 1
        edits = db.execute(
            "SELECT count(*) FROM curation_event"
            " WHERE action = 'syllabus_item_edit' AND subject->>'item_id' = %s",
            (item_id,),
        ).fetchone()[0]
        assert edits == 1
