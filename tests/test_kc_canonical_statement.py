"""Canonical statements attach to exact composite snapshots."""

import json

from universe import defaults, harness
from universe.kc_canonical_statement import (
    canonicalization_of,
    fetch_current_canonicalizations,
    run_canonicalization,
    tasks_markup,
)


class FakeClient:
    model = defaults.STAGE_DEFAULTS["kc-canonical-statement"]["model"]
    params = {}

    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete(self, prompt):
        self.calls.append(prompt)
        return json.dumps(self.response), {"total_tokens": 12}, 7


def test_parser_keeps_stated_and_unsure_distinct():
    assert canonicalization_of(
        {"response": '{"verdict":"stated","statement":" Shared rule. "}', "error": None}
    ) == {"verdict": "stated", "statement": "Shared rule."}
    assert canonicalization_of(
        {"response": '{"verdict":"unsure","reason":"Not enough evidence."}', "error": None}
    ) == {"verdict": "unsure", "reason": "Not enough evidence."}
    assert canonicalization_of(
        {"response": '{"verdict":"stated"}', "error": None}
    ) == "unparseable"
    assert canonicalization_of({"response": None, "error": "timeout"}) == "error"


def test_tasks_markup_escapes_member_evidence():
    markup = tasks_markup(
        [{"task": "When is x < y?", "answer": "When x & y differ."}]
    )
    assert "<task>When is x &lt; y?</task>" in markup
    assert "<answer>When x &amp; y differ.</answer>" in markup
    assert "knowledge_statement" not in markup


def _seed_group(db):
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES ('canonical-source', '{\"kind\":\"test\"}', 'Canonical', 'article')"
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES ('canonical-snapshot', 'canonical-source', 'hash', 'ok')"
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES ('canonical-artifact', 'canonical-snapshot', 'markdown', 'test', 'Body')"
    )
    generation = harness.claim_run(
        db, "task-generation", "fake/model", "task-generation/test", "sha", {}
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, 'canonical-artifact', '{}')",
        (f"{generation}-0001", generation),
    )
    db.execute(
        "INSERT INTO passage (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES ('canonical-passage', 'canonical-artifact', 'test', 1, 1)"
    )
    for index in (1, 2):
        db.execute(
            "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
            " VALUES (%s, %s, 'canonical-passage', %s, %s, %s)",
            (
                f"canonical-task-{index}",
                f"{generation}-0001",
                index,
                f"Question {index}",
                f"Answer {index}",
            ),
        )
    db.execute("INSERT INTO kc_grouping (id) VALUES ('canonical-grouping')")
    db.execute(
        "INSERT INTO kc_group (grouping_id, id)"
        " VALUES ('canonical-grouping', 'canonical-group')"
    )
    db.execute(
        "INSERT INTO kc_group_member (grouping_id, group_id, task_id) VALUES"
        " ('canonical-grouping', 'canonical-group', 'canonical-task-1'),"
        " ('canonical-grouping', 'canonical-group', 'canonical-task-2')"
    )
    db.commit()


def test_run_persists_snapshot_identity_and_reuses_usable_result(db):
    _seed_group(db)
    client = FakeClient(
        {"verdict": "stated", "statement": "The two answers follow one shared rule."}
    )

    first = run_canonicalization(db, "canonical-grouping", client, workers=1)

    assert first["status"] == "done"
    assert len(client.calls) == 1
    assert "<task>Question 1</task>" in client.calls[0]
    assert db.execute(
        "SELECT grouping_id, group_id FROM kc_canonicalization"
        " WHERE run_item_id = %s",
        (f"{first['run_id']}-0001",),
    ).fetchone() == ("canonical-grouping", "canonical-group")
    assert fetch_current_canonicalizations(db, "canonical-grouping") == {
        "canonical-group": {
            "verdict": "stated",
            "statement": "The two answers follow one shared rule.",
        }
    }

    second = run_canonicalization(db, "canonical-grouping", client, workers=1)
    assert second["status"] == "unchanged"
    assert second["run_id"] is None
    assert len(client.calls) == 1
