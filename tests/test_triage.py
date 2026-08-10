"""Passages and the triage stage. The transport is faked; the database is real."""

import json
from pathlib import Path

import pytest
from psycopg.types.json import Jsonb

from universe import blocks, harness, passages, triage, triage_report
from universe.blocks import BLOCKER_VERSION, split_blocks
from universe.harness import load_prompt, load_tool
from universe.model_client import ModelClient

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts" / "passage-triage"

BODY = """---
title: "Triage lesson"
---

# Alpha heading

First paragraph, about alpha.

## Beta heading

Second paragraph, about beta.

Third paragraph, still beta.

## Gamma heading

Fourth paragraph, about gamma.
"""

# The blocks BODY splits into, seq 1 to 7.
BLOCK_TEXTS = [
    "# Alpha heading",
    "First paragraph, about alpha.",
    "## Beta heading",
    "Second paragraph, about beta.",
    "Third paragraph, still beta.",
    "## Gamma heading",
    "Fourth paragraph, about gamma.",
]

TEMPLATE = "Read the source.\n\n<source>\n{{body}}\n</source>\n\nNow judge:\n{{passage}}\n"


def synthetic_prompt(template: str = TEMPLATE) -> harness.Prompt:
    return harness.Prompt(ref="passage-triage/vtest", sha="0" * 64, template=template)


def transport(verdicts: dict[str, str], calls: list | None = None):
    """Answers by whichever keyword the passage in focus carries."""

    def send(url, headers, payload, timeout):
        prompt = payload["messages"][0]["content"]
        if calls is not None:
            calls.append(prompt)
        focus = prompt.rsplit("Now judge:", 1)[-1]
        for keyword, verdict in verdicts.items():
            if keyword in focus:
                return {
                    "choices": [{"message": {"content": verdict}, "finish_reason": "stop"}],
                    "usage": {"total_tokens": 10},
                }
        raise ValueError(f"no verdict configured for {focus[:40]!r}")

    return send


@pytest.fixture(scope="session")
def triage_artifact(db) -> str:
    """A source of triage's own, blocked, independent of the other fixtures."""
    source_id = "triage-src-1"
    snapshot_id = f"{source_id}:snap:test"
    artifact_id = f"{snapshot_id}:markdown"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', 'Triage lesson', 'article')"
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


def fake_cuts_run(db, artifact_id: str, cut_list: list[int]) -> str:
    """A passage-cuts run written by hand, so no model is needed to have one."""
    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, 'passage-cuts', 'fake/model', 'passage-cuts/v001',"
        " 'abc', %s, 'done')",
        (run_id, Jsonb({"blocker_version": BLOCKER_VERSION})),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, %s, %s)",
        (f"{run_id}-0001", run_id, artifact_id, json.dumps({"cuts": cut_list})),
    )
    db.commit()
    return run_id


@pytest.fixture(scope="session")
def cuts_runs(db, triage_artifact) -> tuple[str, str]:
    """Two runs that agree on the opening passage and disagree after it."""
    return fake_cuts_run(db, triage_artifact, [3, 6]), fake_cuts_run(db, triage_artifact, [3])


# --- the blocker fixture is enough to check the split assumption -------------


def test_the_fixture_body_blocks_as_expected(db, triage_artifact):
    assert [row["body"] for row in blocks.fetch_blocks(db, triage_artifact)] == BLOCK_TEXTS


# --- materializing ----------------------------------------------------------


def test_materializing_writes_the_ranges_the_cuts_imply(db, cuts_runs):
    first, _ = cuts_runs
    counts = passages.materialize(db, first)
    assert counts == {"passages_new": 3, "passages_existing": 0, "origins_new": 3}

    rows = passages.fetch_passages_for_runs(db, [first])
    assert [(row["first_seq"], row["last_seq"]) for row in rows] == [(1, 2), (3, 5), (6, 7)]
    assert all(row["blocker_version"] == BLOCKER_VERSION for row in rows)
    assert rows[0]["id"].endswith(f":b{BLOCKER_VERSION}:p0001-0002")


def test_materializing_the_same_run_again_writes_nothing(db, cuts_runs):
    first, _ = cuts_runs
    passages.materialize(db, first)
    assert passages.materialize(db, first) == {
        "passages_new": 0,
        "passages_existing": 3,
        "origins_new": 0,
    }


def test_a_range_two_runs_agree_on_is_one_passage_with_two_origins(db, cuts_runs):
    first, second = cuts_runs
    passages.materialize(db, first)
    counts = passages.materialize(db, second)
    # (1,2) is the range both runs drew; (3,7) is this run's alone.
    assert counts == {"passages_new": 1, "passages_existing": 1, "origins_new": 2}

    rows = passages.fetch_passages_for_runs(db, [first, second])
    assert [(row["first_seq"], row["last_seq"]) for row in rows] == [
        (1, 2),
        (3, 5),
        (3, 7),
        (6, 7),
    ]
    assert len({row["id"] for row in rows}) == 4
    # Five ranges went in, four passages came out: one is the dedup.
    assert passages.count_ranges(db, [first, second]) == 5

    shared = rows[0]["id"]
    origins = db.execute(
        "SELECT run_id FROM passage_origin WHERE passage_id = %s ORDER BY run_id", (shared,)
    ).fetchall()
    assert [row[0] for row in origins] == sorted([first, second])


def test_materializing_refuses_a_run_that_is_not_about_cuts(db, triage_artifact):
    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'something-else', 'fake/model', 'x/v001', 'abc', 'done')",
        (run_id,),
    )
    db.commit()
    with pytest.raises(SystemExit, match="not passage-cuts"):
        passages.materialize(db, run_id)


def test_materializing_refuses_a_missing_run(db):
    with pytest.raises(SystemExit, match="no run"):
        passages.materialize(db, "r9999")


def test_a_failed_cuts_item_is_a_clear_error(db, triage_artifact):
    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'passage-cuts', 'fake/model', 'passage-cuts/v001', 'abc', 'failed')",
        (run_id,),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, error)"
        " VALUES (%s, %s, %s, 'HTTP 502: upstream said no')",
        (f"{run_id}-0001", run_id, triage_artifact),
    )
    db.commit()
    with pytest.raises(SystemExit, match="failed and has no cuts"):
        passages.materialize(db, run_id)


# --- the text a model reads -------------------------------------------------


def test_source_text_is_the_blocks_with_no_tags_and_no_front_matter(db, triage_artifact):
    text = passages.source_text(db, triage_artifact)
    assert text == "\n\n".join(BLOCK_TEXTS)
    assert "<block" not in text and "title:" not in text


def test_passage_text_is_only_the_blocks_of_its_range(db, cuts_runs):
    first, _ = cuts_runs
    passages.materialize(db, first)
    middle = passages.fetch_passages_for_runs(db, [first])[1]
    assert passages.passage_text(db, middle) == "\n\n".join(BLOCK_TEXTS[2:5])
    assert "<block" not in passages.passage_text(db, middle)


# --- rendering the prompt ---------------------------------------------------


def test_render_fields_fills_every_placeholder():
    rendered = synthetic_prompt().render_fields({"body": "SOURCE", "passage": "FOCUS"})
    assert "<source>\nSOURCE\n</source>" in rendered
    assert rendered.endswith("Now judge:\nFOCUS\n")
    assert "{{" not in rendered


def test_render_refuses_a_placeholder_with_no_field():
    with pytest.raises(SystemExit, match="no value for passage"):
        synthetic_prompt().render("SOURCE")


def test_a_field_value_that_looks_like_a_placeholder_is_content():
    """One pass over the template: what a field carries is never re-read."""
    rendered = synthetic_prompt().render_fields({"body": "{{passage}}", "passage": "FOCUS"})
    assert "<source>\n{{passage}}\n</source>" in rendered


def test_current_prompt_defines_refine_without_preselecting_removals():
    prompt = load_prompt("passage-triage", "v003")
    assert "content that should be removed" in prompt.template
    assert "{{body}}" in prompt.template and "{{passage}}" in prompt.template
    assert "at least two" not in prompt.template
    assert "non-empty" not in prompt.template


def test_current_triage_tools_report_only_the_verdict():
    regular = load_tool(str(PROMPTS_DIR / "tool-v003.json"))
    regular_function = regular["tools"][0]["function"]
    regular_properties = regular_function["parameters"]["properties"]
    assert set(regular_properties) == {"verdict"}
    assert regular_properties["verdict"]["enum"] == [
        "keep",
        "drop",
        "refine",
        "unknown",
    ]

    atomic = load_tool(str(PROMPTS_DIR / "tool-v003-atomic.json"))
    atomic_properties = atomic["tools"][0]["function"]["parameters"]["properties"]
    assert set(atomic_properties) == {"verdict"}
    assert atomic_properties["verdict"]["enum"] == ["keep", "drop", "unknown"]


# --- targets ----------------------------------------------------------------


def test_every_passage_of_an_artifact_gets_the_same_body_byte_for_byte(db, cuts_runs):
    first, second = cuts_runs
    for run_id in cuts_runs:
        passages.materialize(db, run_id)
    rows = passages.fetch_passages_for_runs(db, [first, second])
    targets = triage.build_targets(db, rows)

    assert len(targets) == len(rows)
    assert len({target.body for target in targets}) == 1  # what the prefix cache needs
    assert targets[0].body == passages.source_text(db, targets[0].artifact_id)
    assert [target.passage_id for target in targets] == [row["id"] for row in rows]
    assert targets[0].source_id == "triage-src-1"
    assert targets[0].extra_fields == {"passage": "\n\n".join(BLOCK_TEXTS[0:2])}
    assert targets[1].extra_fields == {"passage": "\n\n".join(BLOCK_TEXTS[2:5])}


def test_a_revised_passage_target_uses_the_revision_body_and_identity(db, cuts_runs):
    first, _ = cuts_runs
    passages.materialize(db, first)
    rows = passages.fetch_passages_for_runs(db, [first])
    revised = {
        rows[0]["id"]: {
            "body": "Refined alpha passage.",
            "revision_id": "revision-test-id",
        }
    }

    targets = triage.build_targets(db, rows, revised)

    assert targets[0].extra_fields == {"passage": "Refined alpha passage."}
    assert targets[0].passage_revision_id == "revision-test-id"
    assert targets[1].extra_fields == {"passage": "\n\n".join(BLOCK_TEXTS[2:5])}
    assert targets[1].passage_revision_id is None


# --- the run ----------------------------------------------------------------


@pytest.fixture
def triage_run(db, cuts_runs) -> str:
    """One triage run over every passage the two cuts runs produced."""
    for run_id in cuts_runs:
        passages.materialize(db, run_id)
    rows = passages.fetch_passages_for_runs(db, list(cuts_runs))
    client = ModelClient(
        "fake/model",
        api_base="https://example.invalid/v1",
        transport=transport({"alpha": '{"verdict": "keep"}', "beta": '{"verdict": "keep"}',
                             "gamma": '{"verdict": "drop"}'}),
    )
    summary = harness.execute(db, synthetic_prompt(), client, triage.build_targets(db, rows))
    assert summary["failed"] == 0
    return summary["run_id"]


def test_a_run_item_records_the_passage_it_was_about(db, triage_run, cuts_runs):
    items = harness.fetch_items(db, triage_run)
    expected = [row["id"] for row in passages.fetch_passages_for_runs(db, list(cuts_runs))]
    assert [item["passage_id"] for item in items] == expected
    assert all(item["error"] is None for item in items)


def test_workers_are_bounded_by_the_argument(db, cuts_runs):
    """One worker still writes every item, in order."""
    for run_id in cuts_runs:
        passages.materialize(db, run_id)
    rows = passages.fetch_passages_for_runs(db, list(cuts_runs))
    client = ModelClient(
        "fake/model",
        api_base="https://example.invalid/v1",
        transport=transport({"paragraph": '{"verdict": "keep"}', "heading": '{"verdict": "keep"}'}),
    )
    summary = harness.execute(
        db, synthetic_prompt(), client, triage.build_targets(db, rows), workers=1
    )
    assert summary["ok"] == len(rows) and summary["failed"] == 0


# --- reading it back --------------------------------------------------------


def test_the_report_puts_a_row_per_passage_and_a_column_per_run(db, triage_run, tmp_path):
    path = triage_report.write_report(db, [triage_run], tmp_path)
    text = path.read_text()

    assert path.name == f"passage-triage-{triage_run}.md"
    assert f"| passage | {triage_run} |" in text
    assert "| 1-2 # Alpha heading |" in text
    assert "| keep | 3 |" in text and "| drop | 1 |" in text
    # The appendix carries the passages in full, verdicts repeated in the title.
    assert f"### blocks 3 to 5 ({triage_run} keep)" in text
    assert "Third paragraph, still beta." in text


def test_the_report_refuses_a_run_that_is_not_about_passages(db, triage_artifact, tmp_path):
    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'passage-triage', 'fake/model', 'passage-triage/v001', 'abc', 'done')",
        (run_id,),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, %s, '{\"verdict\": \"keep\"}')",
        (f"{run_id}-0001", run_id, "triage-src-1:snap:test:markdown"),
    )
    db.commit()
    with pytest.raises(SystemExit, match="not a triage run"):
        triage_report.write_report(db, [run_id], tmp_path)


def test_an_unusable_response_shows_as_itself_not_as_a_verdict():
    assert triage_report.verdict_of({"error": None, "response": '{"verdict": "keep"}'}) == "keep"
    assert triage_report.verdict_of({"error": "boom", "response": None}) == "error"
    assert triage_report.verdict_of({"error": None, "response": "not json"}) == "unparseable"
    assert triage_report.verdict_of({"error": None, "response": '{"cuts": [1]}'}) == "unparseable"


@pytest.mark.parametrize("verdict", ["keep", "drop", "refine", "unknown"])
def test_cleanup_verdict_accepts_only_the_four_current_decisions(verdict):
    item = {"error": None, "response": json.dumps({"verdict": verdict})}
    assert triage.cleanup_verdict_of(item) == verdict


def test_cleanup_verdict_rejects_legacy_or_unknown_values():
    for verdict in ("not_filler", "filler", "something_else"):
        item = {"error": None, "response": json.dumps({"verdict": verdict})}
        assert triage.cleanup_verdict_of(item) == "unparseable"
