"""HTTP contract for explicit lesson-local Knowledge Builds."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from universe.web.app import create_app

from test_lesson_knowledge import (
    _attach_reference,
    _seed_publication,
    _seed_route,
    _supersede_publication,
)


def _client(database_url: str) -> TestClient:
    return TestClient(create_app(lambda: psycopg.connect(database_url)))


def _url(route: dict[str, str]) -> str:
    return (
        f"/api/syllabi/{route['syllabus_id']}"
        f"/versions/{route['version_id']}"
        f"/lessons/{route['lesson_id']}"
    )


def _add_lesson(
    db,
    *,
    route: dict[str, str],
    marker: str,
    seq: int,
) -> str:
    lesson_id = f"syllabus-lesson-kc-{marker}-{seq}"
    db.execute(
        "INSERT INTO syllabus_lesson"
        " (id, version_id, week, seq, kind, title)"
        " VALUES (%s, %s, %s, %s, 'Encontro', %s)",
        (lesson_id, route["version_id"], seq, seq, f"Aula {seq}"),
    )
    return lesson_id


def _complete_work_summary(db, work_id: str, *, kc_count: int = 3) -> None:
    db.execute(
        "UPDATE lesson_knowledge_work"
        " SET status = 'succeeded', stage = NULL,"
        " diagnostics = %s, updated_at = now() WHERE id = %s",
        (
            Jsonb(
                {
                    "completed_stage_count": 11,
                    "total_stage_count": 11,
                    "kc_count": kc_count,
                }
            ),
            work_id,
        ),
    )


def test_lesson_knowledge_http_offer_request_and_pinned_build_read(
    test_database_url,
    applied_migrations,
    db,
):
    marker = "web-offer"
    route = _seed_route(db, marker=marker)
    publication = _seed_publication(db, marker=marker, suffix="source")
    reference_id = f"reference-lesson-kc-{marker}"
    _attach_reference(
        db,
        route=route,
        publication=publication,
        reference_id=reference_id,
        seq=1,
    )
    db.commit()

    with _client(test_database_url) as client:
        offered = client.get(f"{_url(route)}/knowledge")
        assert offered.status_code == 200, offered.text
        assert offered.json()["eligibility"]["code"] == "ready"
        assert offered.json()["latest_build"] is None

        started = client.post(
            f"{_url(route)}/knowledge-builds",
            json={"request_key": "browser-click-1"},
        )
        assert started.status_code == 202, started.text
        build = started.json()
        assert build["request_key"] == "browser-click-1"
        assert build["current"] is True
        assert build["work"][0]["artifact_id"] == publication["artifact_id"]
        assert tuple(build["work"][0]["snapshot"]["stages"]) == (
            "blocks",
            "passage-cuts",
            "passage-triage",
            "task-generation",
            "task-granularity",
            "task-revision",
            "task-triage",
            "task-substance",
            "kc-statement",
            "task-modality",
            "task-knowledge",
        )

        replay = client.post(
            f"{_url(route)}/knowledge-builds",
            json={"request_key": "browser-click-1"},
        )
        assert replay.status_code == 202
        assert replay.json()["id"] == build["id"]

        read = client.get(f"/api/knowledge-builds/{build['id']}")
        assert read.status_code == 200, read.text
        assert read.json() == replay.json()


def test_syllabus_detail_reuses_one_completed_source_publication_across_lessons(
    test_database_url,
    applied_migrations,
    db,
):
    marker = "web-reused-source"
    first_route = _seed_route(db, marker=marker)
    second_lesson_id = _add_lesson(
        db,
        route=first_route,
        marker=marker,
        seq=2,
    )
    publication = _seed_publication(db, marker=marker, suffix="shared")
    _attach_reference(
        db,
        route=first_route,
        publication=publication,
        reference_id=f"reference-lesson-kc-{marker}-first",
        seq=1,
    )
    second_route = {**first_route, "lesson_id": second_lesson_id}
    _attach_reference(
        db,
        route=second_route,
        publication=publication,
        reference_id=f"reference-lesson-kc-{marker}-second",
        seq=1,
    )
    db.commit()

    with _client(test_database_url) as client:
        started = client.post(
            f"{_url(first_route)}/knowledge-builds",
            json={"request_key": "create-shared-once"},
        )
        assert started.status_code == 202, started.text
        build = started.json()
        _complete_work_summary(db, build["work"][0]["id"], kc_count=4)
        db.commit()

        detail = client.get(f"/api/syllabi/{first_route['syllabus_id']}")
        assert detail.status_code == 200, detail.text
        lessons = {lesson["id"]: lesson for lesson in detail.json()["lessons"]}

        own = lessons[first_route["lesson_id"]]
        reused = lessons[second_lesson_id]
        assert own["knowledge"]["latest_build"]["id"] == build["id"]
        assert reused["knowledge"]["latest_build"] is None
        assert reused["sources"][0]["knowledge"] == {
            "build_id": build["id"],
            "work_id": build["work"][0]["id"],
            "status": "succeeded",
            "current": True,
            "kc_count": 4,
            "snapshot": None,
        }

    assert db.execute(
        "SELECT count(*) FROM lesson_knowledge_build WHERE version_id = %s",
        (first_route["version_id"],),
    ).fetchone()[0] == 1
    assert db.execute(
        "SELECT count(*) FROM lesson_knowledge_work WHERE artifact_id = %s",
        (publication["artifact_id"],),
    ).fetchone()[0] == 1


def test_syllabus_detail_does_not_reuse_kcs_after_the_publication_is_superseded(
    test_database_url,
    applied_migrations,
    db,
):
    marker = "web-reused-superseded"
    first_route = _seed_route(db, marker=marker)
    second_lesson_id = _add_lesson(
        db,
        route=first_route,
        marker=marker,
        seq=2,
    )
    publication = _seed_publication(db, marker=marker, suffix="shared")
    _attach_reference(
        db,
        route=first_route,
        publication=publication,
        reference_id=f"reference-lesson-kc-{marker}-first",
        seq=1,
    )
    _attach_reference(
        db,
        route={**first_route, "lesson_id": second_lesson_id},
        publication=publication,
        reference_id=f"reference-lesson-kc-{marker}-second",
        seq=1,
    )
    db.commit()

    with _client(test_database_url) as client:
        started = client.post(
            f"{_url(first_route)}/knowledge-builds",
            json={"request_key": "create-before-refresh"},
        )
        assert started.status_code == 202, started.text
        build = started.json()
        _complete_work_summary(db, build["work"][0]["id"])
        _supersede_publication(
            db,
            source_id=publication["source_id"],
            marker=marker,
        )
        db.commit()

        detail = client.get(f"/api/syllabi/{first_route['syllabus_id']}")
        assert detail.status_code == 200, detail.text
        lessons = {lesson["id"]: lesson for lesson in detail.json()["lessons"]}
        assert "knowledge" not in lessons[second_lesson_id]["sources"][0]


@pytest.mark.parametrize("invalid_state", ["partial", "failed", "impure-build"])
def test_syllabus_detail_reuses_only_a_wholly_succeeded_current_build(
    test_database_url,
    applied_migrations,
    db,
    invalid_state,
):
    marker = f"web-reused-{invalid_state}"
    first_route = _seed_route(db, marker=marker)
    second_lesson_id = _add_lesson(
        db,
        route=first_route,
        marker=marker,
        seq=2,
    )
    publication = _seed_publication(db, marker=marker, suffix="shared")
    _attach_reference(
        db,
        route=first_route,
        publication=publication,
        reference_id=f"reference-lesson-kc-{marker}-first",
        seq=1,
    )
    _attach_reference(
        db,
        route={**first_route, "lesson_id": second_lesson_id},
        publication=publication,
        reference_id=f"reference-lesson-kc-{marker}-second",
        seq=1,
    )
    sibling = None
    if invalid_state == "impure-build":
        sibling = _seed_publication(db, marker=marker, suffix="sibling")
        _attach_reference(
            db,
            route=first_route,
            publication=sibling,
            reference_id=f"reference-lesson-kc-{marker}-sibling",
            seq=2,
        )
    db.commit()

    with _client(test_database_url) as client:
        started = client.post(
            f"{_url(first_route)}/knowledge-builds",
            json={"request_key": "invalid-for-reuse"},
        )
        assert started.status_code == 202, started.text
        build = started.json()
        shared_work = next(
            work
            for work in build["work"]
            if work["artifact_id"] == publication["artifact_id"]
        )
        if invalid_state == "partial":
            db.execute(
                "UPDATE lesson_knowledge_work"
                " SET status = 'running', stage = 'task-generation',"
                " diagnostics = %s, updated_at = now() WHERE id = %s",
                (
                    Jsonb(
                        {
                            "completed_stage_count": 4,
                            "total_stage_count": 11,
                            "kc_count": 0,
                        }
                    ),
                    shared_work["id"],
                ),
            )
        else:
            _complete_work_summary(db, shared_work["id"])
        if invalid_state == "failed":
            db.execute(
                "UPDATE lesson_knowledge_work"
                " SET status = 'failed', stage = 'kc-statement',"
                " failure_code = 'invalid_evidence', updated_at = now()"
                " WHERE id = %s",
                (shared_work["id"],),
            )
        if invalid_state == "impure-build":
            sibling_work = next(
                work
                for work in build["work"]
                if work["artifact_id"] == sibling["artifact_id"]
            )
            db.execute(
                "UPDATE lesson_knowledge_work"
                " SET status = 'failed', stage = 'blocks',"
                " failure_code = 'invalid_evidence', updated_at = now()"
                " WHERE id = %s",
                (sibling_work["id"],),
            )
        db.commit()

        detail = client.get(f"/api/syllabi/{first_route['syllabus_id']}")
        assert detail.status_code == 200, detail.text
        lessons = {lesson["id"]: lesson for lesson in detail.json()["lessons"]}
        assert "knowledge" not in lessons[second_lesson_id]["sources"][0]


def test_lesson_knowledge_http_rechecks_gate_and_enriches_syllabus_detail(
    test_database_url,
    applied_migrations,
    db,
):
    marker = "web-gate"
    route = _seed_route(db, marker=marker)
    publication = _seed_publication(db, marker=marker, suffix="source")
    reference_id = f"reference-lesson-kc-{marker}"
    _attach_reference(
        db,
        route=route,
        publication=publication,
        reference_id=reference_id,
        seq=1,
        validated=False,
    )
    db.commit()

    with _client(test_database_url) as client:
        detail = client.get(f"/api/syllabi/{route['syllabus_id']}")
        assert detail.status_code == 200, detail.text
        lesson = detail.json()["lessons"][0]
        assert lesson["knowledge"]["eligibility"]["code"] == (
            "references_not_validated"
        )
        assert "knowledge" not in lesson["sources"][0]

        blocked = client.post(
            f"{_url(route)}/knowledge-builds",
            json={"request_key": "must-not-spend"},
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "references_not_validated"

    assert db.execute(
        "SELECT count(*) FROM lesson_knowledge_build WHERE lesson_id = %s",
        (route["lesson_id"],),
    ).fetchone()[0] == 0


def test_knowledge_build_read_does_not_cross_its_owned_route(
    test_database_url,
    applied_migrations,
    db,
):
    marker = "web-owner"
    route = _seed_route(db, marker=marker)
    publication = _seed_publication(db, marker=marker, suffix="source")
    _attach_reference(
        db,
        route=route,
        publication=publication,
        reference_id=f"reference-lesson-kc-{marker}",
        seq=1,
    )
    db.commit()

    with _client(test_database_url) as client:
        started = client.post(
            f"{_url(route)}/knowledge-builds",
            json={"request_key": "owned"},
        )
        build_id = started.json()["id"]
        missing = client.get("/api/knowledge-builds/does-not-exist")
        assert missing.status_code == 404
        read = client.get(f"/api/knowledge-builds/{build_id}")
        assert read.status_code == 200
        assert read.json()["syllabus_id"] == route["syllabus_id"]


def test_syllabus_knowledge_http_checkpoint_seals_and_reads_one_exact_manifest(
    test_database_url,
    applied_migrations,
    db,
):
    from test_kc_pipeline_orchestration import seed_complete_single_task_source
    from test_syllabus_knowledge import _attach as attach_to_syllabus
    from test_syllabus_knowledge import _seed_route as seed_syllabus_route

    marker = "web-corpus"
    complete = seed_complete_single_task_source(db, marker)
    route = seed_syllabus_route(db, marker)
    attach_to_syllabus(
        db,
        route,
        source_id=complete["source_id"],
        lesson_seq=1,
        reference_seq=1,
    )
    db.commit()
    base = (
        f"/api/syllabi/{route['syllabus_id']}"
        f"/versions/{route['version_id']}"
    )

    with _client(test_database_url) as client:
        offered = client.get(f"{base}/knowledge")
        assert offered.status_code == 200, offered.text
        assert offered.json()["eligibility"]["code"] == "ready"
        assert offered.json()["complete_publication_count"] == 1
        assert offered.json()["latest_build"] is None

        started = client.post(
            f"{base}/knowledge-builds",
            json={"request_key": "publish-click-1"},
        )
        assert started.status_code == 202, started.text
        build = started.json()
        assert build["manifest"]["origin"] == {
            "kind": "syllabus-version",
            "syllabus_id": route["syllabus_id"],
            "version_id": route["version_id"],
        }
        assert build["manifest"]["publications"] == [
            {
                "source_id": complete["source_id"],
                "artifact_id": complete["artifact_id"],
            }
        ]

        replay = client.post(
            f"{base}/knowledge-builds",
            json={"request_key": "publish-click-1"},
        )
        assert replay.status_code == 202
        assert replay.json()["id"] == build["id"]
        read = client.get(f"{base}/knowledge-builds/{build['id']}")
        assert read.status_code == 200
        assert read.json() == replay.json()

        detail = client.get(f"/api/syllabi/{route['syllabus_id']}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["knowledge"]["latest_build"]["id"] == build["id"]
        assert "knowledge_manifest_id" not in detail.json()

        db.execute(
            "UPDATE syllabus_knowledge_build SET status = 'succeeded', stage = NULL"
            " WHERE id = %s",
            (build["id"],),
        )
        db.commit()
        current_detail = client.get(f"/api/syllabi/{route['syllabus_id']}").json()
        assert current_detail.get("knowledge_manifest_id") == build["manifest_id"], (
            current_detail["knowledge"]["eligibility"],
            current_detail["knowledge"]["latest_build"],
        )
        assert current_detail["knowledge"]["latest_build"]["current"] is True

        republish = client.post(
            f"{base}/knowledge-builds",
            json={"request_key": "publish-click-2"},
        )
        assert republish.status_code == 202, republish.text
        republish_build = republish.json()
        republishing_detail = client.get(
            f"/api/syllabi/{route['syllabus_id']}"
        ).json()
        assert republishing_detail["knowledge"]["latest_build"]["id"] == (
            republish_build["id"]
        )
        assert republishing_detail["knowledge"]["latest_build"]["status"] == (
            "queued"
        )
        assert republishing_detail["knowledge"]["published_build"]["id"] == (
            build["id"]
        )
        assert republishing_detail["knowledge_manifest_id"] == build["manifest_id"]

        replacement_snapshot = f"snapshot-{marker}-replacement"
        replacement_artifact = f"artifact-{marker}-replacement"
        db.execute(
            "INSERT INTO source_snapshot"
            " (id, source_id, content_hash, status, created_at)"
            " VALUES (%s, %s, 'replacement-hash', 'ok', now() + interval '1 day')",
            (replacement_snapshot, complete["source_id"]),
        )
        db.execute(
            "INSERT INTO artifact (id, snapshot_id, kind, tool, body, created_at)"
            " VALUES (%s, %s, 'markdown', 'test', '# Replacement',"
            " now() + interval '1 day')",
            (replacement_artifact, replacement_snapshot),
        )
        db.commit()

        stale_detail = client.get(f"/api/syllabi/{route['syllabus_id']}").json()
        assert "knowledge_manifest_id" not in stale_detail
        assert stale_detail["knowledge"]["latest_build"]["manifest_id"] == (
            republish_build["manifest_id"]
        )
        assert stale_detail["knowledge"]["latest_build"]["current"] is False
        assert stale_detail["knowledge"]["published_build"]["manifest_id"] == (
            build["manifest_id"]
        )
