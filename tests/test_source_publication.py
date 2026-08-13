"""Behavior tests for the Canonical Source Markdown publication seam."""

from __future__ import annotations

import uuid

import pytest
from psycopg.types.json import Jsonb


def _insert_source(db, source_id: str) -> None:
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Publication test', 'article')",
        (
            source_id,
            Jsonb({"kind": "url", "value": f"https://example.com/{source_id}"}),
        ),
    )


def _insert_markdown(
    db,
    *,
    source_id: str,
    snapshot_id: str,
    artifact_id: str,
    body: str,
    created_offset: int = 0,
    tool: str = "legacy-import",
) -> None:
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, %s, 'ok', now() + (%s * interval '1 second'))",
        (snapshot_id, source_id, f"hash-{snapshot_id}", created_offset),
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, created_at)"
        " VALUES (%s, %s, 'markdown', %s, %s,"
        " now() + (%s * interval '1 second'))",
        (artifact_id, snapshot_id, tool, body, created_offset),
    )


def _insert_strict_publication(
    db,
    *,
    source_id: str,
    tag: str,
    body: str,
    snapshot_offset: int = 0,
    cleanup_finished_offset: int | None = None,
) -> dict[str, str]:
    snapshot_id = f"snapshot-{tag}"
    source_artifact_id = f"artifact-{tag}-source"
    canonical_artifact_id = f"artifact-{tag}-canonical"
    acquisition_job_id = f"acquisition-{tag}"
    cuts_run_id = f"cuts-{tag}"
    cleanup_id = f"cleanup-result-{tag}"
    cleanup_job_id = f"cleanup-job-{tag}"
    _insert_markdown(
        db,
        source_id=source_id,
        snapshot_id=snapshot_id,
        artifact_id=source_artifact_id,
        body=f"# Intermediate {tag}",
        created_offset=snapshot_offset,
        tool="firecrawl-v2",
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, tool_version, body, metadata, created_at)"
        " VALUES (%s, %s, 'markdown', 'passage-cleanup', 'v1', %s, %s,"
        " now() + (%s * interval '1 second'))",
        (
            canonical_artifact_id,
            snapshot_id,
            body,
            Jsonb(
                {
                    "source_markdown_artifact_id": source_artifact_id,
                    "cleanup_id": cleanup_id,
                }
            ),
            snapshot_offset + 1,
        ),
    )
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status, finished_at)"
        " VALUES (%s, 'passage-cuts', 'test/model', 'passage-cuts/v001',"
        " 'sha', 'done', now())",
        (cuts_run_id,),
    )
    db.execute(
        "INSERT INTO passage_cleanup"
        " (id, cuts_run_id, model, triage_prompt_ref, refine_prompt_ref,"
        "  status, finished_at)"
        " VALUES (%s, %s, 'test/model', 'passage-triage/v005',"
        " 'passage-refine/v002', 'done', now())",
        (cleanup_id, cuts_run_id),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, artifact_id, diagnostics,"
        "  finished_at, created_at)"
        " VALUES (%s, %s, 'succeeded', 'firecrawl/v2', %s, %s, now(),"
        " now() + (%s * interval '1 second'))",
        (
            acquisition_job_id,
            source_id,
            source_artifact_id,
            Jsonb({"pipeline_requires_cleanup": True}),
            snapshot_offset,
        ),
    )
    finished_offset = (
        snapshot_offset + 1
        if cleanup_finished_offset is None
        else cleanup_finished_offset
    )
    db.execute(
        "INSERT INTO source_cleanup_job"
        " (id, acquisition_job_id, source_id, source_artifact_id, status,"
        "  cuts_run_id, cleanup_id, canonical_artifact_id, finished_at, created_at)"
        " VALUES (%s, %s, %s, %s, 'succeeded', %s, %s, %s,"
        " now() + (%s * interval '1 second'),"
        " now() + (%s * interval '1 second'))",
        (
            cleanup_job_id,
            acquisition_job_id,
            source_id,
            source_artifact_id,
            cuts_run_id,
            cleanup_id,
            canonical_artifact_id,
            finished_offset,
            snapshot_offset,
        ),
    )
    return {
        "snapshot_id": snapshot_id,
        "source_artifact_id": source_artifact_id,
        "canonical_artifact_id": canonical_artifact_id,
        "acquisition_job_id": acquisition_job_id,
        "cleanup_job_id": cleanup_job_id,
    }


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
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, metadata, created_at)"
        " VALUES (%s, %s, 'markdown', 'firecrawl', '# Old raw', '{}', now()),"
        "        (%s, %s, 'markdown', 'passage-cleanup', '# Published', %s,"
        "         now() + interval '1 second'),"
        "        (%s, %s, 'markdown', 'firecrawl', '# New intermediate', '{}',"
        "         now() + interval '2 second')",
        (
            old_base,
            old_snapshot,
            old_canonical,
            old_snapshot,
            Jsonb(
                {
                    "source_markdown_artifact_id": old_base,
                    "cleanup_id": cleanup_id,
                }
            ),
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


def test_failed_latest_acquisition_marks_preserved_publication_as_previous(db):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-failed-refresh-{marker}"
    snapshot_id = f"snapshot-failed-refresh-{marker}"
    artifact_id = f"artifact-failed-refresh-{marker}"
    _insert_source(db, source_id)
    _insert_markdown(
        db,
        source_id=source_id,
        snapshot_id=snapshot_id,
        artifact_id=artifact_id,
        body="# Last valid publication",
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, failure_code, diagnostics,"
        "  finished_at, created_at)"
        " VALUES (%s, %s, 'failed', 'firecrawl/v2', 'fetch_failed', %s,"
        " now(), now() + interval '2 seconds')",
        (
            f"acquisition-failed-refresh-{marker}",
            source_id,
            Jsonb({"category": "provider_failure"}),
        ),
    )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.artifact_id == artifact_id
    assert publication.body == "# Last valid publication"
    assert publication.is_previous_attempt is True


def test_first_strict_refresh_preserves_a_legacy_publication(db):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-legacy-refresh-{marker}"
    legacy_snapshot = f"snapshot-legacy-refresh-{marker}"
    legacy_artifact = f"artifact-legacy-refresh-{marker}"
    refresh_snapshot = f"snapshot-modern-refresh-{marker}"
    refresh_artifact = f"artifact-modern-refresh-{marker}"
    refresh_job = f"acquisition-modern-refresh-{marker}"
    _insert_source(db, source_id)
    _insert_markdown(
        db,
        source_id=source_id,
        snapshot_id=legacy_snapshot,
        artifact_id=legacy_artifact,
        body="# Legacy publication",
    )
    _insert_markdown(
        db,
        source_id=source_id,
        snapshot_id=refresh_snapshot,
        artifact_id=refresh_artifact,
        body="# Unpublished modern intermediate",
        created_offset=2,
        tool="firecrawl-v2",
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, artifact_id, diagnostics,"
        "  finished_at, created_at)"
        " VALUES (%s, %s, 'succeeded', 'firecrawl/v2', %s, %s, now(),"
        " now() + interval '2 seconds')",
        (
            refresh_job,
            source_id,
            refresh_artifact,
            Jsonb({"pipeline_requires_cleanup": True}),
        ),
    )
    db.execute(
        "INSERT INTO source_cleanup_job"
        " (id, acquisition_job_id, source_id, source_artifact_id, status, created_at)"
        " VALUES (%s, %s, %s, %s, 'queued', now() + interval '2 seconds')",
        (
            f"cleanup-modern-refresh-{marker}",
            refresh_job,
            source_id,
            refresh_artifact,
        ),
    )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.artifact_id == legacy_artifact
    assert publication.body == "# Legacy publication"
    assert publication.is_previous_attempt is True


def test_succeeded_strict_attempt_publishes_only_its_canonical_artifact(db):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-current-cleanup-{marker}"
    _insert_source(db, source_id)
    inserted = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"current-cleanup-{marker}",
        body="# Canonical publication",
    )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.artifact_id == inserted["canonical_artifact_id"]
    assert publication.artifact_id != inserted["source_artifact_id"]
    assert publication.body == "# Canonical publication"
    assert publication.tool == "passage-cleanup"
    assert publication.is_previous_attempt is False


@pytest.mark.parametrize("cleanup_status", ("running", "failed"))
def test_unfinished_or_failed_cleanup_preserves_previous_publication(
    db, cleanup_status: str
):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-cleanup-{cleanup_status}-{marker}"
    legacy_snapshot = f"snapshot-cleanup-{cleanup_status}-{marker}-legacy"
    legacy_artifact = f"artifact-cleanup-{cleanup_status}-{marker}-legacy"
    refresh_snapshot = f"snapshot-cleanup-{cleanup_status}-{marker}-refresh"
    refresh_artifact = f"artifact-cleanup-{cleanup_status}-{marker}-refresh"
    refresh_job = f"acquisition-cleanup-{cleanup_status}-{marker}"
    _insert_source(db, source_id)
    _insert_markdown(
        db,
        source_id=source_id,
        snapshot_id=legacy_snapshot,
        artifact_id=legacy_artifact,
        body="# Previous publication",
    )
    _insert_markdown(
        db,
        source_id=source_id,
        snapshot_id=refresh_snapshot,
        artifact_id=refresh_artifact,
        body="# Current intermediate",
        created_offset=2,
        tool="firecrawl-v2",
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, artifact_id, diagnostics,"
        "  finished_at, created_at)"
        " VALUES (%s, %s, 'succeeded', 'firecrawl/v2', %s, %s, now(),"
        " now() + interval '2 seconds')",
        (
            refresh_job,
            source_id,
            refresh_artifact,
            Jsonb({"pipeline_requires_cleanup": True}),
        ),
    )
    if cleanup_status == "running":
        db.execute(
            "INSERT INTO source_cleanup_job"
            " (id, acquisition_job_id, source_id, source_artifact_id, status,"
            "  claim_token, claimed_at, created_at)"
            " VALUES (%s, %s, %s, %s, 'running', 'test-claim', now(), now())",
            (
                f"cleanup-{cleanup_status}-{marker}",
                refresh_job,
                source_id,
                refresh_artifact,
            ),
        )
    else:
        db.execute(
            "INSERT INTO source_cleanup_job"
            " (id, acquisition_job_id, source_id, source_artifact_id, status,"
            "  failure_code, finished_at, created_at)"
            " VALUES (%s, %s, %s, %s, 'failed', 'source_cleanup_failed',"
            " now(), now())",
            (
                f"cleanup-{cleanup_status}-{marker}",
                refresh_job,
                source_id,
                refresh_artifact,
            ),
        )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.artifact_id == legacy_artifact
    assert publication.body == "# Previous publication"
    assert publication.is_previous_attempt is True


def test_first_strict_attempt_has_no_publication_until_cleanup_succeeds(db):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-first-strict-{marker}"
    snapshot_id = f"snapshot-first-strict-{marker}"
    artifact_id = f"artifact-first-strict-{marker}"
    acquisition_job_id = f"acquisition-first-strict-{marker}"
    _insert_source(db, source_id)
    _insert_markdown(
        db,
        source_id=source_id,
        snapshot_id=snapshot_id,
        artifact_id=artifact_id,
        body="# Intermediate only",
        tool="firecrawl-v2",
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, artifact_id, diagnostics, finished_at)"
        " VALUES (%s, %s, 'succeeded', 'firecrawl/v2', %s, %s, now())",
        (
            acquisition_job_id,
            source_id,
            artifact_id,
            Jsonb({"pipeline_requires_cleanup": True}),
        ),
    )
    db.execute(
        "INSERT INTO source_cleanup_job"
        " (id, acquisition_job_id, source_id, source_artifact_id, status)"
        " VALUES (%s, %s, %s, %s, 'queued')",
        (
            f"cleanup-first-strict-{marker}",
            acquisition_job_id,
            source_id,
            artifact_id,
        ),
    )

    assert current(db, source_id) is None


def test_previous_publication_follows_snapshot_order_not_cleanup_finish_time(db):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-cleanup-order-{marker}"
    _insert_source(db, source_id)
    older = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"cleanup-order-{marker}-older",
        body="# Older publication",
        snapshot_offset=0,
        cleanup_finished_offset=10,
    )
    newer = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"cleanup-order-{marker}-newer",
        body="# Newer publication",
        snapshot_offset=2,
        cleanup_finished_offset=3,
    )
    refresh_snapshot = f"snapshot-cleanup-order-{marker}-refresh"
    refresh_artifact = f"artifact-cleanup-order-{marker}-refresh"
    refresh_job = f"acquisition-cleanup-order-{marker}-refresh"
    _insert_markdown(
        db,
        source_id=source_id,
        snapshot_id=refresh_snapshot,
        artifact_id=refresh_artifact,
        body="# Latest intermediate",
        created_offset=4,
        tool="firecrawl-v2",
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, artifact_id, diagnostics,"
        "  finished_at, created_at)"
        " VALUES (%s, %s, 'succeeded', 'firecrawl/v2', %s, %s, now(),"
        " now() + interval '4 seconds')",
        (
            refresh_job,
            source_id,
            refresh_artifact,
            Jsonb({"pipeline_requires_cleanup": True}),
        ),
    )
    db.execute(
        "INSERT INTO source_cleanup_job"
        " (id, acquisition_job_id, source_id, source_artifact_id, status, created_at)"
        " VALUES (%s, %s, %s, %s, 'queued', now() + interval '4 seconds')",
        (
            f"cleanup-order-{marker}-refresh",
            refresh_job,
            source_id,
            refresh_artifact,
        ),
    )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.artifact_id == newer["canonical_artifact_id"]
    assert publication.artifact_id != older["canonical_artifact_id"]
    assert publication.body == "# Newer publication"
    assert publication.is_previous_attempt is True


def test_empty_canonical_artifact_is_not_a_source_publication(db):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-empty-canonical-{marker}"
    _insert_source(db, source_id)
    previous = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"empty-canonical-{marker}-previous",
        body="# Previous valid publication",
        snapshot_offset=0,
    )
    rejected = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"empty-canonical-{marker}-current",
        body="  \n\t",
        snapshot_offset=2,
    )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.artifact_id == previous["canonical_artifact_id"]
    assert publication.artifact_id != rejected["canonical_artifact_id"]
    assert publication.body == "# Previous valid publication"
    assert publication.is_previous_attempt is True


def test_canonical_artifact_from_another_snapshot_is_not_a_publication(db):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-cross-snapshot-{marker}"
    _insert_source(db, source_id)
    previous = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"cross-snapshot-{marker}-previous",
        body="# Previous valid publication",
        snapshot_offset=0,
    )
    corrupted = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"cross-snapshot-{marker}-current",
        body="# Original canonical",
        snapshot_offset=2,
    )
    foreign_snapshot = f"snapshot-cross-snapshot-{marker}-foreign"
    foreign_canonical = f"artifact-cross-snapshot-{marker}-foreign"
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, 'foreign-hash', 'ok', now() + interval '3 seconds')",
        (foreign_snapshot, source_id),
    )
    cleanup_id = f"cleanup-result-cross-snapshot-{marker}-current"
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, metadata, created_at)"
        " VALUES (%s, %s, 'markdown', 'passage-cleanup', '# Foreign canonical',"
        " %s, now() + interval '3 seconds')",
        (
            foreign_canonical,
            foreign_snapshot,
            Jsonb(
                {
                    "source_markdown_artifact_id": corrupted["source_artifact_id"],
                    "cleanup_id": cleanup_id,
                }
            ),
        ),
    )
    db.execute(
        "UPDATE source_cleanup_job SET canonical_artifact_id = %s"
        " WHERE id = %s",
        (foreign_canonical, corrupted["cleanup_job_id"]),
    )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.artifact_id == previous["canonical_artifact_id"]
    assert publication.artifact_id != foreign_canonical
    assert publication.body == "# Previous valid publication"
    assert publication.is_previous_attempt is True


def test_current_many_resolves_mixed_sources_and_omits_unpublished_ones(db):
    from universe.source_publication import current_many

    marker = uuid.uuid4().hex[:10]
    legacy_source = f"source-many-{marker}-legacy"
    strict_source = f"source-many-{marker}-strict"
    absent_source = f"source-many-{marker}-absent"
    for source_id in (legacy_source, strict_source, absent_source):
        _insert_source(db, source_id)
    legacy_artifact = f"artifact-many-{marker}-legacy"
    _insert_markdown(
        db,
        source_id=legacy_source,
        snapshot_id=f"snapshot-many-{marker}-legacy",
        artifact_id=legacy_artifact,
        body="# Legacy publication",
    )
    strict = _insert_strict_publication(
        db,
        source_id=strict_source,
        tag=f"many-{marker}-strict",
        body="# Canonical publication",
    )

    publications = current_many(
        db,
        [legacy_source, strict_source, absent_source, legacy_source],
    )

    assert set(publications) == {legacy_source, strict_source}
    assert publications[legacy_source].artifact_id == legacy_artifact
    assert publications[legacy_source].body == "# Legacy publication"
    assert publications[strict_source].artifact_id == strict["canonical_artifact_id"]
    assert publications[strict_source].body == "# Canonical publication"
    assert publications[legacy_source].is_previous_attempt is False
    assert publications[strict_source].is_previous_attempt is False
    assert current_many(db, []) == {}


def test_failed_refresh_never_reclassifies_an_older_strict_intermediate(db):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-intermediate-leak-{marker}"
    snapshot_id = f"snapshot-intermediate-leak-{marker}"
    artifact_id = f"artifact-intermediate-leak-{marker}"
    strict_job = f"acquisition-intermediate-leak-{marker}-strict"
    _insert_source(db, source_id)
    _insert_markdown(
        db,
        source_id=source_id,
        snapshot_id=snapshot_id,
        artifact_id=artifact_id,
        body="# Never published intermediate",
        tool="firecrawl-v2",
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, artifact_id, diagnostics,"
        "  finished_at, created_at)"
        " VALUES (%s, %s, 'succeeded', 'firecrawl/v2', %s, %s, now(), now())",
        (
            strict_job,
            source_id,
            artifact_id,
            Jsonb({"pipeline_requires_cleanup": True}),
        ),
    )
    db.execute(
        "INSERT INTO source_cleanup_job"
        " (id, acquisition_job_id, source_id, source_artifact_id, status)"
        " VALUES (%s, %s, %s, %s, 'queued')",
        (
            f"cleanup-intermediate-leak-{marker}",
            strict_job,
            source_id,
            artifact_id,
        ),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, failure_code, diagnostics,"
        "  finished_at, created_at)"
        " VALUES (%s, %s, 'failed', 'firecrawl/v2', 'fetch_failed', %s, now(),"
        " now() + interval '2 seconds')",
        (
            f"acquisition-intermediate-leak-{marker}-failed",
            source_id,
            Jsonb({"category": "provider_failure"}),
        ),
    )

    assert current(db, source_id) is None


def test_canonical_lineage_must_reach_the_cleanup_source_artifact(db):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-broken-lineage-{marker}"
    _insert_source(db, source_id)
    previous = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"broken-lineage-{marker}-previous",
        body="# Previous valid publication",
        snapshot_offset=0,
    )
    corrupted = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"broken-lineage-{marker}-current",
        body="# Canonical with broken lineage",
        snapshot_offset=2,
    )
    unrelated_artifact = f"artifact-broken-lineage-{marker}-unrelated"
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'unrelated-projection', '# Sibling')",
        (unrelated_artifact, corrupted["snapshot_id"]),
    )
    db.execute(
        "UPDATE artifact SET metadata = %s WHERE id = %s",
        (
            Jsonb(
                {
                    "source_markdown_artifact_id": unrelated_artifact,
                    "cleanup_id": f"cleanup-result-broken-lineage-{marker}-current",
                }
            ),
            corrupted["canonical_artifact_id"],
        ),
    )

    publication = current(db, source_id)

    assert publication is not None
    assert publication.artifact_id == previous["canonical_artifact_id"]
    assert publication.body == "# Previous valid publication"
    assert publication.is_previous_attempt is True


def test_read_keeps_a_historical_strict_publication_but_rejects_its_intermediate(
    db,
):
    from universe.source_publication import current, read

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-read-history-{marker}"
    _insert_source(db, source_id)
    historical = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"read-history-{marker}-old",
        body="# Historical canonical",
        snapshot_offset=0,
    )
    latest = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"read-history-{marker}-new",
        body="# Current canonical",
        snapshot_offset=5,
    )

    selected = current(db, source_id)
    pinned = read(db, source_id, historical["canonical_artifact_id"])

    assert selected is not None
    assert selected.artifact_id == latest["canonical_artifact_id"]
    assert pinned is not None
    assert pinned.artifact_id == historical["canonical_artifact_id"]
    assert pinned.body == "# Historical canonical"
    assert pinned.is_previous_attempt is True
    assert read(db, source_id, historical["source_artifact_id"]) is None


def test_read_rejects_a_fabricated_or_corrupted_cleanup_artifact(db):
    from universe.source_publication import read

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-read-corrupt-{marker}"
    _insert_source(db, source_id)
    strict = _insert_strict_publication(
        db,
        source_id=source_id,
        tag=f"read-corrupt-{marker}",
        body="# Corrupted canonical",
    )
    fake_id = f"artifact-read-corrupt-{marker}-fake"
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, metadata)"
        " VALUES (%s, %s, 'markdown', 'passage-cleanup', '# Fake', %s)",
        (
            fake_id,
            strict["snapshot_id"],
            Jsonb(
                {
                    "source_markdown_artifact_id": fake_id,
                    "cleanup_id": f"cleanup-result-read-corrupt-{marker}",
                }
            ),
        ),
    )
    db.execute(
        "UPDATE artifact SET metadata = %s WHERE id = %s",
        (
            Jsonb(
                {
                    "source_markdown_artifact_id": fake_id,
                    "cleanup_id": f"cleanup-result-read-corrupt-{marker}",
                }
            ),
            strict["canonical_artifact_id"],
        ),
    )

    assert read(db, source_id, fake_id) is None
    assert read(db, source_id, strict["canonical_artifact_id"]) is None
