"""The triage/refine loop over immutable passage element states."""

import json

import pytest
from psycopg.types.json import Jsonb

from universe import blocks, harness, passage_cleanup, passages
from universe.blocks import BLOCKER_VERSION
from universe.model_client import ModelClient


TRIAGE_PROMPT = harness.Prompt(
    ref="passage-triage/vtest",
    sha="1" * 64,
    template="<source>\n{{body}}\n</source>\n<passage>\n{{passage}}\n</passage>",
)
REFINE_PROMPT = harness.Prompt(
    ref="passage-refine/vtest",
    sha="2" * 64,
    template="<passage>\n{{passage}}\n</passage>",
)


def source_with_cuts(db, marker: str, body: str, cuts: list[int]) -> str:
    source_id = f"cleanup-{marker}"
    snapshot_id = f"{source_id}:snapshot"
    artifact_id = f"{snapshot_id}:markdown"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', %s, 'article')",
        (source_id, marker),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, %s, 'ok')",
        (snapshot_id, source_id, f"hash-{marker}"),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', %s)",
        (artifact_id, snapshot_id, body),
    )
    db.commit()
    blocks.store_blocks(db, artifact_id, blocks.split_blocks(body))

    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, 'passage-cuts', 'fake/model', 'passage-cuts/vtest',"
        " 'abc', %s, 'done')",
        (run_id, Jsonb({"blocker_version": BLOCKER_VERSION})),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, %s, %s)",
        (f"{run_id}-0001", run_id, artifact_id, json.dumps({"cuts": cuts})),
    )
    db.commit()
    return run_id


def fake_client(transport) -> ModelClient:
    return ModelClient(
        "fake/model",
        api_base="https://example.invalid/v1",
        transport=transport,
    )


def response(content: str) -> dict:
    return {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 10},
    }


def passage_focus(payload: dict) -> str:
    prompt = payload["messages"][0]["content"]
    return prompt.rsplit("<passage>", 1)[1].split("</passage>", 1)[0]


def test_cleanup_loops_refinement_to_a_terminal_state_and_writes_canonical_markdown(db):
    body = """# Keep passage

Keep this explanation.

# Refine passage

Useful refined content.

Remove me.

# Drop passage

Drop me.

# Unknown passage

Unclear but preserved.

Atomic survivor.
"""
    cuts_run = source_with_cuts(db, "full-loop", body, [3, 6, 8, 10])
    triage_calls = []
    refine_calls = []

    def triage_transport(url, headers, payload, timeout):
        focus = passage_focus(payload)
        triage_calls.append(focus)
        if "Remove me." in focus:
            verdict = "refine"
        elif "Drop passage" in focus:
            verdict = "drop"
        elif "Unknown passage" in focus:
            verdict = "unknown"
        else:
            verdict = "keep"
        return response(json.dumps({"verdict": verdict}))

    def refine_transport(url, headers, payload, timeout):
        focus = passage_focus(payload)
        refine_calls.append(focus)
        assert '<element n="3" kind="paragraph">\nRemove me.' in focus
        return response(json.dumps({"drop_elements": [3]}))

    result = passage_cleanup.run_cleanup(
        db,
        cuts_run_id=cuts_run,
        model="fake/model",
        triage_prompt=TRIAGE_PROMPT,
        refine_prompt=REFINE_PROMPT,
        triage_client=fake_client(triage_transport),
        atomic_triage_client=fake_client(triage_transport),
        refine_client=fake_client(refine_transport),
        workers=2,
    )

    assert result["status"] == "done"
    assert result["passages"] == 5
    assert len(result["artifacts"]) == 1
    assert len(refine_calls) == 1
    # Raw refine state and its child are separate triage calls.
    assert sum("Refine passage" in focus for focus in triage_calls) == 2

    cleanup = db.execute(
        "SELECT status, run_ids FROM passage_cleanup WHERE id = %s",
        (result["cleanup_id"],),
    ).fetchone()
    assert cleanup[0] == "done"
    assert len(cleanup[1]) == 4  # composite + atomic + refine + child triage

    outcomes = db.execute(
        "SELECT p.first_seq, r.verdict, r.passage_revision_id"
        " FROM passage_cleanup_result r JOIN passage p ON p.id = r.passage_id"
        " WHERE r.cleanup_id = %s ORDER BY p.first_seq",
        (result["cleanup_id"],),
    ).fetchall()
    assert [row[:2] for row in outcomes] == [
        (1, "keep"),
        (3, "keep"),
        (6, "drop"),
        (8, "unknown"),
        (10, "keep"),
    ]
    assert outcomes[1][2] is not None
    assert all(row[2] is None for row in outcomes[:1] + outcomes[2:])

    canonical = db.execute(
        "SELECT body, metadata FROM artifact WHERE id = %s",
        (result["artifacts"][0],),
    ).fetchone()
    assert "Keep this explanation." in canonical[0]
    assert "Useful refined content." in canonical[0]
    assert "Unclear but preserved." in canonical[0]
    assert "Atomic survivor." in canonical[0]
    assert "Remove me." not in canonical[0]
    assert "Drop passage" not in canonical[0]
    assert len(canonical[1]["unknown_passage_ids"]) == 1

    # The second triage call is stamped with the exact revision it read.
    assert db.execute(
        "SELECT count(*) FROM run_item i JOIN run r ON r.id = i.run_id"
        " WHERE r.stage = 'passage-triage' AND i.passage_revision_id = %s",
        (outcomes[1][2],),
    ).fetchone()[0] == 1


def test_unresolved_image_does_not_protect_neighboring_text_from_triage(db):
    body = """Visual context.

![Unavailable](https://example.invalid/unavailable.png)
"""
    cuts_run = source_with_cuts(db, "unresolved", body, [])
    calls = []

    def drop_passage(url, headers, payload, timeout):
        calls.append(payload)
        return response('{"verdict":"drop"}')

    client = fake_client(drop_passage)
    result = passage_cleanup.run_cleanup(
        db,
        cuts_run_id=cuts_run,
        model="fake/model",
        triage_prompt=TRIAGE_PROMPT,
        refine_prompt=REFINE_PROMPT,
        triage_client=client,
        atomic_triage_client=client,
        refine_client=client,
    )

    assert result["status"] == "done"
    assert len(calls) == 1
    outcome = db.execute(
        "SELECT verdict, decision_run_item_id FROM passage_cleanup_result"
        " WHERE cleanup_id = %s",
        (result["cleanup_id"],),
    ).fetchone()
    assert outcome[0] == "drop"
    assert outcome[1] is not None
    canonical = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (result["artifacts"][0],)
    ).fetchone()[0]
    assert "![Unavailable]" not in canonical
    assert "Visual context." not in canonical


def test_enriched_image_can_be_discarded_by_a_cleanup_drop_verdict(db):
    body = """# Comparative evidence

![Table continuation](/api/source-assets/table-page-2)

Image summary: This page completes a comparison table begun on the prior page.

OCR: Concurrent processes mapped to the applicable technique families.
"""
    cuts_run = source_with_cuts(db, "enriched-image", body, [])

    def drop_passage(url, headers, payload, timeout):
        return response('{"verdict":"drop"}')

    client = fake_client(drop_passage)
    result = passage_cleanup.run_cleanup(
        db,
        cuts_run_id=cuts_run,
        model="fake/model",
        triage_prompt=TRIAGE_PROMPT,
        refine_prompt=REFINE_PROMPT,
        triage_client=client,
        atomic_triage_client=client,
        refine_client=client,
    )

    assert result["status"] == "done"
    assert db.execute(
        "SELECT verdict, policy_reason FROM passage_cleanup_result"
        " WHERE cleanup_id = %s",
        (result["cleanup_id"],),
    ).fetchone() == ("drop", None)
    canonical = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (result["artifacts"][0],)
    ).fetchone()[0]
    assert "![Table continuation]" not in canonical
    assert "Concurrent processes" not in canonical


def test_refine_that_selects_every_element_becomes_a_terminal_drop(db):
    body = "# Promotional shell\n\nAuthor biography.\n\nNewsletter CTA.\n"
    cuts_run = source_with_cuts(db, "full-refine-drop", body, [])

    def triage_transport(url, headers, payload, timeout):
        return response('{"verdict":"refine"}')

    def refine_transport(url, headers, payload, timeout):
        return response('{"drop_elements":[1,2,3]}')

    result = passage_cleanup.run_cleanup(
        db,
        cuts_run_id=cuts_run,
        model="fake/model",
        triage_prompt=TRIAGE_PROMPT,
        refine_prompt=REFINE_PROMPT,
        triage_client=fake_client(triage_transport),
        atomic_triage_client=fake_client(triage_transport),
        refine_client=fake_client(refine_transport),
    )

    assert result["status"] == "done"
    outcome = db.execute(
        "SELECT verdict, passage_revision_id, decision_run_item_id"
        " FROM passage_cleanup_result WHERE cleanup_id = %s",
        (result["cleanup_id"],),
    ).fetchone()
    assert outcome[0:2] == ("drop", None)
    assert outcome[2] is not None
    canonical = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (result["artifacts"][0],)
    ).fetchone()[0]
    assert canonical == "\n"


def test_empty_refinement_plan_terminates_as_unknown_without_an_identical_child(db):
    body = "# Mixed passage\n\nUseful content.\n\nMaybe removable.\n"
    cuts_run = source_with_cuts(db, "empty-refine", body, [])

    def triage_transport(url, headers, payload, timeout):
        return response('{"verdict":"refine"}')

    def refine_transport(url, headers, payload, timeout):
        return response('{"drop_elements":[]}')

    result = passage_cleanup.run_cleanup(
        db,
        cuts_run_id=cuts_run,
        model="fake/model",
        triage_prompt=TRIAGE_PROMPT,
        refine_prompt=REFINE_PROMPT,
        triage_client=fake_client(triage_transport),
        atomic_triage_client=fake_client(triage_transport),
        refine_client=fake_client(refine_transport),
    )

    assert result["status"] == "done"
    outcome = db.execute(
        "SELECT verdict, passage_revision_id, decision_run_item_id"
        " FROM passage_cleanup_result WHERE cleanup_id = %s",
        (result["cleanup_id"],),
    ).fetchone()
    assert outcome[0:2] == ("unknown", None)
    assert outcome[2] is not None
    assert db.execute(
        "SELECT count(*) FROM passage_revision WHERE passage_id IN ("
        " SELECT passage_id FROM passage_cleanup_result WHERE cleanup_id = %s)",
        (result["cleanup_id"],),
    ).fetchone()[0] == 0


def test_atomic_passage_cannot_enter_refinement_even_if_transport_breaks_schema(db):
    cuts_run = source_with_cuts(db, "atomic-refine", "Atomic content.\n", [])

    def unexpected_composite(url, headers, payload, timeout):  # pragma: no cover
        raise AssertionError("atomic passage used the composite triage client")

    def invalid_atomic(url, headers, payload, timeout):
        return response('{"verdict":"refine"}')

    result = passage_cleanup.run_cleanup(
        db,
        cuts_run_id=cuts_run,
        model="fake/model",
        triage_prompt=TRIAGE_PROMPT,
        refine_prompt=REFINE_PROMPT,
        triage_client=fake_client(unexpected_composite),
        atomic_triage_client=fake_client(invalid_atomic),
        refine_client=fake_client(unexpected_composite),
    )

    assert result["status"] == "failed"
    assert "atomic passage" in result["errors"][0]
    assert db.execute(
        "SELECT count(*) FROM passage_cleanup_artifact WHERE cleanup_id = %s",
        (result["cleanup_id"],),
    ).fetchone()[0] == 0
