"""Producer runs become done atomically with their deterministic rows."""

import threading
import time

import psycopg
import pytest

from universe import blocks, harness, passages, producer_publication, tasks
from universe.blocks import BLOCKER_VERSION


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
    passage_id = passages.passage_id(artifact_id, 1, 1)
    generation_run = f"producer-{tag}-seed-generation"
    generation_item = f"{generation_run}-0001"
    conn.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{}'::jsonb, %s, 'markdown')",
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
    conn.execute(
        "INSERT INTO passage"
        " (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, %s, 1, 1)",
        (passage_id, artifact_id, BLOCKER_VERSION),
    )
    conn.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, 'task-generation', 'fake/seed',"
        " 'task-generation/v001', 'seed-sha', '{}'::jsonb, 'done')",
        (generation_run,),
    )
    conn.execute(
        "INSERT INTO run_item"
        " (id, run_id, artifact_id, passage_id, response)"
        " VALUES (%s, %s, %s, %s,"
        " '{\"tasks\":[{\"task\":\"Parent?\",\"answer\":\"Parent.\"}]}')",
        (generation_item, generation_run, artifact_id, passage_id),
    )
    conn.commit()
    tasks.materialize(conn, generation_run)
    return {
        "source_id": source_id,
        "artifact_id": artifact_id,
        "passage_id": passage_id,
        "parent_task_id": f"{generation_item}:t01",
    }


@pytest.mark.parametrize(
    ("stage", "response", "target_kind", "derived_sql"),
    [
        (
            "passage-cuts",
            '{"cuts":[]}',
            "artifact",
            "SELECT count(*) FROM passage_origin WHERE run_id = %s",
        ),
        (
            "task-generation",
            '{"tasks":[{"task":"Generated?","answer":"Generated."}]}',
            "passage",
            "SELECT count(*) FROM task t JOIN run_item i ON i.id = t.run_item_id"
            " WHERE i.run_id = %s",
        ),
        (
            "task-granularity",
            '{"verdict":"composite","parts":['
            '{"task":"Part one?","answer":"One."},'
            '{"task":"Part two?","answer":"Two."}]}',
            "task",
            "SELECT count(*) FROM task t JOIN run_item i ON i.id = t.run_item_id"
            " WHERE i.run_id = %s",
        ),
    ],
)
def test_done_producer_run_already_has_its_published_representation(
    db, stage, response, target_kind, derived_sql
):
    context = _seed_context(db, f"success-{stage}")
    target = harness.Target(
        context["source_id"],
        None,
        context["artifact_id"],
        "body",
        passage_id=context["passage_id"] if target_kind != "artifact" else None,
        task_id=context["parent_task_id"] if target_kind == "task" else None,
    )
    prompt = harness.Prompt(
        ref=f"{stage}/atomic-success",
        sha=f"atomic-success-{stage}",
        template="{{body}}",
    )

    summary = harness.execute(db, prompt, FakeClient(response), [target], workers=1)

    assert harness.fetch_run(db, summary["run_id"])["status"] == "done"
    expected = 2 if stage == "task-granularity" else 1
    assert db.execute(derived_sql, (summary["run_id"],)).fetchone()[0] == expected


def test_publisher_failure_rolls_back_rows_and_leaves_the_run_unfinished(
    db, monkeypatch
):
    context = _seed_context(db, "publisher-failure")
    target = harness.Target(
        context["source_id"],
        None,
        context["artifact_id"],
        "body",
        passage_id=context["passage_id"],
    )
    prompt = harness.Prompt(
        ref="task-generation/atomic-failure",
        sha="atomic-publisher-failure",
        template="{{body}}",
    )
    original = producer_publication.publish

    def publish_then_fail(conn, **kwargs):
        original(conn, **kwargs)
        raise RuntimeError("injected publication failure")

    monkeypatch.setattr(harness.producer_publication, "publish", publish_then_fail)

    with pytest.raises(RuntimeError, match="injected publication failure"):
        harness.execute(
            db,
            prompt,
            FakeClient('{"tasks":[{"task":"Never visible?","answer":"No."}]}'),
            [target],
            workers=1,
        )

    run_id, status = db.execute(
        "SELECT id, status FROM run WHERE prompt_sha = %s ORDER BY started_at DESC LIMIT 1",
        (prompt.sha,),
    ).fetchone()
    assert status == "publishing"
    assert db.execute(
        "SELECT count(*) FROM task t JOIN run_item i ON i.id = t.run_item_id"
        " WHERE i.run_id = %s",
        (run_id,),
    ).fetchone()[0] == 0


def test_observer_never_sees_done_before_task_publication(
    db, test_database_url, monkeypatch
):
    context = _seed_context(db, "observer")
    target = harness.Target(
        context["source_id"],
        None,
        context["artifact_id"],
        "body",
        passage_id=context["passage_id"],
    )
    prompt = harness.Prompt(
        ref="task-generation/atomic-observer",
        sha="atomic-observer-sha",
        template="{{body}}",
    )
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
                    FakeClient(
                        '{"tasks":[{"task":"Atomic?","answer":"Atomic."}]}'
                    ),
                    [target],
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
                "SELECT id, status FROM run WHERE prompt_sha = %s",
                (prompt.sha,),
            ).fetchone()
            visible_tasks = observer.execute(
                "SELECT count(*) FROM task t JOIN run_item i ON i.id = t.run_item_id"
                " WHERE i.run_id = %s",
                (run_id,),
            ).fetchone()[0]
        assert (status, visible_tasks) == ("publishing", 0)
    finally:
        allow_commit.set()
        thread.join(timeout=10)

    assert not thread.is_alive()
    assert failures == []
    deadline = time.monotonic() + 2
    with psycopg.connect(test_database_url, autocommit=True) as observer:
        while time.monotonic() < deadline:
            status, visible_tasks = observer.execute(
                "SELECT r.status, count(t.id) FROM run r"
                " LEFT JOIN run_item i ON i.run_id = r.id"
                " LEFT JOIN task t ON t.run_item_id = i.id"
                " WHERE r.prompt_sha = %s GROUP BY r.status",
                (prompt.sha,),
            ).fetchone()
            if status == "done":
                break
            time.sleep(0.01)
    assert (status, visible_tasks) == ("done", 1)
