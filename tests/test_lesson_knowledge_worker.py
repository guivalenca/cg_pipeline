"""Operational behavior of the lesson-local KC build worker."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier

import pytest
import psycopg

from universe import lesson_knowledge
from universe.lesson_knowledge_worker import process_next, sync_build

from test_kc_pipeline_orchestration import (
    seed_cuts_done,
    seed_complete_single_task_source,
    seed_run,
    seed_source,
)


def _request_build(db, *, source_id: str, tag: str) -> tuple[dict, dict[str, str]]:
    marker = f"{tag}-{uuid.uuid4().hex[:10]}"
    route = {
        "syllabus_id": f"syllabus-lesson-worker-{marker}",
        "version_id": f"version-lesson-worker-{marker}",
        "lesson_id": f"lesson-worker-{marker}",
    }
    reference_id = f"reference-lesson-worker-{marker}"
    db.execute(
        "INSERT INTO syllabus (id, title) VALUES (%s, 'Sistemas de Informacao')",
        (route["syllabus_id"],),
    )
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES (%s, %s, 1, 'upload')",
        (route["version_id"], route["syllabus_id"]),
    )
    db.execute(
        "INSERT INTO syllabus_lesson"
        " (id, version_id, seq, kind, title)"
        " VALUES (%s, %s, 1, 'Encontro', 'Aula operacional')",
        (route["lesson_id"], route["version_id"]),
    )
    db.execute(
        "INSERT INTO syllabus_source_reference"
        " (id, version_id, lesson_id, seq, title, media_type, source_id)"
        " VALUES (%s, %s, %s, 1, 'Autoestudo', 'article', %s)",
        (reference_id, route["version_id"], route["lesson_id"], source_id),
    )
    db.execute(
        "INSERT INTO syllabus_source_review (reference_id, is_validated)"
        " VALUES (%s, true)",
        (reference_id,),
    )
    build = lesson_knowledge.request(
        db,
        route["syllabus_id"],
        route["version_id"],
        route["lesson_id"],
        f"request-{marker}",
        actor="founder",
    )
    db.execute(
        "UPDATE lesson_knowledge_work"
        " SET available_at = now() - interval '1 day' WHERE build_id = %s",
        (build["id"],),
    )
    db.commit()
    return build, route


@dataclass
class _FakeProcess:
    pid: int = 4242


def test_process_next_claims_one_work_and_launches_exactly_one_local_stage(db):
    tag = f"lesson_worker_launch_{uuid.uuid4().hex[:8]}"
    source_id, artifact_id = seed_source(db, tag, blocks=False)
    build, route = _request_build(db, source_id=source_id, tag=tag)
    launched: list[tuple[list[str], object]] = []

    def spawn(argv, lease):
        launched.append((argv, lease))
        return _FakeProcess()

    result = process_next(db, spawn=spawn)

    assert result is not None
    assert result["action"] == "launched"
    assert result["build_id"] == build["id"]
    assert result["work_id"] == build["work"][0]["id"]
    assert result["source_id"] == source_id
    assert result["artifact_id"] == artifact_id
    assert result["status"] == "running"
    assert result["stage"] == "blocks"
    assert result["pid"] == 4242
    assert len(launched) == 1
    assert launched[0][0][-2:] == ["universe.blocks", artifact_id]
    assert launched[0][1].scope_key == f"source:{source_id}"

    durable = lesson_knowledge.read(db, *route.values(), build["id"])
    assert durable is not None
    assert durable["status"] == "running"
    assert durable["work"][0]["status"] == "running"
    assert durable["work"][0]["stage"] == "blocks"
    assert durable["work"][0]["diagnostics"]["last_action"] == "launched"


def test_process_next_observes_a_live_stage_without_launching_it_again(db):
    tag = f"lesson_worker_observe_{uuid.uuid4().hex[:8]}"
    source_id, _ = seed_source(db, tag, blocks=False)
    build, _ = _request_build(db, source_id=source_id, tag=tag)
    launched = []

    def spawn(argv, lease):
        launched.append((argv, lease))
        return _FakeProcess()

    first = process_next(db, build_id=build["id"], spawn=spawn)
    assert first is not None
    assert first["action"] == "launched"
    db.execute(
        "UPDATE lesson_knowledge_work SET available_at = now() - interval '1 second'"
        " WHERE id = %s",
        (build["work"][0]["id"],),
    )
    db.commit()

    observed = process_next(db, build_id=build["id"], spawn=spawn)

    assert observed is not None
    assert observed["action"] == "observed"
    assert observed["work_id"] == build["work"][0]["id"]
    assert observed["status"] == "running"
    assert observed["stage"] == "blocks"
    assert len(launched) == 1


def test_sync_build_marks_work_succeeded_only_after_all_eleven_local_stages(db):
    tag = f"lesson_worker_complete_{uuid.uuid4().hex[:8]}"
    complete = seed_complete_single_task_source(db, tag)
    build, _ = _request_build(db, source_id=complete["source_id"], tag=tag)

    synced = sync_build(db, build["id"])

    assert synced["status"] == "succeeded"
    assert synced["progress"] == {
        "total": 1,
        "queued": 0,
        "running": 0,
        "succeeded": 1,
        "failed": 0,
    }
    assert synced["work"][0]["status"] == "succeeded"
    assert synced["work"][0]["stage"] is None
    assert synced["work"][0]["diagnostics"]["last_action"] == "completed"
    assert synced["work"][0]["diagnostics"]["local_stage_count"] == 11


def test_process_next_marks_a_superseded_publication_as_explicit_attention(db):
    tag = f"lesson_worker_stale_{uuid.uuid4().hex[:8]}"
    source_id, _ = seed_source(db, tag, blocks=False)
    build, route = _request_build(db, source_id=source_id, tag=tag)
    new_snapshot = f"snapshot-{tag}-new"
    new_artifact = f"artifact-{tag}-new"
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, 'new-hash', 'ok', now() + interval '1 second')",
        (new_snapshot, source_id),
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, created_at)"
        " VALUES (%s, %s, 'markdown', 'test', '# New',"
        " now() + interval '1 second')",
        (new_artifact, new_snapshot),
    )
    db.commit()
    launched = []

    result = process_next(
        db,
        spawn=lambda argv, lease: launched.append((argv, lease)),
    )

    assert result is not None
    assert result["action"] == "attention"
    assert result["status"] == "failed"
    assert result["stage"] == "blocks"
    assert launched == []
    durable = lesson_knowledge.read(db, *route.values(), build["id"])
    assert durable is not None
    assert durable["status"] == "failed"
    assert durable["work"][0]["failure_code"] == "publication_stale"
    assert durable["work"][0]["diagnostics"] == {
        "category": "attention",
        "exception": "StepNotRunnable",
        "last_action": "attention",
        "message": "the pinned Source Publication is no longer current",
        "pipeline_stage": "blocks",
    }


def test_process_next_surfaces_a_durable_failed_stage_without_paid_retry(
    db, monkeypatch
):
    from universe import kc_pipeline

    tag = f"lesson_worker_failed_{uuid.uuid4().hex[:8]}"
    source_id, _ = seed_source(db, tag, blocks=False)
    build, route = _request_build(db, source_id=source_id, tag=tag)
    snapshot = kc_pipeline.read_snapshot(db, source_id)
    snapshot["stages"]["blocks"] = {
        **snapshot["stages"]["blocks"],
        "status": "failed",
        "run_id": f"run-{tag}-failed",
    }
    db.execute(
        "UPDATE lesson_knowledge_work SET last_launched_stage = 'blocks'"
        " WHERE build_id = %s",
        (build["id"],),
    )
    db.commit()
    monkeypatch.setattr(kc_pipeline, "read_snapshot", lambda *_args, **_kwargs: snapshot)
    launched = []

    result = process_next(
        db,
        spawn=lambda argv, lease: launched.append((argv, lease)),
    )

    assert result is not None
    assert result["action"] == "attention"
    assert result["status"] == "failed"
    assert result["stage"] == "blocks"
    assert launched == []
    durable = lesson_knowledge.read(db, *route.values(), build["id"])
    assert durable is not None
    assert durable["work"][0]["failure_code"] == "pipeline_stage_failed"
    assert durable["work"][0]["diagnostics"]["pipeline_run_id"] == (
        f"run-{tag}-failed"
    )
    assert durable["work"][0]["diagnostics"]["pipeline_stage_status"] == "failed"


def test_a_new_explicit_build_authorizes_retry_of_a_previous_stage_failure(
    db, monkeypatch
):
    from universe import kc_pipeline

    tag = f"lesson_worker_retry_{uuid.uuid4().hex[:8]}"
    source_id, _ = seed_source(db, tag, blocks=False)
    first, route = _request_build(db, source_id=source_id, tag=tag)
    db.execute(
        "UPDATE lesson_knowledge_work SET status = 'failed', stage = 'blocks',"
        " failure_code = 'pipeline_stage_failed', last_launched_stage = 'blocks'"
        " WHERE build_id = %s",
        (first["id"],),
    )
    second = lesson_knowledge.request(
        db,
        *route.values(),
        f"retry-{tag}",
        actor="founder",
    )
    snapshot = kc_pipeline.read_snapshot(db, source_id)
    snapshot["next_stage"] = "blocks"
    snapshot["stages"]["blocks"] = {
        **snapshot["stages"]["blocks"],
        "status": "failed",
        "run_id": f"run-{tag}-failed",
    }
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status, finished_at)"
        " VALUES (%s, 'blocks', 'test', 'test', 'sha', 'failed', now())",
        (f"run-{tag}-failed",),
    )
    db.execute(
        "UPDATE lesson_knowledge_build SET created_at = now() + interval '1 second'"
        " WHERE id = %s",
        (second["id"],),
    )
    db.commit()
    monkeypatch.setattr(kc_pipeline, "read_snapshot", lambda *_args, **_kwargs: snapshot)
    launched = []
    monkeypatch.setattr(
        kc_pipeline,
        "advance",
        lambda *_args, **_kwargs: launched.append(True)
        or {"lease_token": "retry-lease", "pid": 9191},
    )

    result = process_next(db, build_id=second["id"])

    assert result is not None
    assert result["build_id"] == second["id"]
    assert result["action"] == "launched"
    assert result["stage"] == "blocks"
    assert launched == [True]
    durable = lesson_knowledge.read(db, *route.values(), second["id"])
    assert durable is not None
    assert durable["status"] == "running"
    assert durable["work"][0]["last_launched_stage"] == "blocks"


@pytest.mark.parametrize("run_status", ["done", "failed"])
def test_retry_requires_a_new_build_after_a_real_terminal_model_attempt(
    db, run_status
):
    tag = f"lesson_worker_real_retry_{run_status}_{uuid.uuid4().hex[:8]}"
    source_id, artifact_id = seed_source(db, tag)
    seed_cuts_done(db, tag, artifact_id)
    first, route = _request_build(db, source_id=source_id, tag=tag)
    passage_id = f"pass_kcpipe_{tag}"
    run_id = f"run-{tag}-triage"
    seed_run(
        db,
        run_id,
        "passage-triage",
        artifact_id,
        status=run_status,
        items=[{"passage_id": passage_id, "error": "provider failed"}],
        params={
            "pipeline_lease": {
                "scope_key": f"source:{source_id}",
                "stage": "passage-triage",
                "token": f"token-{tag}",
                "owner_id": "test",
            }
        },
    )
    db.execute(
        "UPDATE run SET finished_at = now() - interval '1 second' WHERE id = %s",
        (run_id,),
    )
    db.execute(
        "UPDATE lesson_knowledge_work"
        " SET last_launched_stage = 'passage-triage' WHERE build_id = %s",
        (first["id"],),
    )
    db.commit()

    same_attempt = process_next(db, build_id=first["id"])

    assert same_attempt is not None
    assert same_attempt["action"] == "attention"
    second = lesson_knowledge.request(
        db,
        *route.values(),
        f"explicit-retry-{tag}",
        actor="founder",
    )
    launched = []

    retried = process_next(
        db,
        build_id=second["id"],
        spawn=lambda argv, lease: launched.append((argv, lease)) or _FakeProcess(7373),
    )

    assert retried is not None
    assert retried["action"] == "launched"
    assert retried["stage"] == "passage-triage"
    assert len(launched) == 1


def test_process_next_marks_a_non_runnable_stage_as_attention(db, monkeypatch):
    from universe import kc_pipeline

    tag = f"lesson_worker_not_runnable_{uuid.uuid4().hex[:8]}"
    source_id, _ = seed_source(db, tag, blocks=False)
    build, route = _request_build(db, source_id=source_id, tag=tag)
    original = kc_pipeline.next_step

    def not_runnable(conn, target):
        step = original(conn, target)
        return {
            **step,
            "runnable": False,
            "reason": "required input has no completed current run",
        }

    monkeypatch.setattr(kc_pipeline, "next_step", not_runnable)

    result = process_next(db, spawn=lambda *_: pytest.fail("must not spawn"))

    assert result is not None
    assert result["action"] == "attention"
    durable = lesson_knowledge.read(db, *route.values(), build["id"])
    assert durable is not None
    assert durable["work"][0]["failure_code"] == "stage_not_runnable"
    assert durable["work"][0]["diagnostics"]["message"] == (
        "required input has no completed current run"
    )


def test_two_workers_claim_one_work_and_spawn_once(
    db, test_database_url, monkeypatch
):
    from universe import lesson_knowledge_worker

    tag = f"lesson_worker_race_{uuid.uuid4().hex[:8]}"
    db.execute(
        "UPDATE lesson_knowledge_work SET available_at = now() + interval '1 day'"
        " WHERE status IN ('queued', 'running')"
    )
    db.commit()
    source_id, _ = seed_source(db, tag, blocks=False)
    _request_build(db, source_id=source_id, tag=tag)
    barrier = Barrier(2)
    original_claim = lesson_knowledge_worker._claim_next
    launched = []

    def synchronized_claim(conn, **kwargs):
        barrier.wait(timeout=5)
        return original_claim(conn, **kwargs)

    def spawn(_argv, lease):
        launched.append(lease.token)
        return _FakeProcess()

    monkeypatch.setattr(lesson_knowledge_worker, "_claim_next", synchronized_claim)

    def attempt():
        with psycopg.connect(test_database_url) as conn:
            return process_next(conn, spawn=spawn)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))

    assert len(launched) == 1
    assert sum(result is None for result in results) == 1
    assert sum(
        result is not None and result["action"] == "launched"
        for result in results
    ) == 1


def test_expired_work_claim_is_recovered_with_a_new_token(db):
    from universe import lesson_knowledge_worker

    tag = f"lesson_worker_reclaim_{uuid.uuid4().hex[:8]}"
    source_id, _ = seed_source(db, tag, blocks=False)
    build, _ = _request_build(db, source_id=source_id, tag=tag)
    first = lesson_knowledge_worker._claim_next(db)
    assert first is not None
    db.execute(
        "UPDATE lesson_knowledge_work SET"
        " claimed_at = now() - interval '10 minutes',"
        " lease_expires_at = now() - interval '1 second'"
        " WHERE id = %s",
        (first["id"],),
    )
    db.commit()

    successor = lesson_knowledge_worker._claim_next(db)

    assert successor is not None
    assert successor["id"] == build["work"][0]["id"]
    assert successor["claim_token"] != first["claim_token"]
    assert successor["claim_count"] == 2
    assert lesson_knowledge_worker._finish_claim(
        db,
        first,
        status="failed",
        stage="blocks",
        failure_code="stale_worker",
        diagnostics={"category": "must-not-publish"},
    ) is False
