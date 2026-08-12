"""The Markdown-to-KC Module is the caller and test seam."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import multiprocessing
from threading import Barrier

import psycopg
import pytest
from psycopg.types.json import Jsonb

from universe import kc_pipeline


def _lease_process(url, start, results):
    """Independent scheduler process used by the Postgres lease regression."""
    from universe import kc_pipeline as pipeline

    start.wait()
    with psycopg.connect(url) as conn:
        lease = pipeline._acquire_lease(
            conn,
            scope_key="source:cross-process",
            stage="blocks",
            owner_id=f"process-{multiprocessing.current_process().pid}",
        )
    results.put(lease is not None)


def seed_publication(
    db,
    tag: str,
    *,
    body: str = "# Stable title\n\nA durable explanation.",
    source_id: str | None = None,
    version: str = "v1",
) -> kc_pipeline.SourcePublicationTarget:
    source_id = source_id or f"kcpipe-{tag}"
    snapshot_id = f"{source_id}:snapshot:{version}"
    artifact_id = f"{snapshot_id}:markdown"
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, %s, 'article') ON CONFLICT (id) DO NOTHING",
        (
            source_id,
            Jsonb({"kind": "test", "value": source_id}),
            f"KC pipeline test {tag}",
        ),
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, %s, 'ok', now())",
        (snapshot_id, source_id, content_hash),
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, tool_version, body, metadata)"
        " VALUES (%s, %s, 'markdown', 'legacy-import', 'test', %s, %s)",
        (artifact_id, snapshot_id, body, Jsonb({"capture_id": tag})),
    )
    db.commit()
    return kc_pipeline.SourcePublicationTarget(source_id, artifact_id)


def test_current_target_reuses_the_existing_source_publication_without_writes(db):
    target = seed_publication(db, "existing-ledger")
    before = db.execute(
        "SELECT (SELECT count(*) FROM source),"
        " (SELECT count(*) FROM source_snapshot),"
        " (SELECT count(*) FROM artifact)"
    ).fetchone()

    repeated = kc_pipeline.current_target(db, target.source_id)
    after = db.execute(
        "SELECT (SELECT count(*) FROM source),"
        " (SELECT count(*) FROM source_snapshot),"
        " (SELECT count(*) FROM artifact)"
    ).fetchone()

    assert repeated == target
    assert after == before


def test_publication_target_and_read_need_no_provider(db):
    target = seed_publication(
        db, "readable", body="## One idea\n\nThe source body."
    )

    snapshot = kc_pipeline.read_snapshot(db, target)

    assert snapshot["source"] == {
        "id": target.source_id,
        "title": "KC pipeline test readable",
        "artifact_id": target.artifact_id,
        "content_sha256": hashlib.sha256(
            "## One idea\n\nThe source body.".encode()
        ).hexdigest(),
        "provenance": {"capture_id": "readable"},
    }
    assert snapshot["status"] == "pending"
    assert snapshot["next_stage"] == "blocks"
    assert snapshot["grouping_id"] is None
    assert snapshot["components"] == []
    assert snapshot["relationships"] == []


def test_pinned_target_is_rejected_after_a_new_publication_becomes_current(db):
    source_id = "kcpipe-new-snapshot"
    first = seed_publication(
        db, "old", source_id=source_id, version="v1", body="# Version one"
    )
    second = seed_publication(
        db, "new", source_id=source_id, version="v2", body="# Version two"
    )

    assert kc_pipeline.current_target(db, source_id) == second
    with pytest.raises(kc_pipeline.StepNotRunnable, match="no longer current"):
        kc_pipeline.read_snapshot(db, first)


@dataclass
class _FakeProcess:
    pid: int = 4242


def test_advance_launches_exactly_one_planned_stage(db):
    target = seed_publication(db, "advance", body="# First\n\nSecond.")
    launched: list[list[str]] = []

    def spawn(argv: list[str], _lease):
        launched.append(argv)
        return _FakeProcess()

    result = kc_pipeline.advance(db, target, spawn=spawn)

    assert result["status"] == "launched"
    assert result["stage"] == "blocks"
    assert result["pid"] == 4242
    assert len(launched) == 1
    assert launched[0][-2:] == ["universe.blocks", target.artifact_id]


def test_advance_refuses_a_duplicate_in_flight_stage(db):
    target = seed_publication(
        db, "one-launch", body="# Only once\n\nOne in-flight stage per source."
    )
    launched: list[list[str]] = []

    def spawn(argv: list[str], _lease):
        launched.append(argv)
        return _FakeProcess()

    kc_pipeline.advance(db, target, spawn=spawn)

    with pytest.raises(kc_pipeline.StepAlreadyRunning, match="already running"):
        kc_pipeline.advance(db, target, spawn=spawn)
    assert len(launched) == 1


def test_two_concurrent_advance_calls_launch_the_stage_once(
    db, test_database_url, monkeypatch
):
    target = seed_publication(
        db,
        "advance-race",
        body="# One claim\n\nTwo independent schedulers.",
    )
    db.commit()
    barrier = Barrier(2)
    acquire = kc_pipeline._acquire_lease
    launched: list[str] = []

    def synchronized_acquire(conn, **kwargs):
        barrier.wait(timeout=5)
        return acquire(conn, **kwargs)

    def spawn(_argv, lease):
        launched.append(lease.token)
        return _FakeProcess()

    monkeypatch.setattr(kc_pipeline, "_acquire_lease", synchronized_acquire)

    def attempt():
        with psycopg.connect(test_database_url) as conn:
            try:
                return kc_pipeline.advance(
                    conn, target, spawn=spawn
                )
            except kc_pipeline.StepAlreadyRunning as exc:
                return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))

    assert len(launched) == 1
    assert sum(isinstance(item, dict) for item in results) == 1
    assert sum(
        isinstance(item, kc_pipeline.StepAlreadyRunning) for item in results
    ) == 1


def test_postgres_lease_is_atomic_across_scheduler_processes(
    db, test_database_url
):
    db.execute(
        "DELETE FROM kc_pipeline_lease"
        " WHERE scope_key = 'source:cross-process' AND stage = 'blocks'"
    )
    db.commit()
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    results = context.Queue()
    processes = [
        context.Process(
            target=_lease_process,
            args=(test_database_url, start, results),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    start.set()
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0

    assert sorted(results.get(timeout=2) for _ in processes) == [False, True]


def test_expired_lease_is_recoverable_and_old_token_is_fenced(db):
    first = kc_pipeline._acquire_lease(
        db,
        scope_key="source:orphan",
        stage="blocks",
        owner_id="dead-owner",
    )
    assert first is not None
    db.execute(
        "UPDATE kc_pipeline_lease SET"
        " heartbeat_at = now() - interval '10 minutes',"
        " expires_at = now() - interval '1 second'"
        " WHERE scope_key = %s AND stage = %s",
        (first.scope_key, first.stage),
    )
    db.commit()

    successor = kc_pipeline._acquire_lease(
        db,
        scope_key=first.scope_key,
        stage=first.stage,
        owner_id="recovery-owner",
    )

    assert successor is not None
    assert successor.token != first.token
    assert kc_pipeline._heartbeat_lease(db, first) is False
    assert kc_pipeline._release_lease(db, first) is False
    assert kc_pipeline._heartbeat_lease(db, successor) is True


def test_current_target_rejects_a_source_without_a_publication(db):
    source_id = "kcpipe-empty"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'No publication', 'article')",
        (source_id, Jsonb({"kind": "test", "value": source_id})),
    )
    db.commit()

    with pytest.raises(LookupError, match="no Source Publication"):
        kc_pipeline.current_target(db, source_id)
