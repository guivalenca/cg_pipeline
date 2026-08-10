"""Low-cost tracer across enriched images, blocks, cuts and canonical cleanup."""

import json

from psycopg.types.json import Jsonb

from universe import blocks, harness, passage_cleanup, passages
from universe.model_client import ModelClient


TRIAGE_PROMPT = harness.Prompt(
    ref="passage-triage/tracer",
    sha="1" * 64,
    template="<source>\n{{body}}\n</source>\n<passage>\n{{passage}}\n</passage>",
)
REFINE_PROMPT = harness.Prompt(
    ref="passage-refine/tracer",
    sha="2" * 64,
    template="<passage>\n{{passage}}\n</passage>",
)


def _fake_client(transport) -> ModelClient:
    return ModelClient(
        "fake/model",
        api_base="https://example.invalid/v1",
        transport=transport,
    )


def _response(verdict: str) -> dict:
    return {
        "choices": [
            {
                "message": {"content": json.dumps({"verdict": verdict})},
                "finish_reason": "stop",
            }
        ],
        "usage": {"total_tokens": 1},
    }


def _focused_passage(payload: dict) -> str:
    prompt = payload["messages"][0]["content"]
    return prompt.rsplit("<passage>", 1)[1].split("</passage>", 1)[0]


def test_organizational_design_unresolved_svg_does_not_preserve_pre_h1_chrome(db):
    source_id = "source-organizational-design-cleanup-tracer"
    snapshot_id = f"{source_id}:snapshot"
    raw_artifact_id = f"{snapshot_id}:raw"
    enriched_artifact_id = f"{raw_artifact_id}:images"
    enriched_markdown = """# Cookie controls

Accept cookies to continue.

# Organizational Design: A Complete Guide

This explanation remains.

![Retained diagram](/api/source-assets/asset-retained)

Image description: A diagram connects planning to execution.

OCR: Plan → Execute

# Recommended resources

Subscribe to updates.
"""
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Tracer source', 'article')",
        (source_id, Jsonb({"kind": "tracer"})),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'tracer-hash', 'ok')",
        (snapshot_id, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'tracer-raw',"
        " '# Cookie controls\\n\\n![AIHR logo](https://cdn.example/aihr-logo.svg)'),"
        "        (%s, %s, 'markdown', 'article-image-association', %s)",
        (
            raw_artifact_id,
            snapshot_id,
            enriched_artifact_id,
            snapshot_id,
            enriched_markdown,
        ),
    )
    db.execute(
        "UPDATE artifact SET metadata = %s WHERE id = %s",
        (
            Jsonb({"source_markdown_artifact_id": raw_artifact_id}),
            enriched_artifact_id,
        ),
    )
    acquisition_job_id = "acq-organizational-design-cleanup-tracer"
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, artifact_id, finished_at)"
        " VALUES (%s, %s, 'succeeded', 'firecrawl/v2', %s, now())",
        (acquisition_job_id, source_id, raw_artifact_id),
    )
    db.execute(
        "INSERT INTO source_image_candidate"
        " (id, acquisition_job_id, source_id, snapshot_id, markdown_artifact_id,"
        " ordinal, original_url, alt_text, placement, status, failure_code,"
        " diagnostics, finished_at)"
        " VALUES ('candidate-unresolved-tracer', %s, %s, %s, %s, 1,"
        " 'https://cdn.example/aihr-logo.svg', 'AIHR logo', %s, 'failed',"
        " 'image_analysis_unsupported_type', %s, now())",
        (
            acquisition_job_id,
            source_id,
            snapshot_id,
            raw_artifact_id,
            Jsonb({"occurrences": [{"ordinal": 1}]}),
            Jsonb({"category": "unsupported_model_image_type", "mime_type": "image/svg+xml"}),
        ),
    )
    db.commit()

    parsed = blocks.split_blocks(enriched_markdown)
    assert blocks.store_blocks(db, enriched_artifact_id, parsed) == 7
    stored = blocks.fetch_blocks(db, enriched_artifact_id)
    assert [(item["seq"], item["kind"]) for item in stored] == [
        (1, "heading"),
        (2, "paragraph"),
        (3, "heading"),
        (4, "paragraph"),
        (5, "image"),
        (6, "heading"),
        (7, "paragraph"),
    ]
    assert [item["image_state"] for item in stored if item["kind"] == "image"] == [
        "enriched",
    ]

    cuts_run_id = harness.next_run_id(db)
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, 'passage-cuts', 'fake/model', 'passage-cuts/tracer',"
        " 'cuts-sha', %s, 'done')",
        (cuts_run_id, Jsonb({"blocker_version": blocks.BLOCKER_VERSION})),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES (%s, %s, %s, %s)",
        (
            f"{cuts_run_id}-0001",
            cuts_run_id,
            enriched_artifact_id,
            json.dumps({"cuts": [3, 6]}),
        ),
    )
    db.commit()

    materialized = passages.materialize(db, cuts_run_id)
    assert materialized == {
        "passages_new": 3,
        "passages_existing": 0,
        "origins_new": 3,
    }
    assert [
        (item["first_seq"], item["last_seq"])
        for item in passages.fetch_passages_for_runs(db, [cuts_run_id])
    ] == [(1, 2), (3, 5), (6, 7)]

    triaged_passages = []

    def triage_transport(_url, _headers, payload, _timeout):
        focus = _focused_passage(payload)
        triaged_passages.append(focus)
        return _response(
            "drop"
            if "Accept cookies" in focus or "Subscribe to updates." in focus
            else "keep"
        )

    def must_not_refine(_url, _headers, _payload, _timeout):  # pragma: no cover
        raise AssertionError("the tracer does not request refinement")

    result = passage_cleanup.run_cleanup(
        db,
        cuts_run_id=cuts_run_id,
        model="fake/model",
        triage_prompt=TRIAGE_PROMPT,
        refine_prompt=REFINE_PROMPT,
        triage_client=_fake_client(triage_transport),
        atomic_triage_client=_fake_client(triage_transport),
        refine_client=_fake_client(must_not_refine),
        workers=1,
    )

    assert result["status"] == "done"
    assert result["passages"] == 3
    assert len(triaged_passages) == 3
    assert all("Image analysis: unresolved" not in focus for focus in triaged_passages)
    outcomes = db.execute(
        "SELECT p.first_seq, p.last_seq, r.verdict, r.decision_run_item_id"
        " FROM passage_cleanup_result r"
        " JOIN passage p ON p.id = r.passage_id"
        " WHERE r.cleanup_id = %s ORDER BY p.first_seq",
        (result["cleanup_id"],),
    ).fetchall()
    assert [(first, last, verdict) for first, last, verdict, _item in outcomes] == [
        (1, 2, "drop"),
        (3, 5, "keep"),
        (6, 7, "drop"),
    ]
    assert all(outcome[3] is not None for outcome in outcomes)

    canonical_id = result["artifacts"][0]
    canonical_body, metadata, tool = db.execute(
        "SELECT body, metadata, tool FROM artifact WHERE id = %s",
        (canonical_id,),
    ).fetchone()
    assert tool == "passage-cleanup"
    assert "This explanation remains." in canonical_body
    assert "![Retained diagram]" in canonical_body
    assert "Image description: A diagram connects planning to execution." in canonical_body
    assert "OCR: Plan → Execute" in canonical_body
    assert "Cookie controls" not in canonical_body
    assert "Accept cookies" not in canonical_body
    assert "Recommended resources" not in canonical_body
    assert "Subscribe to updates." not in canonical_body
    assert "![Unresolved scan]" not in canonical_body
    assert "Image analysis: unresolved" not in canonical_body
    assert metadata["source_markdown_artifact_id"] == enriched_artifact_id
    assert metadata["unknown_passage_ids"] == []
    ledger = db.execute(
        "SELECT status, failure_code, diagnostics FROM source_image_candidate"
        " WHERE id = 'candidate-unresolved-tracer'"
    ).fetchone()
    assert ledger[0] == "failed"
    assert ledger[1] == "image_analysis_unsupported_type"
    assert ledger[2]["category"] == "unsupported_model_image_type"
    canonical_images = [
        item for item in blocks.split_blocks(canonical_body) if item.kind == "image"
    ]
    assert [item.image_state for item in canonical_images] == ["enriched"]
