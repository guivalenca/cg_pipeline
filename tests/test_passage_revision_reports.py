"""Reports render the exact raw or revised passage state each item read."""

import json

import pytest
from psycopg.types.json import Jsonb

from universe import (
    blocks,
    harness,
    passage_refine,
    passage_report,
    passages,
    triage_report,
)
from universe.blocks import BLOCKER_VERSION


BODY = "# Report lesson\n\nKept paragraph.\n\nRemoved paragraph.\n"


def model_run_item(
    db,
    *,
    stage: str,
    passage: dict,
    response: dict,
    revision_id: str | None = None,
    params: dict | None = None,
) -> tuple[str, dict]:
    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, %s, 'fake/model', %s, 'abc', %s, 'done')",
        (run_id, stage, f"{stage}/vtest", Jsonb(params or {})),
    )
    db.execute(
        "INSERT INTO run_item"
        " (id, run_id, artifact_id, passage_id, passage_revision_id, response)"
        " VALUES (%s, %s, %s, %s, %s, %s)",
        (
            f"{run_id}-0001",
            run_id,
            passage["artifact_id"],
            passage["id"],
            revision_id,
            json.dumps(response),
        ),
    )
    db.commit()
    return run_id, harness.fetch_items(db, run_id)[0]


@pytest.fixture(scope="module")
def report_states(db) -> dict:
    source_id = "passage-report-state-src"
    snapshot_id = f"{source_id}:snapshot"
    artifact_id = f"{snapshot_id}:markdown"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', 'Report states', 'article')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'report-state-hash', 'ok')",
        (snapshot_id, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', %s)",
        (artifact_id, snapshot_id, BODY),
    )
    db.commit()
    split = blocks.split_blocks(BODY)
    blocks.store_blocks(db, artifact_id, split)
    # A deliberately different historical ledger proves passage_report reads
    # the cuts run's stamped version rather than the process-global version.
    blocks.store_blocks(db, artifact_id, split[:1], version="2")

    passage_id = passages.passage_id(artifact_id, 1, 3, BLOCKER_VERSION)
    passage = {
        "id": passage_id,
        "artifact_id": artifact_id,
        "blocker_version": BLOCKER_VERSION,
        "first_seq": 1,
        "last_seq": 3,
    }
    db.execute(
        "INSERT INTO passage"
        " (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, %s, 1, 3)",
        (passage_id, artifact_id, BLOCKER_VERSION),
    )
    db.commit()

    _, refine_item = model_run_item(
        db,
        stage="passage-refine",
        passage=passage,
        response={"drop_elements": [3]},
    )
    revision = passage_refine.materialize_revision(
        db,
        passage=passage,
        refine_item=refine_item,
        parent_revision_id=None,
    )

    triage_raw, _ = model_run_item(
        db,
        stage="passage-triage",
        passage=passage,
        response={"verdict": "keep"},
    )
    triage_revised, _ = model_run_item(
        db,
        stage="passage-triage",
        passage=passage,
        revision_id=revision["id"],
        response={"verdict": "keep"},
    )
    cuts_run = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, 'passage-cuts', 'fake/model', 'passage-cuts/vtest',"
        " 'abc', 'done')",
        (cuts_run,),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, %s, '{\"cuts\": []}')",
        (f"{cuts_run}-0001", cuts_run, artifact_id),
    )
    db.commit()
    return {
        "passage": passage,
        "revision": revision,
        "triage_runs": [triage_raw, triage_revised],
        "cuts_run": cuts_run,
    }


def test_shared_state_renderer_returns_exact_raw_and_revised_bodies(db, report_states):
    passage = report_states["passage"]
    revision = report_states["revision"]

    assert passage_report.passage_state_text(db, passage, None) == BODY.rstrip()
    assert passage_report.passage_state_text(db, passage, revision["id"]) == (
        "# Report lesson\n\nKept paragraph."
    )


def test_triage_report_separates_raw_and_revised_states(db, report_states):
    text = triage_report.render_runs(db, report_states["triage_runs"])

    assert text.count("Removed paragraph.") == 1
    assert text.count("Kept paragraph.") == 2
    assert f"revision: `{report_states['revision']['id']}`" in text
    assert all(run_id in text for run_id in report_states["triage_runs"])


def test_passage_cuts_report_uses_the_run_stamped_blocker_version(db, report_states):
    text = passage_report.render_runs(db, [report_states["cuts_run"]])

    assert "- blocks: 1" in text
    assert "# Report lesson" in text
    assert "Kept paragraph." not in text
