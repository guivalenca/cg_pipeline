"""Syllabus Version checkpoint behavior for exact corpus-wide KC work."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier, Lock

import psycopg
import pytest
from psycopg.types.json import Jsonb

from universe import kc_pipeline, lesson_knowledge, syllabus_knowledge

from test_kc_pipeline_orchestration import (
    seed_complete_single_task_source,
    seed_source,
)


class _CountingConnection:
    """Postgres adapter used to keep page-read cost visible in behavior tests."""

    def __init__(self, connection):
        self._connection = connection
        self.query_count = 0

    def execute(self, *args, **kwargs):
        self.query_count += 1
        return self._connection.execute(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._connection, name)


def _seed_route(db, marker: str) -> dict[str, str]:
    route = {
        "syllabus_id": f"syllabus-corpus-{marker}",
        "version_id": f"version-corpus-{marker}",
    }
    db.execute(
        "INSERT INTO syllabus (id, title) VALUES (%s, 'Sistemas de Informacao')",
        (route["syllabus_id"],),
    )
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES (%s, %s, 7, 'upload')",
        (route["version_id"], route["syllabus_id"]),
    )
    return route


def _attach(
    db,
    route: dict[str, str],
    *,
    source_id: str | None,
    lesson_seq: int,
    reference_seq: int,
    hidden_lesson: bool = False,
    hidden_reference: bool = False,
    validated: bool = True,
) -> str:
    lesson_id = f"lesson-{route['version_id']}-{lesson_seq}"
    reference_id = (
        f"reference-{route['version_id']}-{lesson_seq}-{reference_seq}"
    )
    db.execute(
        "INSERT INTO syllabus_lesson"
        " (id, version_id, seq, kind, title, is_hidden)"
        " VALUES (%s, %s, %s, 'Encontro', %s, %s)"
        " ON CONFLICT (id) DO NOTHING",
        (
            lesson_id,
            route["version_id"],
            lesson_seq,
            f"Aula {lesson_seq}",
            hidden_lesson,
        ),
    )
    db.execute(
        "INSERT INTO syllabus_source_reference"
        " (id, version_id, lesson_id, seq, title, media_type, source_id, is_hidden)"
        " VALUES (%s, %s, %s, %s, %s, 'article', %s, %s)",
        (
            reference_id,
            route["version_id"],
            lesson_id,
            reference_seq,
            f"Autoestudo {reference_seq}",
            source_id,
            hidden_reference,
        ),
    )
    db.execute(
        "INSERT INTO syllabus_source_review (reference_id, is_validated)"
        " VALUES (%s, %s)",
        (reference_id, validated),
    )
    return reference_id


def _request_ready_build(db, marker: str) -> tuple[dict, dict[str, str], dict]:
    complete = seed_complete_single_task_source(db, marker)
    route = _seed_route(db, marker)
    _attach(
        db,
        route,
        source_id=complete["source_id"],
        lesson_seq=1,
        reference_seq=1,
    )
    build = syllabus_knowledge.request(
        db,
        route["syllabus_id"],
        route["version_id"],
        f"publish-{marker}",
        actor="founder",
    )
    return build, route, complete


def _shared_snapshot(
    manifest_id: str,
    *,
    completed: int,
    failed_stage: str | None = None,
) -> dict:
    stages = {}
    for index, stage in enumerate(kc_pipeline.SHARED_STAGES):
        status = "done" if index < completed else "pending"
        if stage == failed_stage:
            status = "failed"
        stages[stage] = {
            "status": status,
            "run_id": f"run-{stage}" if status in {"done", "failed"} else None,
        }
    next_stage = next(
        (stage for stage in kc_pipeline.SHARED_STAGES if stages[stage]["status"] != "done"),
        None,
    )
    return {
        "corpus": {"id": manifest_id},
        "status": "complete" if next_stage is None else "pending",
        "next_stage": next_stage,
        "stages": stages,
        "components": [],
        "relationships": [],
    }


def test_offer_is_read_only_and_request_rejects_incomplete_local_work(db):
    marker = f"offer-{uuid.uuid4().hex[:8]}"
    source_id, _ = seed_source(db, marker, blocks=False)
    route = _seed_route(db, marker)
    _attach(
        db,
        route,
        source_id=source_id,
        lesson_seq=1,
        reference_seq=1,
    )

    manifest_count = db.execute(
        "SELECT count(*) FROM kc_corpus_manifest"
    ).fetchone()[0]
    offered = syllabus_knowledge.offer(db, *route.values())

    assert offered["eligibility"]["eligible"] is False
    assert offered["eligibility"]["code"] == "local_kcs_incomplete"
    assert offered["eligibility"]["source_ids"] == [source_id]
    assert offered["publication_count"] == 1
    assert offered["complete_publication_count"] == 0
    assert offered["local_progress"][0]["total_stage_count"] == 11
    assert offered["latest_build"] is None
    assert db.execute(
        "SELECT count(*) FROM kc_corpus_manifest"
    ).fetchone()[0] == manifest_count
    with pytest.raises(
        syllabus_knowledge.SyllabusKnowledgeNotReady
    ) as caught:
        syllabus_knowledge.request(
            db,
            *route.values(),
            "must-not-seal",
            actor="founder",
        )
    assert caught.value.code == "local_kcs_incomplete"
    assert db.execute(
        "SELECT count(*) FROM kc_corpus_manifest"
    ).fetchone()[0] == manifest_count
    assert db.execute(
        "SELECT count(*) FROM syllabus_knowledge_build WHERE version_id = %s",
        (route["version_id"],),
    ).fetchone()[0] == 0


def test_offer_requires_every_active_reference_to_stay_validated(db):
    marker = f"validation-{uuid.uuid4().hex[:8]}"
    complete = seed_complete_single_task_source(db, marker)
    route = _seed_route(db, marker)
    reference_id = _attach(
        db,
        route,
        source_id=complete["source_id"],
        lesson_seq=1,
        reference_seq=1,
        validated=False,
    )

    offered = syllabus_knowledge.offer(db, *route.values())

    assert offered["eligibility"] == {
        "eligible": False,
        "code": "references_not_validated",
        "message": "every active source reference must be validated",
        "reference_ids": [reference_id],
        "source_ids": [],
    }
    assert offered["publication_count"] == 0
    with pytest.raises(syllabus_knowledge.SyllabusKnowledgeNotReady) as caught:
        syllabus_knowledge.request(
            db,
            *route.values(),
            "must-stay-curated",
            actor="founder",
        )
    assert caught.value.code == "references_not_validated"


def test_offer_summary_reads_twenty_complete_publications_with_bounded_queries(db):
    marker = f"summary-{uuid.uuid4().hex[:8]}"
    route = _seed_route(db, marker)
    for index in range(1, 21):
        complete = seed_complete_single_task_source(db, f"{marker}-{index}")
        _attach(
            db,
            route,
            source_id=complete["source_id"],
            lesson_seq=index,
            reference_seq=1,
        )
        lesson_id = f"lesson-{route['version_id']}-{index}"
        local = lesson_knowledge.request(
            db,
            route["syllabus_id"],
            route["version_id"],
            lesson_id,
            f"local-{index}",
            actor="founder",
        )
        db.execute(
            "UPDATE lesson_knowledge_work SET status = 'succeeded',"
            " stage = NULL, diagnostics = %s, updated_at = now()"
            " WHERE build_id = %s",
            (
                Jsonb(
                    {
                        "completed_stage_count": 11,
                        "total_stage_count": 11,
                        "kc_count": 1,
                    }
                ),
                local["id"],
            ),
        )

    build = syllabus_knowledge.request(
        db,
        *route.values(),
        "publish-summary",
        actor="founder",
    )
    deep = syllabus_knowledge.offer(db, *route.values())
    counted = _CountingConnection(db)

    summary = syllabus_knowledge.offer_summary(counted, *route.values())

    assert counted.query_count <= 6
    assert summary["active_reference_count"] == 20
    assert summary["publication_count"] == 20
    assert summary["complete_publication_count"] == 20
    assert summary["local_progress"] == deep["local_progress"]
    assert summary["eligibility"] == deep["eligibility"]
    assert summary["latest_build"]["id"] == build["id"]
    assert summary["latest_build"]["progress"] == deep["latest_build"]["progress"]
    assert "manifest" not in summary["latest_build"]
    assert "snapshot" not in summary["latest_build"]


def test_request_rechecks_the_ledger_even_when_summary_counters_claim_complete(db):
    marker = f"summary-gate-{uuid.uuid4().hex[:8]}"
    source_id, _ = seed_source(db, marker, blocks=False)
    route = _seed_route(db, marker)
    _attach(
        db,
        route,
        source_id=source_id,
        lesson_seq=1,
        reference_seq=1,
    )
    local = lesson_knowledge.request(
        db,
        route["syllabus_id"],
        route["version_id"],
        f"lesson-{route['version_id']}-1",
        "untrusted-summary",
        actor="founder",
    )
    db.execute(
        "UPDATE lesson_knowledge_work SET status = 'succeeded',"
        " stage = 'local-complete', diagnostics = %s WHERE build_id = %s",
        (
            Jsonb(
                {
                    "completed_stage_count": 11,
                    "total_stage_count": 11,
                    "kc_count": 1,
                }
            ),
            local["id"],
        ),
    )

    manifest_count = db.execute(
        "SELECT count(*) FROM kc_corpus_manifest"
    ).fetchone()[0]
    summary = syllabus_knowledge.offer_summary(db, *route.values())

    assert summary["eligibility"]["code"] == "ready"
    with pytest.raises(syllabus_knowledge.SyllabusKnowledgeNotReady) as caught:
        syllabus_knowledge.request(
            db,
            *route.values(),
            "must-recheck-ledger",
            actor="founder",
        )
    assert caught.value.code == "local_kcs_incomplete"
    assert db.execute(
        "SELECT count(*) FROM kc_corpus_manifest"
    ).fetchone()[0] == manifest_count


def test_request_seals_every_active_publication_once_and_replays_exactly(db):
    marker = f"seal-{uuid.uuid4().hex[:8]}"
    complete_b = seed_complete_single_task_source(db, f"{marker}-b")
    complete_a = seed_complete_single_task_source(db, f"{marker}-a")
    hidden_source, _ = seed_source(db, f"{marker}-hidden", blocks=False)
    route = _seed_route(db, marker)
    _attach(
        db,
        route,
        source_id=complete_b["source_id"],
        lesson_seq=2,
        reference_seq=1,
    )
    _attach(
        db,
        route,
        source_id=complete_a["source_id"],
        lesson_seq=1,
        reference_seq=1,
    )
    # Duplicate active references pin the reference set, not duplicate corpus work.
    _attach(
        db,
        route,
        source_id=complete_a["source_id"],
        lesson_seq=1,
        reference_seq=2,
    )
    _attach(
        db,
        route,
        source_id=hidden_source,
        lesson_seq=3,
        reference_seq=1,
        hidden_lesson=True,
    )

    created = syllabus_knowledge.request(
        db,
        *route.values(),
        "publish-v7",
        actor="founder",
    )
    replayed = syllabus_knowledge.request(
        db,
        *route.values(),
        "publish-v7",
        actor="someone-else",
    )

    assert replayed == created
    assert created["requested_by"] == "founder"
    assert created["status"] == "queued"
    assert created["stage"] is None
    assert created["progress"] == {
        "total": 4,
        "completed": 0,
        "pending": 4,
        "partial": 0,
        "running": 0,
        "failed": 0,
    }
    assert created["manifest"]["publications"] == sorted(
        [
            {
                "source_id": complete_a["source_id"],
                "artifact_id": complete_a["artifact_id"],
            },
            {
                "source_id": complete_b["source_id"],
                "artifact_id": complete_b["artifact_id"],
            },
        ],
        key=lambda item: (item["source_id"], item["artifact_id"]),
    )
    assert created["manifest"]["origin"] == {
        "kind": "syllabus-version",
        "syllabus_id": route["syllabus_id"],
        "version_id": route["version_id"],
    }
    assert syllabus_knowledge.read(
        db, *route.values(), created["id"]
    ) == created
    assert syllabus_knowledge.latest(db, *route.values()) == created
    offered = syllabus_knowledge.offer(db, *route.values())
    assert offered["active_reference_count"] == 3
    assert offered["publication_count"] == 2
    assert offered["complete_publication_count"] == 2
    assert offered["latest_build"] == created
    assert db.execute(
        "SELECT count(*) FROM syllabus_knowledge_build"
        " WHERE version_id = %s AND request_key = 'publish-v7'",
        (route["version_id"],),
    ).fetchone()[0] == 1


def test_pinned_manifest_remains_readable_after_a_source_is_superseded(db):
    marker = f"history-{uuid.uuid4().hex[:8]}"
    build, route, complete = _request_ready_build(db, marker)
    assert build["current"] is True
    replacement_snapshot = f"snapshot-{marker}-replacement"
    replacement_artifact = f"artifact-{marker}-replacement"
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, 'replacement-hash', 'ok',"
        " now() + interval '2 seconds')",
        (replacement_snapshot, complete["source_id"]),
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, created_at)"
        " VALUES (%s, %s, 'markdown', 'test', '# Replacement',"
        " now() + interval '2 seconds')",
        (replacement_artifact, replacement_snapshot),
    )
    db.commit()

    historical = syllabus_knowledge.read(db, *route.values(), build["id"])
    offered = syllabus_knowledge.offer(db, *route.values())

    assert historical is not None
    assert historical["current"] is False
    assert historical["manifest_id"] == build["manifest_id"]
    assert historical["manifest"]["publications"] == [
        {
            "source_id": complete["source_id"],
            "artifact_id": complete["artifact_id"],
        }
    ]
    assert historical["snapshot"]["corpus"]["id"] == build["manifest_id"]
    assert offered["eligibility"]["code"] == "local_kcs_incomplete"
    assert offered["latest_build"]["manifest_id"] == build["manifest_id"]
    assert offered["latest_build"]["current"] is False


def test_offer_keeps_the_last_published_build_when_a_new_attempt_is_not_successful(db):
    marker = f"published-{uuid.uuid4().hex[:8]}"
    published, route, _ = _request_ready_build(db, marker)
    db.execute(
        "UPDATE syllabus_knowledge_build SET status = 'succeeded', stage = NULL"
        " WHERE id = %s",
        (published["id"],),
    )
    newer_published = syllabus_knowledge.request(
        db,
        *route.values(),
        "newer-publish-after-success",
        actor="founder",
    )
    db.execute(
        "UPDATE syllabus_knowledge_build SET status = 'succeeded', stage = NULL"
        " WHERE id = %s",
        (newer_published["id"],),
    )
    latest = syllabus_knowledge.request(
        db,
        *route.values(),
        "latest-republish-attempt",
        actor="founder",
    )

    queued = syllabus_knowledge.offer(db, *route.values())

    assert queued["latest_build"]["id"] == latest["id"]
    assert queued["latest_build"]["status"] == "queued"
    assert queued["published_build"]["id"] == newer_published["id"]
    assert queued["published_build"]["status"] == "succeeded"
    queued_summary = syllabus_knowledge.offer_summary(db, *route.values())
    assert queued_summary["latest_build"]["id"] == latest["id"]
    assert queued_summary["published_build"]["id"] == newer_published["id"]

    db.execute(
        "UPDATE syllabus_knowledge_build SET status = 'failed', stage = NULL,"
        " failure_code = 'provider_failed' WHERE id = %s",
        (latest["id"],),
    )
    failed = syllabus_knowledge.offer(db, *route.values())

    assert failed["latest_build"]["id"] == latest["id"]
    assert failed["latest_build"]["status"] == "failed"
    assert failed["published_build"]["id"] == newer_published["id"]


def test_build_cannot_be_read_through_another_syllabus_version(db):
    marker = f"ownership-{uuid.uuid4().hex[:8]}"
    build, _, _ = _request_ready_build(db, marker)
    other = _seed_route(db, f"{marker}-other")

    assert syllabus_knowledge.read(
        db, *other.values(), build["id"]
    ) is None


@dataclass
class _FakeProcess:
    pid: int = 4242


def test_process_next_claims_one_build_and_launches_one_exact_shared_stage(db):
    marker = f"launch-{uuid.uuid4().hex[:8]}"
    build, route, _ = _request_ready_build(db, marker)
    launched = []

    def spawn(argv, lease):
        launched.append((argv, lease))
        return _FakeProcess()

    result = syllabus_knowledge.process_next(
        db, build_id=build["id"], spawn=spawn
    )

    assert result == {
        "action": "launched",
        "build_id": build["id"],
        "manifest_id": build["manifest_id"],
        "status": "running",
        "stage": "task-embedding",
        "pid": 4242,
        "claim_count": 1,
    }
    assert len(launched) == 1
    assert launched[0][0][1:4] == ["-m", "universe.task_embedding", "run"]
    assert launched[0][1].scope_key == f"corpus:{build['manifest_id']}"
    durable = syllabus_knowledge.read(db, *route.values(), build["id"])
    assert durable is not None
    assert durable["status"] == "running"
    assert durable["stage"] == "task-embedding"
    assert durable["last_launched_stage"] == "task-embedding"
    assert durable["diagnostics"]["last_action"] == "launched"


def test_process_next_marks_complete_and_failed_snapshots_durably(
    db, monkeypatch
):
    complete_marker = f"complete-{uuid.uuid4().hex[:8]}"
    completed, complete_route, _ = _request_ready_build(db, complete_marker)
    monkeypatch.setattr(
        syllabus_knowledge,
        "_snapshot",
        lambda _conn, manifest_id: _shared_snapshot(manifest_id, completed=4),
    )

    done = syllabus_knowledge.process_next(db, build_id=completed["id"])

    assert done["action"] == "completed"
    durable_done = syllabus_knowledge.read(
        db, *complete_route.values(), completed["id"]
    )
    assert durable_done["status"] == "succeeded"
    assert durable_done["progress"]["completed"] == 4
    assert durable_done["diagnostics"]["shared_stage_count"] == 4

    failed_marker = f"failed-{uuid.uuid4().hex[:8]}"
    failed, failed_route, _ = _request_ready_build(db, failed_marker)
    monkeypatch.setattr(
        syllabus_knowledge,
        "_snapshot",
        lambda _conn, manifest_id: _shared_snapshot(
            manifest_id, completed=0, failed_stage="task-embedding"
        ),
    )
    launched = []

    attention = syllabus_knowledge.process_next(
        db,
        build_id=failed["id"],
        spawn=lambda *args: launched.append(args),
    )

    assert attention["action"] == "attention"
    assert launched == []
    durable_failed = syllabus_knowledge.read(
        db, *failed_route.values(), failed["id"]
    )
    assert durable_failed["status"] == "failed"
    assert durable_failed["failure_code"] == "pipeline_stage_failed"
    assert durable_failed["diagnostics"]["pipeline_run_id"] == (
        "run-task-embedding"
    )


def test_a_finished_launch_without_result_requires_a_new_explicit_request(
    db, monkeypatch
):
    marker = f"no-retry-{uuid.uuid4().hex[:8]}"
    build, route, _ = _request_ready_build(db, marker)
    db.execute(
        "UPDATE syllabus_knowledge_build"
        " SET status = 'running', stage = 'task-embedding',"
        " last_launched_stage = 'task-embedding', available_at = now()"
        " WHERE id = %s",
        (build["id"],),
    )
    db.commit()
    monkeypatch.setattr(
        syllabus_knowledge,
        "_snapshot",
        lambda _conn, manifest_id: _shared_snapshot(manifest_id, completed=0),
    )

    result = syllabus_knowledge.process_next(
        db,
        build_id=build["id"],
        spawn=lambda *_: pytest.fail("must not retry implicitly"),
    )

    assert result["action"] == "attention"
    durable = syllabus_knowledge.read(db, *route.values(), build["id"])
    assert durable["failure_code"] == "stage_ended_without_result"
    assert "new explicit request" in durable["diagnostics"]["message"]


def test_two_workers_claim_one_build_and_spawn_only_once(
    db, test_database_url, monkeypatch
):
    marker = f"race-{uuid.uuid4().hex[:8]}"
    db.execute(
        "UPDATE syllabus_knowledge_build SET available_at = now() + interval '1 day'"
        " WHERE status IN ('queued', 'running')"
    )
    db.commit()
    build, _, _ = _request_ready_build(db, marker)
    db.commit()
    barrier = Barrier(2)
    lock = Lock()
    launched = []
    original_claim = syllabus_knowledge._claim_next

    def synchronized_claim(conn, **kwargs):
        barrier.wait(timeout=5)
        return original_claim(conn, **kwargs)

    def spawn(_argv, lease):
        with lock:
            launched.append(lease.token)
        return _FakeProcess()

    monkeypatch.setattr(syllabus_knowledge, "_claim_next", synchronized_claim)

    def attempt():
        with psycopg.connect(test_database_url) as conn:
            return syllabus_knowledge.process_next(
                conn, build_id=build["id"], spawn=spawn
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))

    assert len(launched) == 1
    assert sum(result is None for result in results) == 1
    assert sum(
        result is not None and result["action"] == "launched"
        for result in results
    ) == 1
