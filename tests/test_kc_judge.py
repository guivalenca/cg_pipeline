"""Candidate selection and permanent directional KC verdicts."""

import json
import threading
import time

import psycopg
import pytest

from universe import harness, judge_manifest, pipeline_lease
from universe.judge_manifest import manifest_sha256
from universe.kc_groups import build_context, compute_snapshot
from universe.kc_judge import (
    DEFAULT_EXTRA,
    DEFAULT_MODEL,
    _matching_verdicts,
    build_parser,
    fetch_candidate_data,
    fetch_usable_axis_verdicts,
    generate_candidates,
    parse_verdicts,
    run_judge,
)
from universe.kc_statement import fetch_usable_statements
from universe.task_modality import modality_of


def test_parser_accepts_multiple_statement_and_axis_runs():
    args = build_parser().parse_args(
        [
            "run",
            "--statements-from", "r0001,r0002",
            "--embedding-run", "r0003",
            "--modality-run", "r0004,r0006",
            "--knowledge-run", "r0005,r0007",
        ]
    )

    assert args.statements_from == ["r0001", "r0002"]
    assert args.modality_runs == ["r0004", "r0006"]
    assert args.knowledge_runs == ["r0005", "r0007"]
    assert args.model == "deepseek/deepseek-v4-flash-0731"
    assert DEFAULT_MODEL == args.model
    assert DEFAULT_EXTRA["reasoning_effort"] == "low"
    assert "thinking" not in DEFAULT_EXTRA


def test_axis_verdicts_keep_the_newest_usable_item_per_task():
    rows = [
        ("r-new-0002", "task-a", "{}", None),
        (
            "r-new-0001",
            "task-b",
            json.dumps({"verdict": "explain", "reason": "new"}),
            None,
        ),
        (
            "r-old-0002",
            "task-b",
            json.dumps({"verdict": "do", "reason": "old"}),
            None,
        ),
        (
            "r-old-0001",
            "task-a",
            json.dumps({"verdict": "do", "reason": "fallback"}),
            None,
        ),
    ]

    class StubConnection:
        def execute(self, query, params):
            assert (
                "ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC" in query
            )
            assert params == (["r-old", "r-new"],)
            return self

        def fetchall(self):
            return rows

    assert fetch_usable_axis_verdicts(
        StubConnection(), ["r-old", "r-new"], modality_of
    ) == {"task-a": "do", "task-b": "explain"}


def test_reused_verdict_selection_is_deterministic_for_each_exact_pair_input():
    rows = [
        ("task-a", "task-b", "same-input", "newest-item"),
        ("task-a", "task-c", "same-input", "other-pair-item"),
    ]

    class StubConnection:
        def execute(self, query, params):
            assert (
                "DISTINCT ON (task_a_id, task_b_id, input_key)" in query
            )
            assert (
                "ORDER BY task_a_id, task_b_id, input_key,"
                " created_at DESC, run_item_id DESC"
            ) in query
            assert params == (["same-input"],)
            return self

        def fetchall(self):
            # PostgreSQL's DISTINCT ON has already selected the deterministic
            # newest row for each pair/input identity.
            return rows

    descriptors = [
        (("task-a", "task-b", 0.9), "prompt one", "same-input"),
        (("task-a", "task-c", 0.8), "prompt two", "same-input"),
    ]

    assert _matching_verdicts(StubConnection(), descriptors) == {
        ("task-a", "task-b", "same-input"): "newest-item",
        ("task-a", "task-c", "same-input"): "other-pair-item",
    }


def test_newest_usable_unsure_statement_blocks_older_stated_text(db):
    task_ids, runs = _input_runs(db, "judge-statement-unsure")
    old_run = runs["kc-statement"][0]
    artifact_id = db.execute(
        "SELECT artifact_id FROM run_item WHERE run_id = %s LIMIT 1", (old_run,)
    ).fetchone()[0]
    newer = harness.claim_run(
        db,
        "kc-statement",
        "fake/model",
        "kc-statement/test",
        "new",
        harness.fetch_run(db, old_run)["params"],
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
        " VALUES (%s, %s, %s, %s, %s)",
        (
            f"{newer}-0001",
            newer,
            artifact_id,
            task_ids[0],
            json.dumps({"verdict": "unsure", "reason": "not stable"}),
        ),
    )
    db.execute(
        "UPDATE run SET started_at = started_at + interval '1 hour' WHERE id = %s",
        (newer,),
    )
    db.commit()

    statements = fetch_usable_statements(db, [old_run, newer])

    assert task_ids[0] not in statements
    assert statements[task_ids[1]] == "Shared concept two"


@pytest.mark.parametrize("newer_value", ["error", "unparseable"])
def test_failed_newer_statement_attempt_falls_back_to_older_stated_text(
    db, newer_value
):
    task_ids, runs = _input_runs(db, f"judge-statement-{newer_value}")
    old_run = runs["kc-statement"][0]
    artifact_id = db.execute(
        "SELECT artifact_id FROM run_item WHERE run_id = %s LIMIT 1", (old_run,)
    ).fetchone()[0]
    newer = harness.claim_run(
        db,
        "kc-statement",
        "fake/model",
        "kc-statement/test",
        "new",
        harness.fetch_run(db, old_run)["params"],
    )
    if newer_value == "error":
        db.execute(
            "INSERT INTO run_item"
            " (id, run_id, artifact_id, task_id, error)"
            " VALUES (%s, %s, %s, %s, 'provider failed')",
            (f"{newer}-0001", newer, artifact_id, task_ids[0]),
        )
    else:
        db.execute(
            "INSERT INTO run_item"
            " (id, run_id, artifact_id, task_id, response)"
            " VALUES (%s, %s, %s, %s, 'not json')",
            (f"{newer}-0001", newer, artifact_id, task_ids[0]),
        )
    db.execute(
        "UPDATE run SET started_at = started_at + interval '1 hour' WHERE id = %s",
        (newer,),
    )
    db.commit()

    statements = fetch_usable_statements(db, [old_run, newer])

    assert statements[task_ids[0]] == "Shared concept one"


def test_candidates_apply_floor_caps_axes_and_already_judged_after_ranking():
    items = [
        {
            "id": f"t{index:02d}",
            "statement": "shared words" if index < 8 else "different",
            "modality": "explain" if index != 1 else "do",
            "knowledge": "concept",
        }
        for index in range(8)
    ]
    similarities = {
        ("t00", f"t{index:02d}"): 0.99 - index / 100
        for index in range(1, 8)
    }
    similarities.update(
        {
            (f"t{left:02d}", f"t{right:02d}"): 0.995
            for left in range(1, 8)
            for right in range(left + 1, 8)
        }
    )

    candidates = generate_candidates(
        items,
        similarities,
        already_judged={("t00", "t02")},
        lexical_k=0,
    )

    # t01 consumed the first of t00's six semantic slots before the axis
    # filter, t02 was already judged, and t07 was below t00's cap.
    assert ("t00", "t01", 0.98) not in candidates
    assert ("t00", "t02", 0.97) not in candidates
    assert ("t00", "t06", 0.93) in candidates
    assert ("t00", "t07", 0.92) not in candidates


def test_lexical_top_five_adds_a_below_floor_pair_and_normalizes_it():
    items = [
        {"id": "b", "statement": "rare shared term", "modality": "do", "knowledge": "procedure"},
        {"id": "a", "statement": "shared term", "modality": "do", "knowledge": "procedure"},
    ]

    assert generate_candidates(items, {("b", "a"): 0.25}) == [("a", "b", 0.25)]


def test_semantic_candidates_respect_the_floor_and_both_axes():
    base = {"statement": "no lexical overlap", "modality": "explain", "knowledge": "concept"}
    items = [
        {"id": "t1", **base},
        {"id": "t2", **base, "statement": "other tokens"},
        {"id": "t3", **base, "knowledge": "fact"},
    ]

    assert generate_candidates(
        items,
        {("t1", "t2"): 0.6999, ("t1", "t3"): 0.95},
        lexical_k=0,
    ) == []


@pytest.mark.parametrize(
    "a_to_b,b_to_a",
    [
        ("clear_yes", "likely"),
        ("unlikely", "clear_no"),
    ],
)
def test_tool_result_parses_both_directions_on_the_four_level_scale(a_to_b, b_to_a):
    parsed = parse_verdicts(
        json.dumps(
            {
                "verdict_a_to_b": a_to_b,
                "reason_a_to_b": "  A reason. ",
                "verdict_b_to_a": b_to_a,
                "reason_b_to_a": "B reason.",
            }
        )
    )

    assert parsed == {
        "verdict_a_to_b": a_to_b,
        "reason_a_to_b": "A reason.",
        "verdict_b_to_a": b_to_a,
        "reason_b_to_a": "B reason.",
    }


class FakeModelClient:
    model = "fake/model"
    params = {"fake": True}

    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    def complete(self, prompt):
        self.prompts.append(prompt)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def _input_runs(db, prefix, *, task_count=2):
    source_id = f"{prefix}-source"
    snapshot_id = f"{source_id}:snapshot"
    artifact_id = f"{snapshot_id}:markdown"
    passage_id = f"{artifact_id}:p01"
    generation_run = harness.claim_run(
        db, "task-generation", "fake/model", "task/test", "abc", {}
    )
    generation_item = f"{generation_run}-0001"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', 'Judge test', 'article')",
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
    task_ids = [
        f"{prefix}-t{number:02d}" for number in range(1, task_count + 1)
    ]
    for seq, task_id in enumerate(task_ids, 1):
        db.execute(
            "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (task_id, generation_item, passage_id, seq, f"Task {seq}", f"Answer {seq}"),
        )

    run_specs = [
        (
            "kc-statement",
            [
                {
                    "verdict": "stated",
                    "statement": "Shared concept " + (
                        {1: "one", 2: "two"}.get(number, str(number))
                    ),
                }
                for number in range(1, task_count + 1)
            ],
        ),
        ("task-embedding", [None] * task_count),
        (
            "task-modality",
            [{"verdict": "explain", "reason": "test"}] * task_count,
        ),
        (
            "task-knowledge",
            [{"verdict": "concept", "reason": "test"}] * task_count,
        ),
    ]
    run_ids = {}
    for stage, responses in run_specs:
        run_id = harness.claim_run(
            db,
            stage,
            "fake/model",
            f"{stage}/test",
            "abc",
            {"gen_runs": [generation_run]} if stage == "kc-statement" else {},
        )
        run_ids[stage] = run_id
        for index, (task_id, response) in enumerate(zip(task_ids, responses), 1):
            item_id = f"{run_id}-{index:04d}"
            body = "embedded input" if response is None else json.dumps(response)
            db.execute(
                "INSERT INTO run_item"
                " (id, run_id, artifact_id, task_id, response)"
                " VALUES (%s, %s, %s, %s, %s)",
                (item_id, run_id, artifact_id, task_id, body),
            )
            if stage == "task-embedding":
                vector = "[1,0]" if index == 1 else "[0.8,0.6]"
                db.execute(
                    "INSERT INTO task_embedding"
                    " (run_item_id, task_id, model, input_sha, dims, embedding)"
                    " VALUES (%s, %s, 'fake/embedding', 'sha', 2, %s::vector)",
                    (item_id, task_id, vector),
                )
    db.commit()
    run_ids["kc-statement"] = [run_ids["kc-statement"]]
    run_ids["task-modality"] = [run_ids["task-modality"]]
    run_ids["task-knowledge"] = [run_ids["task-knowledge"]]
    return task_ids, run_ids


def test_candidate_data_combines_two_statement_runs(db):
    task_ids, runs = _input_runs(db, "judge-multi-statements")
    artifact_id = db.execute(
        "SELECT p.artifact_id FROM task t"
        " JOIN passage p ON p.id = t.passage_id WHERE t.id = %s",
        (task_ids[0],),
    ).fetchone()[0]
    statements = ["Shared algebra concept one", "Shared algebra concept two"]
    generation_run = db.execute(
        "SELECT i.run_id FROM task t JOIN run_item i ON i.id = t.run_item_id"
        " WHERE t.id = %s",
        (task_ids[0],),
    ).fetchone()[0]
    statement_runs = []
    for index, (task_id, statement) in enumerate(zip(task_ids, statements), 1):
        run_id = harness.claim_run(
            db,
            "kc-statement",
            "fake/model",
            "kc-statement/test",
            "abc",
            {"gen_runs": [generation_run]},
        )
        statement_runs.append(run_id)
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
            " VALUES (%s, %s, %s, %s, %s)",
            (
                f"{run_id}-0001",
                run_id,
                artifact_id,
                task_id,
                json.dumps({"verdict": "stated", "statement": statement}),
            ),
        )
    db.commit()

    items, similarities, judged = fetch_candidate_data(
        db,
        statement_runs,
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        "judge-multi/model",
        "kc-judge/test-multi",
    )

    assert {item["id"]: item["statement"] for item in items} == dict(
        zip(task_ids, statements)
    )
    assert generate_candidates(items, similarities, judged) == [
        (task_ids[0], task_ids[1], 0.8)
    ]


def test_candidate_data_combines_two_modality_runs(db):
    task_ids, runs = _input_runs(db, "judge-multi-modality")
    artifact_id = db.execute(
        "SELECT p.artifact_id FROM task t"
        " JOIN passage p ON p.id = t.passage_id WHERE t.id = %s",
        (task_ids[0],),
    ).fetchone()[0]
    modality_runs = []
    for task_id in task_ids:
        run_id = harness.claim_run(
            db, "task-modality", "fake/model", "task-modality/test", "abc", {}
        )
        modality_runs.append(run_id)
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
            " VALUES (%s, %s, %s, %s, %s)",
            (
                f"{run_id}-0001",
                run_id,
                artifact_id,
                task_id,
                json.dumps({"verdict": "explain", "reason": "test"}),
            ),
        )
    db.commit()

    items, similarities, judged = fetch_candidate_data(
        db,
        runs["kc-statement"],
        runs["task-embedding"],
        modality_runs,
        runs["task-knowledge"],
        "judge-multi-axis/model",
        "kc-judge/test-multi-axis",
    )

    assert {item["id"]: item["modality"] for item in items} == {
        task_ids[0]: "explain",
        task_ids[1]: "explain",
    }
    assert generate_candidates(items, similarities, judged) == [
        (task_ids[0], task_ids[1], 0.8)
    ]


def test_axes_may_cover_an_unsure_task_omitted_from_statement_embeddings(db):
    task_ids, runs = _input_runs(db, "judge-axis-superset")
    statement_run = runs["kc-statement"][0]
    db.execute(
        "UPDATE run_item SET response = %s"
        " WHERE run_id = %s AND task_id = %s",
        (
            json.dumps({"verdict": "unsure", "reason": "not a stable KC"}),
            statement_run,
            task_ids[1],
        ),
    )
    embedding_item = db.execute(
        "SELECT i.id FROM run_item i"
        " WHERE i.run_id = %s AND i.task_id = %s",
        (runs["task-embedding"], task_ids[1]),
    ).fetchone()[0]
    db.execute("DELETE FROM task_embedding WHERE run_item_id = %s", (embedding_item,))
    db.execute("DELETE FROM run_item WHERE id = %s", (embedding_item,))
    db.commit()

    items, similarities, judged = fetch_candidate_data(
        db,
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        "fake/model",
        "kc-judge/test",
    )

    assert [item["id"] for item in items] == [task_ids[0]]
    assert similarities == {}
    assert judged == set()

    summary = run_judge(
        db,
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        FakeModelClient([]),
        workers=1,
    )
    grouping_id, groups = compute_snapshot(db, judge_run_id=summary["run_id"])

    assert summary["candidate_count"] == 0
    assert summary["candidate_manifest_complete"] is True
    assert groups == []
    assert db.execute(
        "SELECT count(*) FROM kc_grouping_verdict WHERE grouping_id = %s",
        (grouping_id,),
    ).fetchone()[0] == 0


def test_run_stamps_the_call_and_both_directional_verdicts(db):
    task_ids, runs = _input_runs(db, "judge-ok")
    response = json.dumps(
        {
            "verdict_a_to_b": "clear_yes",
            "reason_a_to_b": "A contains B.",
            "verdict_b_to_a": "likely",
            "reason_b_to_a": "B probably contains A.",
        }
    )
    client = FakeModelClient([(response, {"input_tokens": 10}, 25)])

    summary = run_judge(
        db,
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        client,
        workers=1,
    )

    assert summary["status"] == "done"
    assert summary["ok"] == 1
    assert summary["candidate_manifest_complete"] is True
    assert len(client.prompts) == 1
    assert "Shared concept one" in client.prompts[0]
    assert "Task 2" in client.prompts[0]
    assert db.execute(
        "SELECT stage, model, status FROM run WHERE id = %s", (summary["run_id"],)
    ).fetchone() == ("kc-judge", "fake/model", "done")
    assert harness.fetch_run(db, summary["run_id"])["params"]["statements_from"] == runs[
        "kc-statement"
    ]
    assert harness.fetch_run(db, summary["run_id"])["params"]["modality_runs"] == runs[
        "task-modality"
    ]
    assert harness.fetch_run(db, summary["run_id"])["params"]["knowledge_runs"] == runs[
        "task-knowledge"
    ]
    assert harness.fetch_run(db, summary["run_id"])["params"][
        "candidate_manifest_complete"
    ] is True
    params = harness.fetch_run(db, summary["run_id"])["params"]
    manifest_ids = [
        row[0]
        for row in db.execute(
            "SELECT run_item_id FROM kc_judge_manifest"
            " WHERE judge_run_id = %s ORDER BY seq",
            (summary["run_id"],),
        ).fetchall()
    ]
    assert params["candidate_count"] == len(manifest_ids) == 1
    assert params["candidate_manifest_sha256"] == manifest_sha256(manifest_ids)
    assert "candidate_manifest_run_item_ids" not in params
    assert db.execute(
        "SELECT count(*) FROM kc_grouping WHERE params->>'build_key' = %s",
        (summary["build_key"],),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT artifact_id, task_id, usage->>'input_tokens', duration_ms, error"
        " FROM run_item WHERE run_id = %s",
        (summary["run_id"],),
    ).fetchone() == (None, task_ids[0], "10", 25, None)
    assert db.execute(
        "SELECT task_a_id, task_b_id, a_implies_b, b_implies_a"
        " FROM kc_verdict WHERE run_item_id = %s",
        (f"{summary['run_id']}-0001",),
    ).fetchone() == (task_ids[0], task_ids[1], "clear_yes", "likely")


def test_certified_manifest_rejects_a_verdict_endpoint_outside_statement_scope(db):
    _, runs = _input_runs(db, "judge-forged-endpoint")
    foreign_task_ids, _ = _input_runs(db, "judge-forged-endpoint-foreign")
    response = json.dumps(
        {
            "verdict_a_to_b": "clear_yes",
            "reason_a_to_b": "A contains B.",
            "verdict_b_to_a": "clear_no",
            "reason_b_to_a": "B does not contain A.",
        }
    )
    summary = run_judge(
        db,
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        FakeModelClient([(response, None, 1)]),
        workers=1,
    )
    manifest_item = db.execute(
        "SELECT run_item_id FROM kc_judge_manifest WHERE judge_run_id = %s",
        (summary["run_id"],),
    ).fetchone()[0]
    db.execute(
        # The ledger stores each pair in lexical order. This foreign id sorts
        # before the original pair, so forge endpoint A while preserving that
        # independent database invariant.
        "UPDATE kc_verdict SET task_a_id = %s WHERE run_item_id = %s",
        (foreign_task_ids[0], manifest_item),
    )
    db.commit()

    assert judge_manifest.read(db, summary["run_id"]) is None
    with pytest.raises(LookupError, match="certified judge run"):
        build_context(db, summary["run_id"])


def test_limited_attempt_cannot_certify_or_publish_an_incomplete_manifest(db):
    task_ids, runs = _input_runs(db, "judge-limited", task_count=3)
    response = json.dumps(
        {
            "verdict_a_to_b": "clear_yes",
            "reason_a_to_b": "A contains B.",
            "verdict_b_to_a": "clear_yes",
            "reason_b_to_a": "B contains A.",
        }
    )
    client = FakeModelClient([(response, None, 1)])

    summary = run_judge(
        db,
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        client,
        workers=1,
        limit=1,
    )

    assert len(task_ids) == 3
    assert summary["candidate_count"] == 3
    assert len(client.prompts) == 1
    assert summary["candidate_manifest_complete"] is False
    params = harness.fetch_run(db, summary["run_id"])["params"]
    assert "candidate_manifest_complete" not in params
    assert db.execute(
        "SELECT count(*) FROM kc_grouping WHERE params->>'build_key' = %s",
        (summary["build_key"],),
    ).fetchone()[0] == 0
    with pytest.raises(LookupError, match="certified judge run"):
        build_context(db, summary["run_id"])
    with pytest.raises(LookupError, match="certified judge run"):
        compute_snapshot(db, judge_run_id=summary["run_id"])


def test_retry_reuses_partial_verdicts_then_certifies_for_grouped_stage(db):
    _, runs = _input_runs(db, "judge-limited-retry", task_count=3)
    response = json.dumps(
        {
            "verdict_a_to_b": "clear_yes",
            "reason_a_to_b": "A contains B.",
            "verdict_b_to_a": "clear_yes",
            "reason_b_to_a": "B contains A.",
        }
    )
    run_args = (
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
    )
    first = run_judge(
        db,
        *run_args,
        FakeModelClient([(response, None, 1)]),
        workers=1,
        limit=1,
    )
    retry_client = FakeModelClient([(response, None, 1), (response, None, 1)])

    retry = run_judge(db, *run_args, retry_client, workers=1)

    assert first["candidate_manifest_complete"] is False
    assert retry["reused"] == 1
    assert len(retry_client.prompts) == 2
    assert retry["candidate_count"] == 3
    assert retry["candidate_manifest_complete"] is True
    assert harness.fetch_run(db, retry["run_id"])["params"][
        "candidate_manifest_complete"
    ] is True
    manifest_ids = [
        row[0]
        for row in db.execute(
            "SELECT run_item_id FROM kc_judge_manifest"
            " WHERE judge_run_id = %s ORDER BY seq",
            (retry["run_id"],),
        ).fetchall()
    ]
    assert len(manifest_ids) == 3
    assert harness.fetch_run(db, retry["run_id"])["params"][
        "candidate_manifest_sha256"
    ] == manifest_sha256(manifest_ids)
    assert db.execute(
        "SELECT count(*) FROM kc_grouping WHERE params->>'build_key' = %s",
        (retry["build_key"],),
    ).fetchone()[0] == 0

    grouping_id, groups = compute_snapshot(db, judge_run_id=retry["run_id"])

    assert grouping_id is not None
    assert len(groups) == 1


def test_fast_later_judge_result_persists_while_first_candidate_is_still_slow(
    db, test_database_url
):
    _, runs = _input_runs(db, "judge-head-of-line", task_count=3)
    slow_started = threading.Event()
    fast_returned = threading.Event()
    release_slow = threading.Event()
    response = json.dumps(
        {
            "verdict_a_to_b": "clear_yes",
            "reason_a_to_b": "same",
            "verdict_b_to_a": "clear_yes",
            "reason_b_to_a": "same",
        }
    )

    class OutOfOrderClient:
        model = "fake/head-of-line-model"
        params = {"fake": "head-of-line"}

        def complete(self, prompt):
            is_first_candidate = (
                "<task>Task 2</task>" in prompt
                and "<task>Task 3</task>" in prompt
                and "<task>Task 1</task>" not in prompt
            )
            if is_first_candidate:
                slow_started.set()
                assert release_slow.wait(5), "test did not release slow provider"
            else:
                fast_returned.set()
            return response, None, 1

    summaries = []
    failures = []

    def execute_judge():
        try:
            with psycopg.connect(test_database_url) as worker_conn:
                summaries.append(
                    run_judge(
                        worker_conn,
                        runs["kc-statement"],
                        runs["task-embedding"],
                        runs["task-modality"],
                        runs["task-knowledge"],
                        OutOfOrderClient(),
                        workers=3,
                    )
                )
        except BaseException as exc:  # surfaced in the test thread below
            failures.append(exc)

    thread = threading.Thread(target=execute_judge)
    thread.start()
    try:
        assert slow_started.wait(5)
        assert fast_returned.wait(5)
        deadline = time.monotonic() + 5
        observed = []
        with psycopg.connect(test_database_url, autocommit=True) as observer:
            while time.monotonic() < deadline:
                observed = observer.execute(
                    "SELECT i.id FROM run_item i JOIN run r ON r.id = i.run_id"
                    " WHERE r.stage = 'kc-judge' AND r.model = %s"
                    " ORDER BY i.id",
                    (OutOfOrderClient.model,),
                ).fetchall()
                if observed:
                    break
                time.sleep(0.01)

        assert observed
        assert all(not item_id.endswith("-0001") for item_id, in observed)
    finally:
        release_slow.set()
        thread.join(timeout=10)

    assert not thread.is_alive()
    assert failures == []
    assert summaries[0]["status"] == "done"


def test_new_build_can_certify_and_group_a_manifest_reused_entirely_from_old_build(db):
    task_ids, runs = _input_runs(db, "judge-cross-build-reuse")
    response = json.dumps(
        {
            "verdict_a_to_b": "clear_yes",
            "reason_a_to_b": "same knowledge",
            "verdict_b_to_a": "clear_yes",
            "reason_b_to_a": "same knowledge",
        }
    )
    first = run_judge(
        db,
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        FakeModelClient([(response, None, 1)]),
        workers=1,
    )
    old_item = db.execute(
        "SELECT run_item_id FROM kc_judge_manifest WHERE judge_run_id = %s",
        (first["run_id"],),
    ).fetchone()[0]

    replacement = harness.claim_run(
        db, "task-embedding", "fake/model", "task-embedding/test", "new", {}
    )
    for index, task_id in enumerate(task_ids, 1):
        item_id = f"{replacement}-{index:04d}"
        db.execute(
            "INSERT INTO run_item"
            " (id, run_id, artifact_id, task_id, response)"
            " SELECT %s, %s, artifact_id, task_id, response"
            " FROM run_item WHERE run_id = %s AND task_id = %s",
            (item_id, replacement, runs["task-embedding"], task_id),
        )
        vector = "[1,0]" if index == 1 else "[0.8,0.6]"
        db.execute(
            "INSERT INTO task_embedding"
            " (run_item_id, task_id, model, input_sha, dims, embedding)"
            " VALUES (%s, %s, 'fake/embedding', %s, 2, %s::vector)",
            (item_id, task_id, f"replacement-{index}", vector),
        )
    db.commit()

    second_client = FakeModelClient([])
    second = run_judge(
        db,
        runs["kc-statement"],
        replacement,
        runs["task-modality"],
        runs["task-knowledge"],
        second_client,
        workers=1,
    )
    second_item = db.execute(
        "SELECT run_item_id FROM kc_judge_manifest WHERE judge_run_id = %s",
        (second["run_id"],),
    ).fetchone()[0]
    first_grouping, first_groups = compute_snapshot(
        db, judge_run_id=first["run_id"]
    )
    second_grouping, second_groups = compute_snapshot(
        db, judge_run_id=second["run_id"]
    )

    assert first["build_key"] != second["build_key"]
    assert second["reused"] == 1
    assert second_client.prompts == []
    assert second_item == old_item
    assert second_groups == first_groups
    assert db.execute(
        "SELECT run_item_id FROM kc_grouping_verdict WHERE grouping_id = %s",
        (second_grouping,),
    ).fetchall() == [(old_item,)]
    assert first_grouping != second_grouping


def test_failed_call_is_a_run_item_without_a_verdict(db):
    _, runs = _input_runs(db, "judge-failed")
    client = FakeModelClient([RuntimeError("deterministic failure")])

    summary = run_judge(
        db,
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        client,
        workers=1,
    )

    assert summary["status"] == "failed"
    assert summary["ok"] == 0
    assert summary["failed"] == 1
    item_id, response, error = db.execute(
        "SELECT id, response, error FROM run_item WHERE run_id = %s",
        (summary["run_id"],),
    ).fetchone()
    assert response is None
    assert error == "RuntimeError: deterministic failure"
    assert db.execute(
        "SELECT count(*) FROM kc_verdict WHERE run_item_id = %s", (item_id,)
    ).fetchone()[0] == 0


def test_lost_judge_lease_discards_a_completed_provider_result(
    db, monkeypatch
):
    _, runs = _input_runs(db, "judge-lost-lease")
    response = json.dumps(
        {
            "verdict_a_to_b": "clear_yes",
            "reason_a_to_b": "same",
            "verdict_b_to_a": "clear_yes",
            "reason_b_to_a": "same",
        }
    )

    class Supervisor:
        def __init__(self):
            self.fences = 0
            self.provider_checks = 0

        def before_provider_call(self):
            self.provider_checks += 1

        def fence(self, conn):
            self.fences += 1
            if self.fences > 1:  # claim_run owns the first fenced write
                raise pipeline_lease.LeaseLost("taken over before persistence")

    supervisor = Supervisor()
    monkeypatch.setattr(
        pipeline_lease,
        "current_supervisor",
        lambda *, required=False: supervisor,
    )
    before_runs = {
        row[0]
        for row in db.execute(
            "SELECT id FROM run WHERE stage = 'kc-judge'"
        ).fetchall()
    }

    with pytest.raises(pipeline_lease.LeaseLost, match="before persistence"):
        run_judge(
            db,
            runs["kc-statement"],
            runs["task-embedding"],
            runs["task-modality"],
            runs["task-knowledge"],
            FakeModelClient([(response, None, 1)]),
            workers=1,
        )

    new_runs = {
        row[0]
        for row in db.execute(
            "SELECT id FROM run WHERE stage = 'kc-judge'"
        ).fetchall()
    } - before_runs
    assert len(new_runs) == 1
    run_id = new_runs.pop()
    assert supervisor.provider_checks == 1
    assert db.execute(
        "SELECT count(*) FROM run_item WHERE run_id = %s", (run_id,)
    ).fetchone()[0] == 0
    assert harness.fetch_run(db, run_id)["status"] == "running"


def test_a_new_judge_generation_re_judges_what_the_old_one_answered(db):
    task_ids, runs = _input_runs(db, "judge-gen")
    response = json.dumps(
        {
            "verdict_a_to_b": "clear_yes",
            "reason_a_to_b": "Same claim.",
            "verdict_b_to_a": "clear_yes",
            "reason_b_to_a": "Same claim.",
        }
    )
    run_args = (
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
    )

    first = run_judge(db, *run_args, FakeModelClient([(response, None, 1)]), workers=1)
    assert first["ok"] == 1

    # The same generation never re-asks an answered pair.
    again = run_judge(db, *run_args, FakeModelClient([]), workers=1)
    assert again["candidates"] == []
    assert first["candidate_manifest_complete"] is True
    assert again["candidate_manifest_complete"] is True

    # A different model is a new generation: the pair is judged again and
    # both verdicts stand in the ledger.
    class OtherModelClient(FakeModelClient):
        model = "other/model"

    second = run_judge(
        db, *run_args, OtherModelClient([(response, None, 1)]), workers=1
    )
    assert second["ok"] == 1
    assert db.execute(
        "SELECT count(*) FROM kc_verdict WHERE task_a_id = %s AND task_b_id = %s",
        (task_ids[0], task_ids[1]),
    ).fetchone()[0] == 2


def test_changed_upstream_inputs_rejudge_with_same_model_and_prompt(db):
    """A new classification/statement build invalidates old pair verdicts."""
    task_ids, runs = _input_runs(db, "judge-input-version")
    response = json.dumps(
        {
            "verdict_a_to_b": "clear_yes",
            "reason_a_to_b": "Same claim.",
            "verdict_b_to_a": "clear_yes",
            "reason_b_to_a": "Same claim.",
        }
    )
    first = run_judge(
        db,
        runs["kc-statement"],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        FakeModelClient([(response, None, 1)]),
        workers=1,
    )

    artifact_id = db.execute(
        "SELECT artifact_id FROM run_item WHERE run_id = %s LIMIT 1",
        (runs["kc-statement"][0],),
    ).fetchone()[0]
    replacement = harness.claim_run(
        db,
        "kc-statement",
        "fake/model",
        "kc-statement/test",
        "new-sha",
        {
            "gen_runs": [
                db.execute(
                    "SELECT i.run_id FROM task t"
                    " JOIN run_item i ON i.id = t.run_item_id WHERE t.id = %s",
                    (task_ids[0],),
                ).fetchone()[0]
            ]
        },
    )
    for index, task_id in enumerate(task_ids, 1):
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, task_id, response)"
            " VALUES (%s, %s, %s, %s, %s)",
            (
                f"{replacement}-{index:04d}",
                replacement,
                artifact_id,
                task_id,
                json.dumps(
                    {"verdict": "stated", "statement": f"Replacement {index}"}
                ),
            ),
        )
    db.commit()

    second = run_judge(
        db,
        [*runs["kc-statement"], replacement],
        runs["task-embedding"],
        runs["task-modality"],
        runs["task-knowledge"],
        FakeModelClient([(response, None, 1)]),
        workers=1,
    )

    assert first["build_key"] != second["build_key"]
    assert second["ok"] == 1
    assert db.execute(
        "SELECT count(DISTINCT build_key) FROM kc_verdict"
        " WHERE task_a_id = %s AND task_b_id = %s",
        (task_ids[0], task_ids[1]),
    ).fetchone()[0] == 2
