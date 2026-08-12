"""Behavior tests for the Canonical Source Markdown publication seam."""

from __future__ import annotations

import uuid

from psycopg.types.json import Jsonb


def test_current_publication_ignores_late_enrichment_of_an_older_snapshot(db):
    """Publication order follows Source snapshots, not late child artifacts."""
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-publication-{marker}"
    old_snapshot = f"snapshot-{marker}-old"
    new_snapshot = f"snapshot-{marker}-new"
    old_markdown = f"artifact-{marker}-old"
    old_enriched = f"{old_markdown}:images"
    new_markdown = f"artifact-{marker}-new"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Publication test', 'article')",
        (source_id, Jsonb({"kind": "url", "value": f"https://example.com/{marker}"})),
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, 'old-hash', 'ok', now()),"
        "        (%s, %s, 'new-hash', 'ok', now() + interval '1 second')",
        (old_snapshot, source_id, new_snapshot, source_id),
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, metadata, created_at)"
        " VALUES (%s, %s, 'markdown', 'firecrawl', '# Old', '{}', now()),"
        "        (%s, %s, 'markdown', 'article-images', '# Old enriched', %s,"
        "         now() + interval '10 seconds'),"
        "        (%s, %s, 'markdown', 'firecrawl', '# New', '{}',"
        "         now() + interval '1 second')",
        (
            old_markdown,
            old_snapshot,
            old_enriched,
            old_snapshot,
            Jsonb({"source_markdown_artifact_id": old_markdown}),
            new_markdown,
            new_snapshot,
        ),
    )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.source_id == source_id
    assert publication.snapshot_id == new_snapshot
    assert publication.artifact_id == new_markdown
    assert publication.content_hash == "new-hash"
    assert publication.body == "# New"
    assert publication.is_previous_attempt is False


def test_current_publication_preserves_last_canonical_during_a_refresh(db):
    """An unfinished strict cleanup cannot publish its intermediate artifact."""
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-refresh-{marker}"
    old_snapshot = f"snapshot-refresh-{marker}-old"
    new_snapshot = f"snapshot-refresh-{marker}-new"
    old_base = f"artifact-refresh-{marker}-old-base"
    old_canonical = f"artifact-refresh-{marker}-old-canonical"
    new_intermediate = f"artifact-refresh-{marker}-new-intermediate"
    old_job = f"acquisition-refresh-{marker}-old"
    new_job = f"acquisition-refresh-{marker}-new"
    cuts_run = f"cuts-refresh-{marker}"
    cleanup_id = f"cleanup-result-{marker}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Refresh test', 'article')",
        (source_id, Jsonb({"kind": "url", "value": f"https://example.com/{marker}"})),
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, 'old-hash', 'ok', now()),"
        "        (%s, %s, 'new-hash', 'ok', now() + interval '1 second')",
        (old_snapshot, source_id, new_snapshot, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body, created_at)"
        " VALUES (%s, %s, 'markdown', 'firecrawl', '# Old raw', now()),"
        "        (%s, %s, 'markdown', 'passage-cleanup', '# Published',"
        "         now() + interval '1 second'),"
        "        (%s, %s, 'markdown', 'firecrawl', '# New intermediate',"
        "         now() + interval '2 second')",
        (
            old_base,
            old_snapshot,
            old_canonical,
            old_snapshot,
            new_intermediate,
            new_snapshot,
        ),
    )
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status, finished_at)"
        " VALUES (%s, 'passage-cuts', 'test/model', 'passage-cuts/v001',"
        " 'sha', 'done', now())",
        (cuts_run,),
    )
    db.execute(
        "INSERT INTO passage_cleanup"
        " (id, cuts_run_id, model, triage_prompt_ref, refine_prompt_ref,"
        "  status, finished_at)"
        " VALUES (%s, %s, 'test/model', 'passage-triage/v005',"
        " 'passage-refine/v002', 'done', now())",
        (cleanup_id, cuts_run),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, artifact_id, diagnostics,"
        "  finished_at, created_at)"
        " VALUES (%s, %s, 'succeeded', 'firecrawl/v2', %s, %s, now(), now()),"
        "        (%s, %s, 'succeeded', 'firecrawl/v2', %s, %s, now(),"
        "         now() + interval '2 second')",
        (
            old_job,
            source_id,
            old_base,
            Jsonb({"pipeline_requires_cleanup": True}),
            new_job,
            source_id,
            new_intermediate,
            Jsonb({"pipeline_requires_cleanup": True}),
        ),
    )
    db.execute(
        "INSERT INTO source_cleanup_job"
        " (id, acquisition_job_id, source_id, source_artifact_id, status,"
        "  cuts_run_id, cleanup_id, canonical_artifact_id, finished_at, created_at)"
        " VALUES (%s, %s, %s, %s, 'succeeded', %s, %s, %s, now(), now()),"
        "        (%s, %s, %s, %s, 'queued', NULL, NULL, NULL, NULL,"
        "         now() + interval '2 second')",
        (
            f"cleanup-job-{marker}-old",
            old_job,
            source_id,
            old_base,
            cuts_run,
            cleanup_id,
            old_canonical,
            f"cleanup-job-{marker}-new",
            new_job,
            source_id,
            new_intermediate,
        ),
    )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.artifact_id == old_canonical
    assert publication.snapshot_id == old_snapshot
    assert publication.body == "# Published"
    assert publication.is_previous_attempt is True
