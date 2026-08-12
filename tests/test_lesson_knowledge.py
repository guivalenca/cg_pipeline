"""Public behavior of the durable lesson-local KC build aggregate."""

from __future__ import annotations

import uuid

import pytest
from psycopg.types.json import Jsonb


def _seed_route(db, *, marker: str) -> dict[str, str]:
    ids = {
        "syllabus_id": f"syllabus-lesson-kc-{marker}",
        "version_id": f"syllabus-version-lesson-kc-{marker}",
        "lesson_id": f"syllabus-lesson-kc-{marker}",
    }
    db.execute(
        "INSERT INTO syllabus (id, title) VALUES (%s, 'Sistemas de Informação')",
        (ids["syllabus_id"],),
    )
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES (%s, %s, 1, 'upload')",
        (ids["version_id"], ids["syllabus_id"]),
    )
    db.execute(
        "INSERT INTO syllabus_lesson"
        " (id, version_id, week, seq, kind, title)"
        " VALUES (%s, %s, 6, 1, 'Encontro', 'Aula 6')",
        (ids["lesson_id"], ids["version_id"]),
    )
    return ids


def _seed_publication(db, *, marker: str, suffix: str) -> dict[str, str]:
    ids = {
        "source_id": f"source-lesson-kc-{marker}-{suffix}",
        "snapshot_id": f"snapshot-lesson-kc-{marker}-{suffix}",
        "artifact_id": f"artifact-lesson-kc-{marker}-{suffix}",
    }
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, %s, 'article')",
        (
            ids["source_id"],
            Jsonb({"kind": "url", "value": f"https://example.test/{marker}/{suffix}"}),
            f"Autoestudo {suffix}",
        ),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, %s, 'ok')",
        (ids["snapshot_id"], ids["source_id"], f"sha256-{marker}-{suffix}"),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'legacy-import', %s)",
        (ids["artifact_id"], ids["snapshot_id"], f"# Conteudo {suffix}"),
    )
    return ids


def _attach_reference(
    db,
    *,
    route: dict[str, str],
    publication: dict[str, str],
    reference_id: str,
    seq: int,
    validated: bool = True,
    hidden: bool = False,
) -> None:
    db.execute(
        "INSERT INTO syllabus_source_reference"
        " (id, version_id, lesson_id, seq, title, media_type, source_id, is_hidden)"
        " VALUES (%s, %s, %s, %s, %s, 'article', %s, %s)",
        (
            reference_id,
            route["version_id"],
            route["lesson_id"],
            seq,
            f"Referencia {seq}",
            publication["source_id"],
            hidden,
        ),
    )
    db.execute(
        "INSERT INTO syllabus_source_review (reference_id, is_validated)"
        " VALUES (%s, %s)",
        (reference_id, validated),
    )


def _mark_refresh_incomplete(db, *, source_id: str, marker: str) -> None:
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, failure_code, finished_at, created_at)"
        " VALUES (%s, %s, 'failed', 'firecrawl/v2', 'refresh_failed', now(),"
        " now() + interval '1 second')",
        (f"acquisition-lesson-kc-{marker}", source_id),
    )


def _supersede_publication(
    db,
    *,
    source_id: str,
    marker: str,
) -> dict[str, str]:
    snapshot_id = f"snapshot-lesson-kc-{marker}-new"
    artifact_id = f"artifact-lesson-kc-{marker}-new"
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, %s, 'ok', now() + interval '2 seconds')",
        (snapshot_id, source_id, f"sha256-{marker}-new"),
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, created_at)"
        " VALUES (%s, %s, 'markdown', 'legacy-import', '# Conteudo novo',"
        " now() + interval '2 seconds')",
        (artifact_id, snapshot_id),
    )
    return {"snapshot_id": snapshot_id, "artifact_id": artifact_id}


def test_request_pins_ordered_current_publications_and_reads_queued_build(db):
    from universe.lesson_knowledge import read, request

    marker = uuid.uuid4().hex[:10]
    route = _seed_route(db, marker=marker)
    later = _seed_publication(db, marker=marker, suffix="later")
    first = _seed_publication(db, marker=marker, suffix="first")
    later_reference = f"reference-lesson-kc-{marker}-later"
    first_reference = f"reference-lesson-kc-{marker}-first"
    _attach_reference(
        db,
        route=route,
        publication=later,
        reference_id=later_reference,
        seq=20,
    )
    _attach_reference(
        db,
        route=route,
        publication=first,
        reference_id=first_reference,
        seq=10,
    )

    build = request(
        db,
        route["syllabus_id"],
        route["version_id"],
        route["lesson_id"],
        "create-local-kcs",
        actor="founder",
    )

    assert build["syllabus_id"] == route["syllabus_id"]
    assert build["version_id"] == route["version_id"]
    assert build["lesson_id"] == route["lesson_id"]
    assert build["lesson_title"] == "Aula 6"
    assert build["request_key"] == "create-local-kcs"
    assert build["requested_by"] == "founder"
    assert build["status"] == "queued"
    assert build["progress"] == {
        "total": 2,
        "queued": 2,
        "running": 0,
        "succeeded": 0,
        "failed": 0,
    }
    assert [row["reference_id"] for row in build["references"]] == [
        first_reference,
        later_reference,
    ]
    assert [row["source_id"] for row in build["references"]] == [
        first["source_id"],
        later["source_id"],
    ]
    assert [row["artifact_id"] for row in build["references"]] == [
        first["artifact_id"],
        later["artifact_id"],
    ]
    assert [row["artifact_id"] for row in build["work"]] == [
        first["artifact_id"],
        later["artifact_id"],
    ]
    assert all(row["status"] == "queued" for row in build["work"])
    assert read(db, *route.values(), build["id"]) == build


def test_offer_and_request_reject_a_publication_preserved_from_previous_attempt(db):
    from universe.lesson_knowledge import LessonKnowledgeNotReady, offer, request

    marker = uuid.uuid4().hex[:10]
    route = _seed_route(db, marker=marker)
    publication = _seed_publication(db, marker=marker, suffix="refreshing")
    reference_id = f"reference-lesson-kc-{marker}"
    _attach_reference(
        db,
        route=route,
        publication=publication,
        reference_id=reference_id,
        seq=1,
    )
    _mark_refresh_incomplete(db, source_id=publication["source_id"], marker=marker)

    projection = offer(db, *route.values())

    assert projection["eligibility"] == {
        "eligible": False,
        "code": "publications_not_current",
        "message": "some Source Publications belong to a previous attempt",
        "reference_ids": [],
        "source_ids": [publication["source_id"]],
    }
    assert projection["active_reference_count"] == 1
    assert projection["publication_count"] == 1
    assert projection["latest_build"] is None
    with pytest.raises(LessonKnowledgeNotReady) as caught:
        request(
            db,
            *route.values(),
            "must-not-spend",
            actor="founder",
        )
    assert caught.value.code == "publications_not_current"
    assert caught.value.source_ids == (publication["source_id"],)
    assert db.execute(
        "SELECT count(*) FROM lesson_knowledge_build WHERE lesson_id = %s",
        (route["lesson_id"],),
    ).fetchone()[0] == 0


def test_duplicate_source_references_share_publication_work_but_both_are_pinned(db):
    from universe.lesson_knowledge import request

    marker = uuid.uuid4().hex[:10]
    route = _seed_route(db, marker=marker)
    publication = _seed_publication(db, marker=marker, suffix="shared")
    second_reference = f"reference-lesson-kc-{marker}-second"
    first_reference = f"reference-lesson-kc-{marker}-first"
    _attach_reference(
        db,
        route=route,
        publication=publication,
        reference_id=second_reference,
        seq=2,
    )
    _attach_reference(
        db,
        route=route,
        publication=publication,
        reference_id=first_reference,
        seq=1,
    )

    build = request(db, *route.values(), "deduplicate", actor="founder")

    assert build["progress"]["total"] == 1
    assert len(build["work"]) == 1
    assert build["work"][0]["artifact_id"] == publication["artifact_id"]
    assert build["work"][0]["reference_ids"] == [
        first_reference,
        second_reference,
    ]
    assert [row["reference_id"] for row in build["references"]] == [
        first_reference,
        second_reference,
    ]
    assert {row["work_id"] for row in build["references"]} == {
        build["work"][0]["id"]
    }


def test_route_ownership_is_required_for_request_read_latest_and_offer(db):
    from universe.lesson_knowledge import latest, offer, read, request

    marker = uuid.uuid4().hex[:10]
    route = _seed_route(db, marker=marker)
    publication = _seed_publication(db, marker=marker, suffix="owned")
    _attach_reference(
        db,
        route=route,
        publication=publication,
        reference_id=f"reference-lesson-kc-{marker}",
        seq=1,
    )
    build = request(db, *route.values(), "owned", actor="founder")
    wrong_syllabus = f"syllabus-lesson-kc-{marker}-wrong"

    with pytest.raises(LookupError):
        request(
            db,
            wrong_syllabus,
            route["version_id"],
            route["lesson_id"],
            "owned",
            actor="founder",
        )
    with pytest.raises(LookupError):
        read(
            db,
            wrong_syllabus,
            route["version_id"],
            route["lesson_id"],
            build["id"],
        )
    with pytest.raises(LookupError):
        latest(db, wrong_syllabus, route["version_id"], route["lesson_id"])
    with pytest.raises(LookupError):
        offer(db, wrong_syllabus, route["version_id"], route["lesson_id"])
    assert read(db, *route.values(), "lesson-kc-build-does-not-exist") is None


def test_idempotent_replay_keeps_original_pins_and_latest_tracks_new_request(db):
    from universe.lesson_knowledge import (
        LessonKnowledgeNotReady,
        latest,
        offer,
        request,
    )

    marker = uuid.uuid4().hex[:10]
    route = _seed_route(db, marker=marker)
    publication = _seed_publication(db, marker=marker, suffix="original")
    reference_id = f"reference-lesson-kc-{marker}"
    _attach_reference(
        db,
        route=route,
        publication=publication,
        reference_id=reference_id,
        seq=1,
    )
    first = request(db, *route.values(), "user-click-1", actor="founder")
    newer = _supersede_publication(
        db,
        source_id=publication["source_id"],
        marker=marker,
    )
    db.execute(
        "UPDATE syllabus_source_review SET is_validated = false"
        " WHERE reference_id = %s",
        (reference_id,),
    )

    replay = request(db, *route.values(), "user-click-1", actor="someone-else")

    assert replay == first
    assert replay["work"][0]["artifact_id"] == publication["artifact_id"]
    with pytest.raises(LessonKnowledgeNotReady) as caught:
        request(db, *route.values(), "user-click-2", actor="founder")
    assert caught.value.code == "references_not_validated"

    db.execute(
        "UPDATE syllabus_source_review SET is_validated = true"
        " WHERE reference_id = %s",
        (reference_id,),
    )
    second = request(db, *route.values(), "user-click-2", actor="founder")

    assert second["id"] != first["id"]
    assert second["work"][0]["artifact_id"] == newer["artifact_id"]
    assert latest(db, *route.values()) == second
    assert offer(db, *route.values())["latest_build"] == second
    assert db.execute(
        "SELECT count(*) FROM lesson_knowledge_build WHERE lesson_id = %s",
        (route["lesson_id"],),
    ).fetchone()[0] == 2


def test_only_active_validated_references_participate_in_the_offer_and_build(db):
    from universe.lesson_knowledge import LessonKnowledgeNotReady, offer, request

    marker = uuid.uuid4().hex[:10]
    route = _seed_route(db, marker=marker)
    active = _seed_publication(db, marker=marker, suffix="active")
    hidden = _seed_publication(db, marker=marker, suffix="hidden")
    active_reference = f"reference-lesson-kc-{marker}-active"
    hidden_reference = f"reference-lesson-kc-{marker}-hidden"
    _attach_reference(
        db,
        route=route,
        publication=active,
        reference_id=active_reference,
        seq=1,
        validated=False,
    )
    _attach_reference(
        db,
        route=route,
        publication=hidden,
        reference_id=hidden_reference,
        seq=2,
        validated=False,
        hidden=True,
    )

    blocked = offer(db, *route.values())

    assert blocked["active_reference_count"] == 1
    assert blocked["eligibility"]["code"] == "references_not_validated"
    assert blocked["eligibility"]["reference_ids"] == [active_reference]
    with pytest.raises(LessonKnowledgeNotReady) as caught:
        request(db, *route.values(), "before-review", actor="founder")
    assert caught.value.reference_ids == (active_reference,)

    db.execute(
        "UPDATE syllabus_source_review SET is_validated = true"
        " WHERE reference_id = %s",
        (active_reference,),
    )
    ready = offer(db, *route.values())
    build = request(db, *route.values(), "after-review", actor="founder")

    assert ready["eligibility"] == {
        "eligible": True,
        "code": "ready",
        "message": "lesson is ready for local KC work",
        "reference_ids": [],
        "source_ids": [],
    }
    assert ready["active_reference_count"] == 1
    assert ready["publication_count"] == 1
    assert [row["reference_id"] for row in build["references"]] == [
        active_reference
    ]
    assert [row["source_id"] for row in build["work"]] == [active["source_id"]]


def test_offer_explains_missing_current_publication_without_creating_a_build(db):
    from universe.lesson_knowledge import LessonKnowledgeNotReady, offer, request

    marker = uuid.uuid4().hex[:10]
    route = _seed_route(db, marker=marker)
    source_id = f"source-lesson-kc-{marker}-empty"
    reference_id = f"reference-lesson-kc-{marker}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Ainda sem Markdown', 'article')",
        (
            source_id,
            Jsonb({"kind": "url", "value": f"https://example.test/{marker}/empty"}),
        ),
    )
    _attach_reference(
        db,
        route=route,
        publication={"source_id": source_id},
        reference_id=reference_id,
        seq=1,
    )

    projection = offer(db, *route.values())

    assert projection["eligibility"]["code"] == "publications_unavailable"
    assert projection["eligibility"]["source_ids"] == [source_id]
    assert projection["publication_count"] == 0
    with pytest.raises(LessonKnowledgeNotReady) as caught:
        request(db, *route.values(), "not-ready", actor="founder")
    assert caught.value.code == "publications_unavailable"
    assert db.execute(
        "SELECT count(*) FROM lesson_knowledge_build WHERE lesson_id = %s",
        (route["lesson_id"],),
    ).fetchone()[0] == 0


def test_read_derives_aggregate_status_and_progress_from_publication_work(db):
    from universe.lesson_knowledge import read, request

    marker = uuid.uuid4().hex[:10]
    route = _seed_route(db, marker=marker)
    first = _seed_publication(db, marker=marker, suffix="first-status")
    second = _seed_publication(db, marker=marker, suffix="second-status")
    _attach_reference(
        db,
        route=route,
        publication=first,
        reference_id=f"reference-lesson-kc-{marker}-first",
        seq=1,
    )
    _attach_reference(
        db,
        route=route,
        publication=second,
        reference_id=f"reference-lesson-kc-{marker}-second",
        seq=2,
    )
    build = request(db, *route.values(), "status", actor="founder")
    first_work, second_work = [row["id"] for row in build["work"]]

    db.execute(
        "UPDATE lesson_knowledge_work"
        " SET status = 'succeeded', stage = 'local-complete', updated_at = now()"
        " WHERE id = %s",
        (first_work,),
    )
    running = read(db, *route.values(), build["id"])
    assert running is not None
    assert running["status"] == "running"
    assert running["progress"] == {
        "total": 2,
        "queued": 1,
        "running": 0,
        "succeeded": 1,
        "failed": 0,
    }

    db.execute(
        "UPDATE lesson_knowledge_work"
        " SET status = 'failed', stage = 'statements',"
        " failure_code = 'invalid_evidence', diagnostics = %s, updated_at = now()"
        " WHERE id = %s",
        (Jsonb({"retryable": True}), second_work),
    )
    failed = read(db, *route.values(), build["id"])
    assert failed is not None
    assert failed["status"] == "failed"
    assert failed["progress"]["failed"] == 1
    assert failed["work"][1]["failure_code"] == "invalid_evidence"
    assert failed["work"][1]["diagnostics"] == {"retryable": True}

    db.execute(
        "UPDATE lesson_knowledge_work"
        " SET status = 'succeeded', stage = 'local-complete', failure_code = NULL,"
        " diagnostics = '{}'::jsonb, updated_at = now() WHERE id = %s",
        (second_work,),
    )
    succeeded = read(db, *route.values(), build["id"])
    assert succeeded is not None
    assert succeeded["status"] == "succeeded"
    assert succeeded["progress"] == {
        "total": 2,
        "queued": 0,
        "running": 0,
        "succeeded": 2,
        "failed": 0,
    }
