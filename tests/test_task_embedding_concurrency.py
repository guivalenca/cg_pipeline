"""Concurrency durability regressions for statement/task embeddings."""

import argparse
import json
import threading
import time

import psycopg

from universe import task_embedding
from universe.blocks import BLOCKER_VERSION
from universe.tasks import materialize


def test_fast_later_embedding_persists_while_first_call_is_slow(
    db, test_database_url, monkeypatch
):
    source_id = "embedding-hol-source"
    artifact_id = "embedding-hol-artifact"
    passage_id = "embedding-hol-passage"
    generation_run = "embedding-hol-generation"
    generation_item = f"{generation_run}-i1"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{}'::jsonb, 'Embedding HOL', 'markdown')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES ('embedding-hol-snapshot', %s, 'embedding-hol-hash', 'ok')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, 'embedding-hol-snapshot', 'markdown', 'test', 'body')",
        (artifact_id,),
    )
    db.execute(
        "INSERT INTO passage"
        " (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, %s, 0, 0)",
        (passage_id, artifact_id, BLOCKER_VERSION),
    )
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, 'task-generation', 'fake/generator',"
        " 'task-generation/v001', 'generation-sha', '{}'::jsonb, 'done')",
        (generation_run,),
    )
    db.execute(
        "INSERT INTO run_item"
        " (id, run_id, artifact_id, passage_id, response)"
        " VALUES (%s, %s, %s, %s, %s)",
        (
            generation_item,
            generation_run,
            artifact_id,
            passage_id,
            json.dumps(
                {
                    "tasks": [
                        {"task": "slow question", "answer": "slow answer"},
                        {"task": "fast question", "answer": "fast answer"},
                    ]
                }
            ),
        ),
    )
    db.commit()
    materialize(db, generation_run)

    slow_started = threading.Event()
    fast_returned = threading.Event()
    release_slow = threading.Event()

    class OutOfOrderEmbeddingClient:
        def __init__(self, model):
            self.model = model

        def embed(self, texts):
            assert len(texts) == 1
            if "slow question" in texts[0]:
                slow_started.set()
                assert release_slow.wait(5), "test did not release slow embedding"
            else:
                fast_returned.set()
            return [[0.1, 0.2]], {}, 1

    monkeypatch.setattr(task_embedding, "EmbeddingClient", OutOfOrderEmbeddingClient)
    monkeypatch.setattr(
        task_embedding,
        "connect",
        lambda: psycopg.connect(test_database_url),
    )
    args = argparse.Namespace(
        prompt="v001",
        model="fake/embedding-hol",
        gen_runs=[generation_run],
        statements_from=None,
        passages_from=None,
        revision_run=None,
        granularity_run=None,
        parts_revision_run=None,
        workers=2,
    )
    failures = []

    def run_embedding():
        try:
            task_embedding.cmd_run(args)
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=run_embedding)
    thread.start()
    try:
        assert slow_started.wait(5)
        assert fast_returned.wait(5)
        deadline = time.monotonic() + 5
        counts = (0, 0)
        with psycopg.connect(test_database_url, autocommit=True) as observer:
            while time.monotonic() < deadline:
                counts = tuple(
                    row[0]
                    for row in observer.execute(
                        "SELECT count(*) FROM run_item i JOIN run r ON r.id = i.run_id"
                        " WHERE r.stage = 'task-embedding' AND r.model = %s"
                        " AND i.task_id = %s"
                        " UNION ALL"
                        " SELECT count(*) FROM run_item i JOIN run r ON r.id = i.run_id"
                        " WHERE r.stage = 'task-embedding' AND r.model = %s"
                        " AND i.task_id = %s",
                        (
                            args.model,
                            f"{generation_item}:t02",
                            args.model,
                            f"{generation_item}:t01",
                        ),
                    ).fetchall()
                )
                if counts[0] == 1:
                    break
                time.sleep(0.01)
        assert counts == (1, 0)
    finally:
        release_slow.set()
        thread.join(timeout=10)

    assert not thread.is_alive()
    assert failures == []
