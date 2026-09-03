"""Passage-cut runs publish deterministic rows atomically with completion."""

import threading
import time

import psycopg
import pytest

from universe import blocks, harness, producer_publication


class FakeClient:
    model = "fake/atomic-producer"
    params = {}

    def __init__(self, response: str):
        self.response = response

    def complete(self, _prompt):
        return self.response, {}, 1


def _seed_context(conn, tag: str) -> dict:
    source_id = f"producer-{tag}-source"
    snapshot_id = f"producer-{tag}-snapshot"
    artifact_id = f"producer-{tag}-artifact"
    conn.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{}'::jsonb, %s, 'article')",
        (source_id, f"Producer {tag}"),
    )
    conn.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, %s, 'ok')",
        (snapshot_id, source_id, f"hash-{tag}"),
    )
    conn.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', 'A paragraph.')",
        (artifact_id, snapshot_id),
    )
    conn.commit()
    blocks.store_blocks(conn, artifact_id, blocks.split_blocks("A paragraph."))
    return {"source_id": source_id, "artifact_id": artifact_id}


def _target(context: dict) -> harness.Target:
    return harness.Target(
        context["source_id"],
        None,
        context["artifact_id"],
        '<block n="1">A paragraph.</block>',
    )


def _prompt(label: str) -> harness.Prompt:
    return harness.Prompt(
        ref=f"passage-cuts/{label}",
        sha=f"{label}-sha",
        template="{{body}}",
    )


def test_done_passage_cut_run_already_has_its_published_representation(db):
    context = _seed_context(db, "success")

    summary = harness.execute(
        db,
        _prompt("atomic-success"),
        FakeClient('{"cuts":[]}'),
        [_target(context)],
        workers=1,
    )

    assert harness.fetch_run(db, summary["run_id"])["status"] == "done"
    assert db.execute(
        "SELECT count(*) FROM passage_origin WHERE run_id = %s",
        (summary["run_id"],),
    ).fetchone()[0] == 1


def test_publisher_failure_rolls_back_rows_and_leaves_the_run_unfinished(
    db, monkeypatch
):
    context = _seed_context(db, "publisher-failure")
    prompt = _prompt("atomic-publisher-failure")
    original = producer_publication.publish

    def publish_then_fail(conn, **kwargs):
        original(conn, **kwargs)
        raise RuntimeError("injected publication failure")

    monkeypatch.setattr(harness.producer_publication, "publish", publish_then_fail)

    with pytest.raises(RuntimeError, match="injected publication failure"):
        harness.execute(
            db,
            prompt,
            FakeClient('{"cuts":[]}'),
            [_target(context)],
            workers=1,
        )

    run_id, status = db.execute(
        "SELECT id, status FROM run WHERE prompt_sha = %s ORDER BY started_at DESC LIMIT 1",
        (prompt.sha,),
    ).fetchone()
    assert status == "publishing"
    assert db.execute(
        "SELECT count(*) FROM passage_origin WHERE run_id = %s", (run_id,)
    ).fetchone()[0] == 0


def test_observer_never_sees_done_before_passage_publication(
    db, test_database_url, monkeypatch
):
    context = _seed_context(db, "observer")
    prompt = _prompt("atomic-observer")
    published_uncommitted = threading.Event()
    allow_commit = threading.Event()
    original = producer_publication.publish

    def pause_after_publish(conn, **kwargs):
        result = original(conn, **kwargs)
        published_uncommitted.set()
        assert allow_commit.wait(5), "test did not release producer commit"
        return result

    monkeypatch.setattr(harness.producer_publication, "publish", pause_after_publish)
    failures = []

    def execute():
        try:
            with psycopg.connect(test_database_url) as worker:
                harness.execute(
                    worker,
                    prompt,
                    FakeClient('{"cuts":[]}'),
                    [_target(context)],
                    workers=1,
                )
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=execute)
    thread.start()
    try:
        assert published_uncommitted.wait(5)
        with psycopg.connect(test_database_url, autocommit=True) as observer:
            run_id, status = observer.execute(
                "SELECT id, status FROM run WHERE prompt_sha = %s", (prompt.sha,)
            ).fetchone()
            visible_origins = observer.execute(
                "SELECT count(*) FROM passage_origin WHERE run_id = %s", (run_id,)
            ).fetchone()[0]
        assert (status, visible_origins) == ("publishing", 0)
    finally:
        allow_commit.set()
        thread.join(timeout=10)

    assert not thread.is_alive()
    assert failures == []
    deadline = time.monotonic() + 2
    with psycopg.connect(test_database_url, autocommit=True) as observer:
        while time.monotonic() < deadline:
            status = observer.execute(
                "SELECT status FROM run WHERE id = %s", (run_id,)
            ).fetchone()[0]
            visible_origins = observer.execute(
                "SELECT count(*) FROM passage_origin WHERE run_id = %s", (run_id,)
            ).fetchone()[0]
            if status == "done":
                break
            time.sleep(0.01)
    assert (status, visible_origins) == ("done", 1)
