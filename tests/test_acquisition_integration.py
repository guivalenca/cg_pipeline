"""Dashboard integration for acquisition decisions and founder approvals."""

import json

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

import universe.web.app as web_app
from universe.acquisition.book_scope import get_override, is_missing_scope
from universe.acquisition.gates import GATE_CODES
from universe.spine import attention


P = "acin"


def _seed_linked_source(
    db, tag: str, *, media_type: str = "article", description: str | None = None
) -> tuple[str, str]:
    source_id = f"acqx-{P}-{tag}"
    item_id = f"si_{P}_{tag}"
    syllabus_id = f"syl_{P}_{tag}"
    version_id = f"sv_{P}_{tag}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, %s)",
        (source_id, Jsonb({}), f"Source title {tag}", media_type),
    )
    db.execute(
        "INSERT INTO syllabus (id, title) VALUES (%s, %s)",
        (syllabus_id, f"Syllabus {tag}"),
    )
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES (%s, %s, 1, 'upload')",
        (version_id, syllabus_id),
    )
    db.execute(
        "INSERT INTO syllabus_item"
        " (id, version_id, title, kind, description, source_id)"
        " VALUES (%s, %s, %s, 'reading', %s, %s)",
        (item_id, version_id, f"Item title {tag}", description, source_id),
    )
    db.commit()
    return source_id, item_id


def _record_failed_gate(
    db,
    tag: str,
    source_id: str,
    code: str,
    *,
    created_at: str = "2026-08-03 12:00:00+00",
) -> None:
    run_id = f"r_{P}_{tag}"
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, status, failure_note, created_at)"
        " VALUES (%s, %s, 'failed', %s, %s)",
        (f"snap_{P}_{tag}", source_id, code, created_at),
    )
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, params, status, started_at)"
        " VALUES (%s, 'acquisition', 'firecrawl/v2', 'none', 'none', %s, 'failed', %s)",
        (run_id, Jsonb({"source_ids": [source_id]}), created_at),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response, error)"
        " VALUES (%s, %s, NULL, %s, NULL)",
        (
            f"ri_{P}_{tag}",
            run_id,
            json.dumps(
                {
                    "status": "failed_gate",
                    "failures": [code],
                    "warnings": [],
                    "notes": "runner detail",
                }
            ),
        ),
    )
    db.commit()


def test_attention_uses_gate_kind_note_source_title_and_one_alert_per_source(db):
    source_id, item_id = _seed_linked_source(db, "gate_credentials")
    second_item_id = f"{item_id}_duplicate"
    db.execute(
        "INSERT INTO syllabus_item"
        " (id, version_id, title, kind, source_id)"
        " SELECT %s, version_id, 'A second syllabus title', kind, source_id"
        " FROM syllabus_item WHERE id = %s",
        (second_item_id, item_id),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, status, failure_note)"
        " VALUES (%s, %s, 'failed', 'missing_credentials')",
        (f"snap_{P}_gate_credentials", source_id),
    )
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, 'acquisition', 'firecrawl/v2', 'none', 'none', %s, 'failed')",
        (f"r_{P}_gate_credentials", Jsonb({"source_ids": [source_id]})),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response, error)"
        " VALUES (%s, %s, NULL, %s, NULL)",
        (
            f"ri_{P}_gate_credentials",
            f"r_{P}_gate_credentials",
            json.dumps(
                {
                    "status": "failed_gate",
                    "failures": ["missing_credentials"],
                    "warnings": [],
                    "notes": "ignored in favor of the gate catalog",
                }
            ),
        ),
    )
    db.commit()

    alerts = [item for item in attention(db) if item["source_id"] == source_id]

    assert alerts == [
        {
            "kind": "missing_credentials",
            "title": "Source title gate_credentials",
            "note": GATE_CODES["missing_credentials"]["description"],
            "source_id": source_id,
            "item_id": second_item_id,
        }
    ]


@pytest.mark.parametrize(
    ("code", "expected_kind"),
    [
        ("manual_access_required", "manual_access_required"),
        ("missing_concrete_scope", "missing_concrete_scope"),
        ("unsupported_media_kind", "unsupported_media_kind"),
        ("auth_wall_detected", "acquisition_failed"),
    ],
)
def test_attention_maps_each_gate_family_to_a_founder_kind(
    db, code, expected_kind
):
    tag = f"gate_{code}"
    source_id, _ = _seed_linked_source(db, tag)
    _record_failed_gate(db, tag, source_id, code)

    alert = next(item for item in attention(db) if item["source_id"] == source_id)

    assert alert["kind"] == expected_kind
    assert alert["note"] == GATE_CODES[code]["description"]


def test_attention_uses_only_the_latest_snapshot_for_a_source(db):
    source_id, _ = _seed_linked_source(db, "latest_snapshot")
    _record_failed_gate(
        db,
        "latest_snapshot",
        source_id,
        "fetch_failed",
        created_at="2026-08-03 10:00:00+00",
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, 'recovered', 'ok', '2026-08-03 11:00:00+00')",
        (f"snap_{P}_latest_snapshot_ok", source_id),
    )
    db.commit()

    assert not any(item["source_id"] == source_id for item in attention(db))


@pytest.fixture()
def client(db, test_database_url, monkeypatch):
    db.commit()
    monkeypatch.setattr(web_app, "connect", lambda: psycopg.connect(test_database_url))
    with TestClient(web_app.create_app()) as test_client:
        yield test_client


def test_overview_returns_specific_acquisition_attention_kinds(db, client):
    source_id, _ = _seed_linked_source(db, "overview_gate")
    _record_failed_gate(db, "overview_gate", source_id, "manual_access_required")

    payload = client.get("/api/overview").json()
    alert = next(item for item in payload["attention"] if item["source_id"] == source_id)

    assert alert["kind"] == "manual_access_required"
    assert alert["note"] == GATE_CODES["manual_access_required"]["description"]


def test_scope_override_endpoint_records_reads_and_clears_the_newest_value(db, client):
    source_id, _ = _seed_linked_source(
        db, "scope_override", media_type="book", description="Read this textbook"
    )
    row = {
        "id": source_id,
        "media_type": "book",
        "description": "Read this textbook",
    }
    assert is_missing_scope(db, row)

    first = client.post(
        f"/api/sources/{source_id}/scope-override",
        json={"value": "chapter 4", "note": "Use the assigned chapter"},
    )
    second = client.post(
        f"/api/sources/{source_id}/scope-override",
        json={"value": "pages 40-52", "note": "Founder narrowed the reading"},
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["event_id"] != second.json()["event_id"]
    action, subject, note = db.execute(
        "SELECT action, subject, note FROM curation_event WHERE id = %s",
        (second.json()["event_id"],),
    ).fetchone()
    assert action == "source_scope_override"
    assert subject == {
        "source_id": source_id,
        "value": "pages 40-52",
        "note": "Founder narrowed the reading",
    }
    assert note == "Founder narrowed the reading"
    assert get_override(db, source_id) == "pages 40-52"
    assert not is_missing_scope(db, row)

    cleared = client.post(
        f"/api/sources/{source_id}/scope-override",
        json={"value": None, "note": "Use the syllabus scope again"},
    )

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["value"] is None
    action, subject, note = db.execute(
        "SELECT action, subject, note FROM curation_event WHERE id = %s",
        (cleared.json()["event_id"],),
    ).fetchone()
    assert action == "source_scope_override_cleared"
    assert subject == {
        "source_id": source_id,
        "note": "Use the syllabus scope again",
    }
    assert note == "Use the syllabus scope again"
    assert get_override(db, source_id) is None
    assert is_missing_scope(db, row)


def test_skip_endpoint_records_event_hides_attention_and_marks_syllabus_item(db, client):
    source_id, item_id = _seed_linked_source(db, "skip")
    _record_failed_gate(db, "skip", source_id, "manual_access_required")
    assert any(item["source_id"] == source_id for item in attention(db))

    response = client.post(
        f"/api/sources/{source_id}/skip",
        json={"note": "This reading is not part of the course"},
    )

    assert response.status_code == 200, response.text
    action, subject = db.execute(
        "SELECT action, subject FROM curation_event WHERE id = %s",
        (response.json()["event_id"],),
    ).fetchone()
    assert action == "source_skip"
    assert subject == {
        "source_id": source_id,
        "note": "This reading is not part of the course",
    }
    assert not any(item["source_id"] == source_id for item in attention(db))

    syllabus_id = f"syl_{P}_skip"
    payload = client.get(f"/api/syllabi/{syllabus_id}").json()
    item = next(
        candidate
        for week in payload["latest"]["weeks"]
        for candidate in week["items"]
        if candidate["id"] == item_id
    )
    assert item["source_status"] == "skipped by founder"

    unskipped = client.post(
        f"/api/sources/{source_id}/unskip",
        json={"note": "The reading is part of the course after all"},
    )

    assert unskipped.status_code == 200, unskipped.text
    action, subject = db.execute(
        "SELECT action, subject FROM curation_event WHERE id = %s",
        (unskipped.json()["event_id"],),
    ).fetchone()
    assert action == "source_unskip"
    assert subject == {
        "source_id": source_id,
        "note": "The reading is part of the course after all",
    }
    alert = next(item for item in attention(db) if item["source_id"] == source_id)
    assert alert["kind"] == "manual_access_required"

    payload = client.get(f"/api/syllabi/{syllabus_id}").json()
    item = next(
        candidate
        for week in payload["latest"]["weeks"]
        for candidate in week["items"]
        if candidate["id"] == item_id
    )
    assert item["source_status"] == "failed"
    assert item["source_status"] != "skipped by founder"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("scope-override", {"value": "chapter 2", "note": None}),
        ("skip", {"note": "Not assigned"}),
        ("unskip", {"note": None}),
    ],
)
def test_source_approval_endpoints_return_404_for_unknown_source(client, path, payload):
    response = client.post(f"/api/sources/acqx-{P}-missing/{path}", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found"
