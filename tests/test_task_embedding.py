"""Task embeddings and their report helpers; no live model calls."""

import argparse
import re
import uuid
from pathlib import Path

import pytest

from universe import harness, task_embedding
from universe.blocks import BLOCKER_VERSION
from universe.harness import load_prompt
from universe.model_client import ModelError
from universe.task_embedding import (
    STAGE,
    build_parser,
    cmd_run,
    statement_embedding_inputs,
)
from universe.task_embedding_report import components, percentile

PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "prompts" / "task-embedding" / "v001.md"
)
STATEMENT_PROMPT_PATH = PROMPT_PATH.with_name("v002.md")


# --- the stage's files ------------------------------------------------------


def test_the_prompt_is_only_the_task_and_answer():
    assert PROMPT_PATH.read_bytes() == b"{{task}}\n\n{{answer}}\n"

    prompt = load_prompt(STAGE, "v001", require_body=False)
    assert "{{task}}" in prompt.template and "{{answer}}" in prompt.template
    assert "{{body}}" not in prompt.template
    assert prompt.render_fields({"task": "Question?", "answer": "Answer."}) == (
        "Question?\n\nAnswer.\n"
    )


def test_statement_scope_keeps_only_stated_task_and_renders_statement_text(db):
    prefix = "task-embedding-statements"
    source_id = f"{prefix}-source"
    snapshot_id = f"{source_id}:snapshot"
    artifact_id = f"{snapshot_id}:markdown"
    passage_id = f"{artifact_id}:p01"
    generation_run = harness.claim_run(
        db, "task-generation", "fake/model", "task/test", "abc", {}
    )
    generation_item = f"{generation_run}-0001"
    task_ids = [f"{prefix}-t01", f"{prefix}-t02"]
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', 'Statement embedding', 'article')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, %s, 'ok')",
        (snapshot_id, source_id, f"{prefix}-hash"),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', 'Body')",
        (artifact_id, snapshot_id),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, %s, '{}')",
        (generation_item, generation_run, artifact_id),
    )
    db.execute(
        "INSERT INTO passage (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, 'test', 1, 1)",
        (passage_id, artifact_id),
    )
    for seq, task_id in enumerate(task_ids, 1):
        db.execute(
            "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (task_id, generation_item, passage_id, seq, f"Task {seq}", f"Answer {seq}"),
        )

    statement_run = harness.claim_run(
        db, "kc-statement", "fake/model", "kc-statement/test", "def", {}
    )
    responses = [
        '{"verdict":"stated","statement":"Learner can identify the invariant."}',
        '{"verdict":"unsure","reason":"Task is ambiguous."}',
    ]
    for index, (task_id, response) in enumerate(zip(task_ids, responses), 1):
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
            " VALUES (%s, %s, %s, %s, %s)",
            (f"{statement_run}-{index:04d}", statement_run, artifact_id, task_id, response),
        )
    db.commit()

    assert STATEMENT_PROMPT_PATH.read_bytes() == b"{{statement}}\n"
    prompt = load_prompt(STAGE, "v002", require_body=False)
    tasks, rendered = statement_embedding_inputs(db, [statement_run], prompt)

    assert [task["id"] for task in tasks] == [task_ids[0]]
    assert rendered == ["Learner can identify the invariant.\n"]


# --- stored vectors --------------------------------------------------------


def test_task_embeddings_hold_variable_vectors_and_cosine_similarity(db):
    source_id = "task-embedding-src"
    snapshot_id = f"{source_id}:snap:test"
    artifact_id = f"{snapshot_id}:markdown"
    passage_id = f"{artifact_id}:p01"
    generation_run = harness.next_run_id(db)
    generation_item = f"{generation_run}-0001"
    task_ids = [f"{generation_item}:t01", f"{generation_item}:t02"]

    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', 'Embedding lesson', 'article')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'deadbeef', 'ok')",
        (snapshot_id, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', 'Body')",
        (artifact_id, snapshot_id),
    )
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'task-generation', 'fake/model', 'task-generation/v001', 'abc', 'done')",
        (generation_run,),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, %s, '{}')",
        (generation_item, generation_run, artifact_id),
    )
    db.execute(
        "INSERT INTO passage"
        " (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, 'test', 1, 1)",
        (passage_id, artifact_id),
    )
    for seq, task_id in enumerate(task_ids, 1):
        db.execute(
            "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (task_id, generation_item, passage_id, seq, f"Task {seq}", f"Answer {seq}"),
        )

    embedding_run = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, %s, 'fake/embedding', %s, 'def', 'done')",
        (embedding_run, STAGE, f"{STAGE}/v001"),
    )
    vectors = ["[1,0]", "[0,1]"]
    for index, (task_id, vector) in enumerate(zip(task_ids, vectors), 1):
        item_id = f"{embedding_run}-{index:04d}"
        rendered = f"Task {index}\n\nAnswer {index}\n"
        db.execute(
            "INSERT INTO run_item"
            " (id, run_id, artifact_id, passage_id, task_id, response)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (item_id, embedding_run, artifact_id, passage_id, task_id, rendered),
        )
        db.execute(
            "INSERT INTO task_embedding"
            " (run_item_id, task_id, model, input_sha, dims, embedding)"
            " VALUES (%s, %s, 'fake/embedding', 'sha', 2, %s::vector)",
            (item_id, task_id, vector),
        )
    db.commit()

    orthogonal = db.execute(
        "SELECT 1 - (a.embedding <=> b.embedding)"
        " FROM task_embedding a, task_embedding b"
        " WHERE a.task_id = %s AND b.task_id = %s",
        task_ids,
    ).fetchone()[0]
    identical = db.execute(
        "SELECT 1 - (a.embedding <=> b.embedding)"
        " FROM task_embedding a, task_embedding b"
        " WHERE a.task_id = %s AND b.task_id = %s",
        (task_ids[0], task_ids[0]),
    ).fetchone()[0]
    assert orthogonal == pytest.approx(0.0)
    assert identical == pytest.approx(1.0)


# --- report helpers --------------------------------------------------------


def test_percentile_is_exact_at_edges_and_interpolates_between_values():
    values = [30.0, 0.0, 10.0, 20.0]
    assert percentile(values, 0) == 0.0
    assert percentile(values, 100) == 30.0
    assert percentile(values, 25) == pytest.approx(7.5)


def test_components_are_deterministic_with_clusters_and_a_singleton():
    nodes = ["T05", "T03", "T01", "T04", "T02"]
    edges = [("T04", "T03"), ("T02", "T01")]
    assert components(nodes, edges) == [
        ["T01", "T02"],
        ["T03", "T04"],
        ["T05"],
    ]


# --- claiming stamped runs ------------------------------------------------


def test_claim_run_returns_readable_incrementing_ids(db):
    first = harness.claim_run(db, "claim-test", "model-a", "claim-test/v001", "abc", {})
    second = harness.claim_run(db, "claim-test", "model-b", "claim-test/v001", "abc", {})

    assert re.fullmatch(r"r\d{4}", first)
    assert int(second[1:]) == int(first[1:]) + 1
    assert harness.fetch_run(db, first)["status"] == "running"


def test_post_split_overlay_flags_are_available_and_require_granularity():
    args = build_parser().parse_args(
        [
            "run", "--prompt", "v001", "--model", "fake/embedding", "--gen-runs", "r0001",
            "--granularity-run", "r0002", "--parts-revision-run", "r0003",
        ]
    )
    assert args.granularity_run == "r0002"
    assert args.parts_revision_run == "r0003"

    args.granularity_run = None
    with pytest.raises(SystemExit, match="--parts-revision-run requires --granularity-run"):
        cmd_run(args)


def test_embedding_parser_accepts_statement_runs_without_generation_runs():
    args = build_parser().parse_args(
        [
            "run", "--prompt", "v002", "--model", "fake/embedding",
            "--statements-from", "r0001,r0002",
        ]
    )

    assert args.gen_runs is None
    assert args.statements_from == ["r0001", "r0002"]


def test_embedding_run_requires_generation_or_statement_runs():
    args = build_parser().parse_args(
        ["run", "--prompt", "v002", "--model", "fake/embedding"]
    )

    with pytest.raises(
        SystemExit, match="one of --gen-runs or --statements-from is required"
    ):
        cmd_run(args)


def test_embedding_run_persists_billable_failure_telemetry(db, monkeypatch):
    marker = uuid.uuid4().hex[:8]
    source_id = f"embedding-error-source-{marker}"
    snapshot_id = f"embedding-error-snapshot-{marker}"
    artifact_id = f"embedding-error-artifact-{marker}"
    passage_id = f"embedding-error-passage-{marker}"
    generation = harness.claim_run(
        db, "task-generation", "fake/generator", "task-generation/v001", "sha", {}
    )
    generation_item = f"{generation}-seed"
    task_id = f"embedding-error-task-{marker}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{}'::jsonb, 'Embedding error', 'article')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, %s, 'ok')",
        (snapshot_id, source_id, f"hash-{marker}"),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', 'body')",
        (artifact_id, snapshot_id),
    )
    db.execute(
        "INSERT INTO passage"
        " (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, %s, 0, 0)",
        (passage_id, artifact_id, BLOCKER_VERSION),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, passage_id, response)"
        " VALUES (%s, %s, %s, %s, '{}')",
        (generation_item, generation, artifact_id, passage_id),
    )
    db.execute(
        "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
        " VALUES (%s, %s, %s, 1, 'Question?', 'Answer.')",
        (task_id, generation_item, passage_id),
    )
    db.commit()

    class BorrowedConnection:
        def __enter__(self):
            return db

        def __exit__(self, *_):
            return False

    class FailedEmbeddingClient:
        def __init__(self, model):
            self.model = model

        def embed(self, texts):
            error = ModelError("malformed billed embedding")
            error.usage = {"cost": 0.0019, "total_tokens": 11}
            error.duration_ms = 47
            raise error

    prompt = type("Prompt", (), {"ref": "task-embedding/v002", "sha": "sha"})()
    monkeypatch.setattr(task_embedding, "connect", lambda: BorrowedConnection())
    monkeypatch.setattr(task_embedding, "EmbeddingClient", FailedEmbeddingClient)
    monkeypatch.setattr(task_embedding, "load_prompt", lambda *a, **k: prompt)
    monkeypatch.setattr(
        task_embedding,
        "statement_embedding_inputs",
        lambda conn, runs, loaded_prompt: (
            [{
                "id": task_id,
                "artifact_id": artifact_id,
                "passage_id": passage_id,
                "body": "Question?",
                "answer": "Answer.",
            }],
            ["Statement"],
        ),
    )

    task_embedding.cmd_run(
        argparse.Namespace(
            prompt="v002",
            model="fake/embedding-error",
            gen_runs=None,
            statements_from=["statement-run"],
            passages_from=None,
            revision_run=None,
            granularity_run=None,
            parts_revision_run=None,
            workers=1,
        )
    )

    assert db.execute(
        "SELECT usage, duration_ms, error FROM run_item"
        " WHERE run_id = (SELECT id FROM run WHERE stage = 'task-embedding'"
        " AND model = 'fake/embedding-error' ORDER BY started_at DESC LIMIT 1)"
    ).fetchone() == (
        {"cost": 0.0019, "total_tokens": 11},
        47,
        "ModelError: malformed billed embedding",
    )
