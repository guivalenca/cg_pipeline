"""Task embeddings and their report helpers; no model or transport calls."""

import re
from pathlib import Path

import pytest

from universe import harness
from universe.harness import load_prompt
from universe.task_embedding import STAGE, build_parser, cmd_run
from universe.task_embedding_report import components, percentile

PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "prompts" / "task-embedding" / "v001.md"
)


# --- the stage's files ------------------------------------------------------


def test_the_prompt_is_only_the_task_and_answer():
    assert PROMPT_PATH.read_bytes() == b"{{task}}\n\n{{answer}}\n"

    prompt = load_prompt(STAGE, "v001", require_body=False)
    assert "{{task}}" in prompt.template and "{{answer}}" in prompt.template
    assert "{{body}}" not in prompt.template
    assert prompt.render_fields({"task": "Question?", "answer": "Answer."}) == (
        "Question?\n\nAnswer.\n"
    )


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
