"""Task materialization and the task-triage targets; transport faked, database real."""

import json
import pytest
from psycopg.types.json import Jsonb

from universe import blocks, harness, passages, task_triage, tasks
from universe.blocks import split_blocks
from universe.model_client import ModelClient

BODY = """# Tasks lesson

First paragraph, about alpha.

Second paragraph, about beta.

Third paragraph, about gamma.
"""


@pytest.fixture(scope="module")
def tasks_artifact(db) -> str:
    """A source of this module's own, blocked, independent of other fixtures."""
    source_id = "tasks-src-1"
    snapshot_id = f"{source_id}:snap:test"
    artifact_id = f"{snapshot_id}:markdown"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', 'Tasks lesson', 'article')"
        " ON CONFLICT DO NOTHING",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'deadbeef', 'ok') ON CONFLICT DO NOTHING",
        (snapshot_id, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', %s) ON CONFLICT DO NOTHING",
        (artifact_id, snapshot_id, BODY),
    )
    db.commit()
    blocks.store_blocks(db, artifact_id, split_blocks(BODY))
    return artifact_id


@pytest.fixture(scope="module")
def cuts_run(db, tasks_artifact) -> str:
    """A hand-written cuts run so passages exist without any model."""
    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, 'passage-cuts', 'fake/model', 'passage-cuts/v001',"
        " 'abc', %s, 'done')",
        (run_id, Jsonb({"blocker_version": blocks.BLOCKER_VERSION})),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response) VALUES (%s, %s, %s, %s)",
        (f"{run_id}-0001", run_id, tasks_artifact, json.dumps({"cuts": [3]})),
    )
    db.commit()
    return run_id


@pytest.fixture(scope="module")
def gen_run(db, cuts_run) -> str:
    """A task-generation run written by hand over the cuts run's passages."""
    passages.materialize(db, cuts_run)
    rows = passages.fetch_passages_for_runs(db, [cuts_run])

    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'task-generation', 'fake/model', 'task-generation/v001', 'abc', 'done')",
        (run_id,),
    )
    for index, passage in enumerate(rows, 1):
        payload = {
            "tasks": [
                {"task": f"Explain item {index}.", "answer": f"Because of {index}."},
                {"task": f"Apply item {index}.", "answer": f"By doing {index}."},
            ]
        }
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, passage_id, response)"
            " VALUES (%s, %s, %s, %s, %s)",
            (f"{run_id}-{index:04d}", run_id, passage["artifact_id"], passage["id"],
             json.dumps(payload)),
        )
    db.commit()
    return run_id


def test_materializing_writes_one_row_per_reported_task(db, gen_run):
    counts = tasks.materialize(db, gen_run)
    assert counts == {"tasks_new": 4, "tasks_existing": 0}

    rows = tasks.fetch_tasks_for_runs(db, [gen_run])
    assert [row["seq"] for row in rows] == [1, 2, 1, 2]
    assert rows[0]["id"] == f"{gen_run}-0001:t01"
    assert rows[0]["body"] == "Explain item 1."
    assert rows[0]["answer"] == "Because of 1."
    assert all(row["passage_id"] for row in rows)


def test_materializing_again_writes_nothing(db, gen_run):
    tasks.materialize(db, gen_run)
    assert tasks.materialize(db, gen_run) == {"tasks_new": 0, "tasks_existing": 4}


def test_materializing_an_empty_task_report_is_a_valid_zero_task_result(
    db, cuts_run
):
    passages.materialize(db, cuts_run)
    passage = passages.fetch_passages_for_runs(db, [cuts_run])[0]
    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'task-generation', 'fake/model',"
        " 'task-generation/v005', 'abc', 'done')",
        (run_id,),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, passage_id, response)"
        " VALUES (%s, %s, %s, %s, %s)",
        (
            f"{run_id}-0001",
            run_id,
            passage["artifact_id"],
            passage["id"],
            json.dumps({"tasks": []}),
        ),
    )
    db.commit()

    assert tasks.materialize(db, run_id) == {
        "tasks_new": 0,
        "tasks_existing": 0,
    }
    assert tasks.fetch_tasks_for_runs(db, [run_id]) == []


def test_materializing_refuses_a_run_of_another_stage(db, cuts_run):
    with pytest.raises(SystemExit, match="not task-generation"):
        tasks.materialize(db, cuts_run)


def test_triage_targets_carry_task_and_answer_over_one_shared_body(db, gen_run):
    tasks.materialize(db, gen_run)
    rows = tasks.fetch_tasks_for_runs(db, [gen_run])
    targets = task_triage.build_targets(db, rows)

    assert len(targets) == len(rows)
    assert len({target.body for target in targets}) == 1  # what the prefix cache needs
    assert [target.task_id for target in targets] == [row["id"] for row in rows]
    assert targets[0].extra_fields == {"task": "Explain item 1.", "answer": "Because of 1."}
    assert all(target.passage_id is None for target in targets)


def test_a_run_item_records_the_task_it_was_about(db, gen_run):
    tasks.materialize(db, gen_run)
    rows = tasks.fetch_tasks_for_runs(db, [gen_run])

    template = "Judge.\n\n<source>\n{{body}}\n</source>\n\n{{task}}\n{{answer}}\n"
    prompt = harness.Prompt(ref="task-triage/vtest", sha="0" * 64, template=template)

    def transport(url, headers, payload, timeout):
        return {
            "choices": [
                {"message": {"content": '{"verdict": "supported"}'}, "finish_reason": "stop"}
            ],
            "usage": {"total_tokens": 5},
        }

    client = ModelClient("fake/model", api_base="https://example.invalid/v1", transport=transport)
    summary = harness.execute(db, prompt, client, task_triage.build_targets(db, rows))
    assert summary["failed"] == 0

    items = harness.fetch_items(db, summary["run_id"])
    assert [item["task_id"] for item in items] == [row["id"] for row in rows]
