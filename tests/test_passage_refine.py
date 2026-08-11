"""Element-addressed passage revisions and their immutable lineage."""

import json

import pytest

from universe import blocks, harness, passage_refine, passages
from universe.blocks import BLOCKER_VERSION


BODY = """# Lesson

Useful explanation.

Remove this aside.

![Unresolved diagram](https://example.invalid/diagram.png)
"""


@pytest.fixture(scope="session")
def refinement_passage(db) -> dict:
    source_id = "passage-refine-src"
    snapshot_id = f"{source_id}:snapshot"
    artifact_id = f"{snapshot_id}:markdown"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', 'Refinement', 'article')"
        " ON CONFLICT DO NOTHING",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'refinement-hash', 'ok') ON CONFLICT DO NOTHING",
        (snapshot_id, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', %s) ON CONFLICT DO NOTHING",
        (artifact_id, snapshot_id, BODY),
    )
    db.commit()
    blocks.store_blocks(db, artifact_id, blocks.split_blocks(BODY))
    element_count = blocks.count_blocks(db, artifact_id)
    passage_id = passages.passage_id(
        artifact_id, 1, element_count, BLOCKER_VERSION
    )
    db.execute(
        "INSERT INTO passage"
        " (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, %s, 1, %s) ON CONFLICT DO NOTHING",
        (passage_id, artifact_id, BLOCKER_VERSION, element_count),
    )
    db.commit()
    return {
        "id": passage_id,
        "artifact_id": artifact_id,
        "blocker_version": BLOCKER_VERSION,
        "first_seq": 1,
        "last_seq": element_count,
    }


def refine_item(
    db,
    passage: dict,
    drop_elements,
    *,
    parent_revision_id: str | None = None,
    stage: str = "passage-refine",
) -> dict:
    run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, status)"
        " VALUES (%s, %s, 'fake/model', %s, 'abc', 'done')",
        (run_id, stage, f"{stage}/vtest"),
    )
    item_id = f"{run_id}-0001"
    db.execute(
        "INSERT INTO run_item"
        " (id, run_id, artifact_id, passage_id, passage_revision_id, response)"
        " VALUES (%s, %s, %s, %s, %s, %s)",
        (
            item_id,
            run_id,
            passage["artifact_id"],
            passage["id"],
            parent_revision_id,
            json.dumps({"drop_elements": drop_elements}),
        ),
    )
    db.commit()
    return harness.fetch_items(db, run_id)[0]


def test_raw_state_is_an_ordered_numbered_element_sequence(db, refinement_passage):
    current = passage_refine.state(db, refinement_passage)

    assert [element["seq"] for element in current["elements"]] == [1, 2, 3, 4]
    assert current["elements"][-1]["image_state"] == "unresolved"
    assert current["body"] == "\n\n".join(
        element["body"] for element in current["elements"]
    )
    numbered = passage_refine.numbered_elements(current["elements"])
    assert numbered.count("<element ") == 4
    assert 'n="4" kind="image" image_state="unresolved"' in numbered


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ('{"drop_elements": [1, 1]}', "duplicates"),
        ('{"drop_elements": [true]}', "list of integers"),
        ('{"drop_elements": "1"}', "list of integers"),
        ('{"drop_elements": [], "extra": 1}', "only drop_elements"),
        ("not-json", "valid JSON"),
    ],
)
def test_refine_response_parser_rejects_ambiguous_shapes(response, message):
    with pytest.raises(passage_refine.RefinementError, match=message):
        passage_refine.parse_drop_elements(response)


def test_plan_validation_enforces_application_invariants(db, refinement_passage):
    elements = passage_refine.raw_elements(db, refinement_passage)

    assert passage_refine.validate_plan(elements, []) == []
    with pytest.raises(passage_refine.RefinementError, match="outside passage"):
        passage_refine.validate_plan(elements, [5])
    with pytest.raises(passage_refine.RefinementError, match="every passage element"):
        passage_refine.validate_plan(elements, [1, 2, 3, 4])
    with pytest.raises(passage_refine.RefinementError, match="unresolved image"):
        passage_refine.validate_plan(elements, [4])
    enriched = [*elements[:-1], {**elements[-1], "image_state": "enriched"}]
    assert passage_refine.validate_plan(enriched, [4]) == [enriched[3]]
    with pytest.raises(passage_refine.RefinementError, match="atomic passage"):
        passage_refine.validate_plan(elements[:1], [1])


def test_revision_materialization_is_idempotent_and_element_addressed(
    db, refinement_passage
):
    item = refine_item(db, refinement_passage, [3])

    revision = passage_refine.materialize_revision(
        db,
        passage=refinement_passage,
        refine_item=item,
        parent_revision_id=None,
    )
    repeated = passage_refine.materialize_revision(
        db,
        passage=refinement_passage,
        refine_item=item,
        parent_revision_id=None,
    )

    assert repeated == revision
    assert revision["iteration"] == 1
    assert "Remove this aside." not in revision["body"]
    assert "Useful explanation." in revision["body"]
    assert db.execute(
        "SELECT count(*) FROM passage_revision WHERE refine_run_item_id = %s",
        (item["id"],),
    ).fetchone()[0] == 1
    dropped = db.execute(
        "SELECT block_id FROM passage_revision_drop WHERE revision_id = %s",
        (revision["id"],),
    ).fetchall()
    assert dropped == [(passage_refine.raw_elements(db, refinement_passage)[2]["id"],)]


def test_child_revision_numbers_only_the_elements_its_parent_retained(
    db, refinement_passage
):
    first_item = refine_item(db, refinement_passage, [2])
    first = passage_refine.materialize_revision(
        db,
        passage=refinement_passage,
        refine_item=first_item,
        parent_revision_id=None,
    )
    # After the first removal the local sequence is raw elements 1, 3, 4.
    # Local element 2 therefore maps to raw element 3, not raw element 2.
    second_item = refine_item(
        db, refinement_passage, [2], parent_revision_id=first["id"]
    )
    second = passage_refine.materialize_revision(
        db,
        passage=refinement_passage,
        refine_item=second_item,
        parent_revision_id=first["id"],
    )

    current = passage_refine.state(db, refinement_passage, second["id"])
    assert second["iteration"] == 2
    assert [element["seq"] for element in current["elements"]] == [1, 4]
    assert current["body"] == "# Lesson\n\n" + current["elements"][-1]["body"]
    assert passage_refine.dropped_block_ids(db, second["id"]) == {
        passage_refine.raw_elements(db, refinement_passage)[1]["id"],
        passage_refine.raw_elements(db, refinement_passage)[2]["id"],
    }


def test_empty_plan_records_no_child_and_preserves_the_parent(db, refinement_passage):
    item = refine_item(db, refinement_passage, [])

    assert passage_refine.materialize_revision(
        db,
        passage=refinement_passage,
        refine_item=item,
        parent_revision_id=None,
    ) is None
    assert db.execute(
        "SELECT count(*) FROM passage_revision WHERE refine_run_item_id = %s",
        (item["id"],),
    ).fetchone()[0] == 0


def test_only_a_stamped_passage_refine_item_can_create_a_revision(
    db, refinement_passage
):
    item = refine_item(db, refinement_passage, [2], stage="passage-triage")

    with pytest.raises(passage_refine.RefinementError, match="not from passage-refine"):
        passage_refine.materialize_revision(
            db,
            passage=refinement_passage,
            refine_item=item,
            parent_revision_id=None,
        )
