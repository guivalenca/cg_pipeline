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
    """Resolve current publications for many Sources without N+1 queries."""
    source_ids = list(dict.fromkeys(source_ids))
    if not source_ids:
        return {}

    latest_jobs = {
        source_id: {"id": job_id, "diagnostics": diagnostics or {}}
        for source_id, job_id, diagnostics in conn.execute(
            "SELECT DISTINCT ON (source_id) source_id, id, diagnostics"
            " FROM acquisition_job WHERE source_id = ANY(%s)"
            " ORDER BY source_id, created_at DESC, id DESC",
            (source_ids,),
        ).fetchall()
    }
    strict_sources = {
        source_id
        for source_id, job in latest_jobs.items()
        if job["diagnostics"].get("pipeline_requires_cleanup")
    }
    artifact_by_source: dict[str, tuple[str, bool]] = {}

    if strict_sources:
        latest_cleanup = {
            source_id: (status, artifact_id)
            for source_id, status, artifact_id in conn.execute(
                "SELECT j.source_id, c.status, c.canonical_artifact_id"
                " FROM source_cleanup_job c JOIN acquisition_job j"
                " ON j.id = c.acquisition_job_id"
                " WHERE c.acquisition_job_id = ANY(%s)",
                ([latest_jobs[source_id]["id"] for source_id in strict_sources],),
            ).fetchall()
        }
        unresolved = []
        for source_id in strict_sources:
            cleanup = latest_cleanup.get(source_id)
            visual_incomplete = latest_jobs[source_id]["diagnostics"].get(
                "visual_incomplete"
            )
            if (
                cleanup
                and cleanup[0] == "succeeded"
                and cleanup[1]
                and not visual_incomplete
            ):
                artifact_by_source[source_id] = (cleanup[1], False)
            else:
                unresolved.append(source_id)
        if unresolved:
            for source_id, artifact_id in conn.execute(
                "SELECT DISTINCT ON (source_id) source_id, canonical_artifact_id"
                " FROM source_cleanup_job"
                " WHERE source_id = ANY(%s) AND status = 'succeeded'"
                " AND canonical_artifact_id IS NOT NULL"
                " ORDER BY source_id, finished_at DESC, id DESC",
                (unresolved,),
            ).fetchall():
                artifact_by_source[source_id] = (artifact_id, True)

    generic_sources = [
        source_id for source_id in source_ids if source_id not in strict_sources
    ]
    if generic_sources:
        for source_id, artifact_id in conn.execute(
            "SELECT DISTINCT ON (sn.source_id) sn.source_id, a.id"
            " FROM source_snapshot sn JOIN artifact a ON a.snapshot_id = sn.id"
            " WHERE sn.source_id = ANY(%s) AND sn.status = 'ok'"
            " AND a.kind = 'markdown'"
            " ORDER BY sn.source_id, sn.created_at DESC,"
            " (a.metadata ? 'source_markdown_artifact_id') DESC,"
            " a.created_at DESC, a.id DESC",
            (generic_sources,),
        ).fetchall():
            artifact_by_source[source_id] = (artifact_id, False)

    if not artifact_by_source:
        return {}
    previous = {
        artifact_id: is_previous
        for artifact_id, is_previous in artifact_by_source.values()
    }
    rows = conn.execute(
        "SELECT sn.source_id, sn.id, a.id, sn.content_hash, a.body, a.tool,"
        " a.tool_version, a.created_at, a.metadata"
        " FROM artifact a JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE a.id = ANY(%s) AND sn.status = 'ok' AND a.kind = 'markdown'",
        (list(previous),),
    ).fetchall()
    return {
        row[0]: Publication(
            *row[:-1],
            metadata=dict(row[-1] or {}),
            is_previous_attempt=previous[row[2]],
        )
        for row in rows
    }


def current(conn: psycopg.Connection, source_id: str) -> Publication | None:
    """Return the Canonical Source Markdown currently published."""
    return current_many(conn, [source_id]).get(source_id)
