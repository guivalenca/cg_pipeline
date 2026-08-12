"""Resolve the Canonical Source Markdown currently published for a Source.

The acquisition ledger may contain raw, enriched, late-arriving, or otherwise
unpublished Markdown artifacts.  This Module is the single read seam that
turns those append-only facts into the Source Publication downstream
interpretations are allowed to consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg


@dataclass(frozen=True, slots=True)
class Publication:
    source_id: str
    snapshot_id: str
    artifact_id: str
    content_hash: str
    body: str
    tool: str
    tool_version: str | None
    created_at: datetime
    metadata: dict[str, Any]
    is_previous_attempt: bool = False


def current_many(
    conn: psycopg.Connection, source_ids: list[str]
) -> dict[str, Publication]:
    """Resolve publishable Markdown for many Sources without N+1 queries.

    Modern acquisition snapshots publish only through a successful cleanup
    whose artifact lineage reaches the acquisition artifact.  Snapshots that
    predate that contract retain their latest non-empty Markdown projection.
    An unfinished or failed newer attempt preserves the newest eligible
    publication and marks it as belonging to a previous attempt.
    """
    source_ids = list(dict.fromkeys(source_ids))
    if not source_ids:
        return {}

    latest_jobs = {
        source_id: job_id
        for source_id, job_id in conn.execute(
            "SELECT DISTINCT ON (source_id) source_id, id"
            " FROM acquisition_job WHERE source_id = ANY(%s)"
            " ORDER BY source_id, created_at DESC, id DESC",
            (source_ids,),
        ).fetchall()
    }
    rows = conn.execute(
        """
        WITH RECURSIVE cleanup_roots AS (
            SELECT c.id AS cleanup_job_id, c.source_id,
                   c.acquisition_job_id, c.source_artifact_id,
                   j.artifact_id AS acquired_artifact_id,
                   canonical.id AS canonical_artifact_id,
                   canonical.snapshot_id
              FROM source_cleanup_job c
              JOIN acquisition_job j ON j.id = c.acquisition_job_id
              JOIN artifact acquired ON acquired.id = j.artifact_id
              JOIN artifact source_artifact ON source_artifact.id = c.source_artifact_id
              JOIN artifact canonical ON canonical.id = c.canonical_artifact_id
              JOIN source_snapshot sn ON sn.id = canonical.snapshot_id
             WHERE c.source_id = ANY(%s)
               AND c.status = 'succeeded'
               AND c.cleanup_id IS NOT NULL
               AND c.source_id = j.source_id
               AND j.status = 'succeeded'
               AND j.diagnostics->>'pipeline_requires_cleanup' = 'true'
               AND COALESCE(j.diagnostics->>'visual_incomplete', 'false') <> 'true'
               AND sn.status = 'ok'
               AND sn.source_id = c.source_id
               AND acquired.snapshot_id = canonical.snapshot_id
               AND source_artifact.snapshot_id = canonical.snapshot_id
               AND acquired.kind = 'markdown'
               AND source_artifact.kind = 'markdown'
               AND canonical.kind = 'markdown'
               AND acquired.body ~ '[^[:space:]]'
               AND source_artifact.body ~ '[^[:space:]]'
               AND canonical.body ~ '[^[:space:]]'
               AND canonical.tool = 'passage-cleanup'
               AND canonical.metadata->>'cleanup_id' = c.cleanup_id
               AND canonical.id <> j.artifact_id
        ),
        cleanup_lineage AS (
            SELECT root.cleanup_job_id, root.canonical_artifact_id AS artifact_id,
                   root.source_artifact_id, root.acquired_artifact_id,
                   root.snapshot_id, ARRAY[root.canonical_artifact_id]::text[] AS path
              FROM cleanup_roots root
            UNION ALL
            SELECT lineage.cleanup_job_id, parent.id,
                   lineage.source_artifact_id, lineage.acquired_artifact_id,
                   lineage.snapshot_id, lineage.path || ARRAY[parent.id]
              FROM cleanup_lineage lineage
              JOIN artifact child ON child.id = lineage.artifact_id
              JOIN artifact parent
                ON parent.id = child.metadata->>'source_markdown_artifact_id'
             WHERE lineage.artifact_id <> lineage.acquired_artifact_id
               AND cardinality(lineage.path) < 32
               AND parent.snapshot_id = lineage.snapshot_id
               AND parent.kind = 'markdown'
               AND NOT (parent.id = ANY(lineage.path))
        ),
        valid_cleanup_jobs AS (
            SELECT cleanup_job_id
              FROM cleanup_lineage
             GROUP BY cleanup_job_id
            HAVING bool_or(artifact_id = source_artifact_id)
               AND bool_or(artifact_id = acquired_artifact_id)
        ),
        cleanup_candidates AS (
            SELECT root.source_id, sn.id AS snapshot_id,
                   canonical.id AS artifact_id, sn.content_hash,
                   canonical.body, canonical.tool, canonical.tool_version,
                   canonical.created_at, canonical.metadata,
                   root.acquisition_job_id AS origin_job_id,
                   sn.created_at AS snapshot_created_at, 2 AS projection_rank
              FROM cleanup_roots root
              JOIN valid_cleanup_jobs valid
                ON valid.cleanup_job_id = root.cleanup_job_id
              JOIN artifact canonical ON canonical.id = root.canonical_artifact_id
              JOIN source_snapshot sn ON sn.id = root.snapshot_id
        ),
        legacy_candidates AS (
            SELECT sn.source_id, sn.id AS snapshot_id, a.id AS artifact_id,
                   sn.content_hash, a.body, a.tool, a.tool_version,
                   a.created_at, a.metadata, origin.id AS origin_job_id,
                   sn.created_at AS snapshot_created_at,
                   CASE WHEN a.metadata ? 'source_markdown_artifact_id'
                        THEN 1 ELSE 0 END AS projection_rank
              FROM source_snapshot sn
              JOIN artifact a ON a.snapshot_id = sn.id
              LEFT JOIN LATERAL (
                    SELECT j.id
                      FROM acquisition_job j
                      JOIN artifact acquired ON acquired.id = j.artifact_id
                     WHERE j.source_id = sn.source_id
                       AND j.status = 'succeeded'
                       AND acquired.snapshot_id = sn.id
                       AND COALESCE(
                             j.diagnostics->>'pipeline_requires_cleanup', 'false'
                           ) <> 'true'
                     ORDER BY j.created_at DESC, j.id DESC
                     LIMIT 1
              ) origin ON true
             WHERE sn.source_id = ANY(%s)
               AND sn.status = 'ok'
               AND a.kind = 'markdown'
               AND a.body ~ '[^[:space:]]'
               AND a.tool NOT IN (
                     'passage-cleanup', 'article-main-content-boundary'
                   )
               AND NOT (a.metadata ? 'cleanup_id')
               AND NOT EXISTS (
                    SELECT 1
                      FROM acquisition_job strict_job
                      JOIN artifact acquired
                        ON acquired.id = strict_job.artifact_id
                     WHERE strict_job.source_id = sn.source_id
                       AND acquired.snapshot_id = sn.id
                       AND strict_job.diagnostics
                             ->>'pipeline_requires_cleanup' = 'true'
               )
        ),
        candidates AS (
            SELECT * FROM cleanup_candidates
            UNION ALL
            SELECT * FROM legacy_candidates
        )
        SELECT DISTINCT ON (source_id)
               source_id, snapshot_id, artifact_id, content_hash, body, tool,
               tool_version, created_at, metadata, origin_job_id
          FROM candidates
         ORDER BY source_id, snapshot_created_at DESC, snapshot_id DESC,
                  projection_rank DESC, created_at DESC, artifact_id DESC
        """,
        (source_ids, source_ids),
    ).fetchall()
    publications: dict[str, Publication] = {}
    for row in rows:
        (
            source_id,
            snapshot_id,
            artifact_id,
            content_hash,
            body,
            tool,
            tool_version,
            created_at,
            metadata,
            origin_job_id,
        ) = row
        latest_job_id = latest_jobs.get(source_id)
        publications[source_id] = Publication(
            source_id=source_id,
            snapshot_id=snapshot_id,
            artifact_id=artifact_id,
            content_hash=content_hash,
            body=body,
            tool=tool,
            tool_version=tool_version,
            created_at=created_at,
            metadata=dict(metadata or {}),
            is_previous_attempt=bool(
                latest_job_id and origin_job_id != latest_job_id
            ),
        )
    return publications


def current(conn: psycopg.Connection, source_id: str) -> Publication | None:
    """Return the Canonical Source Markdown currently published."""
    return current_many(conn, [source_id]).get(source_id)
