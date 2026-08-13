"""Explicit Syllabus Version checkpoint for the four shared KC stages.

``offer`` proves whether every active reference resolves to a current Source
Publication whose eleven local stages are complete.  ``request`` then seals
exactly those publications into an immutable corpus manifest.  No later read
or worker action discovers participants from global state: the build always
dispatches through its stored ``CorpusManifestTarget``.

The aggregate owns the scheduler claim, request idempotency, and Syllabus
Version route.  ``kc_pipeline`` continues to own stage planning, child leases,
and the durable KC results themselves.
"""

from __future__ import annotations

import subprocess
import uuid
from collections.abc import Callable, Mapping
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from universe import kc_corpus_manifest, kc_pipeline, kc_progress
from universe.source_publication import Publication, current_many


CLAIM_TTL_SECONDS = 300.0
POLL_SECONDS = 1.0
_DEFAULT_SPAWN = object()


class SyllabusKnowledgeNotReady(ValueError):
    """The current Syllabus Version cannot safely seal a corpus yet."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        reference_ids: tuple[str, ...] = (),
        source_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.reference_ids = reference_ids
        self.source_ids = source_ids


def _text(value: object, *, field: str, limit: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    cleaned = value.strip()
    if limit is not None and len(cleaned) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")
    return cleaned


def _route(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
) -> dict[str, Any]:
    syllabus_id = _text(syllabus_id, field="syllabus_id")
    version_id = _text(version_id, field="version_id")
    row = conn.execute(
        "SELECT syllabus.title, version.seq"
        " FROM syllabus_version version"
        " JOIN syllabus ON syllabus.id = version.syllabus_id"
        " WHERE syllabus.id = %s AND version.id = %s",
        (syllabus_id, version_id),
    ).fetchone()
    if row is None:
        raise LookupError(
            f"unknown Syllabus Version {syllabus_id!r}/{version_id!r}"
        )
    return {
        "syllabus_id": syllabus_id,
        "version_id": version_id,
        "syllabus_title": row[0],
        "version_seq": row[1],
    }


def _eligibility_projection(
    error: SyllabusKnowledgeNotReady | None,
) -> dict[str, Any]:
    return {
        "eligible": error is None,
        "code": "ready" if error is None else error.code,
        "message": (
            "the Syllabus Version is ready for shared KC work"
            if error is None
            else str(error)
        ),
        "reference_ids": [] if error is None else list(error.reference_ids),
        "source_ids": [] if error is None else list(error.source_ids),
    }


def _manifest_is_current(
    manifest_id: str,
    publications: list[Publication],
) -> bool:
    """Whether a build pins the exact active Source Publications right now."""
    return bool(
        publications
        and manifest_id == kc_corpus_manifest.id_for(publications)
    )


def _active_publications(
    conn: psycopg.Connection,
    route: Mapping[str, Any],
) -> tuple[
    list[tuple[str, str | None, bool]],
    list[Publication],
    SyllabusKnowledgeNotReady | None,
]:
    """Resolve the complete active publication set without interpreting it."""
    references = conn.execute(
        "SELECT reference.id, reference.source_id,"
        " coalesce(review.is_validated, false)"
        " FROM syllabus_lesson lesson"
        " JOIN syllabus_source_reference reference"
        "   ON reference.version_id = lesson.version_id"
        "  AND reference.lesson_id = lesson.id"
        " LEFT JOIN syllabus_source_review review ON review.reference_id = reference.id"
        " WHERE lesson.version_id = %s"
        "   AND NOT lesson.is_hidden AND NOT reference.is_hidden"
        " ORDER BY lesson.seq, lesson.id, reference.seq, reference.id",
        (route["version_id"],),
    ).fetchall()
    if not references:
        return [], [], SyllabusKnowledgeNotReady(
            "no_active_references",
            "the Syllabus Version has no active source references",
        )

    unvalidated_reference_ids = tuple(
        reference_id
        for reference_id, _, validated in references
        if not validated
    )
    if unvalidated_reference_ids:
        return references, [], SyllabusKnowledgeNotReady(
            "references_not_validated",
            "every active source reference must be validated",
            reference_ids=unvalidated_reference_ids,
        )

    missing_reference_ids = tuple(
        reference_id
        for reference_id, source_id, _ in references
        if source_id is None
    )
    if missing_reference_ids:
        return references, [], SyllabusKnowledgeNotReady(
            "references_without_source",
            "every active reference must resolve to a Source",
            reference_ids=missing_reference_ids,
        )

    source_ids = list(
        dict.fromkeys(source_id for _, source_id, _ in references if source_id)
    )
    current = current_many(conn, source_ids)
    unavailable = tuple(
        source_id for source_id in source_ids if source_id not in current
    )
    if unavailable:
        return references, [], SyllabusKnowledgeNotReady(
            "publications_unavailable",
            "every active Source must have a current Source Publication",
            source_ids=unavailable,
        )
    previous = tuple(
        source_id
        for source_id in source_ids
        if current[source_id].is_previous_attempt
    )
    if previous:
        return references, [], SyllabusKnowledgeNotReady(
            "publications_not_current",
            "some Source Publications belong to a previous attempt",
            source_ids=previous,
        )

    return references, [current[source_id] for source_id in source_ids], None


def _active_scope(
    conn: psycopg.Connection,
    route: Mapping[str, Any],
) -> tuple[
    list[tuple[str, str | None, bool]],
    list[Publication],
    list[dict[str, Any]],
    SyllabusKnowledgeNotReady | None,
]:
    """Authoritatively verify all eleven local stages before sealing."""
    references, publications, publication_error = _active_publications(conn, route)
    if publication_error is not None:
        return references, publications, [], publication_error
    local_progress: list[dict[str, Any]] = []
    incomplete: list[str] = []
    for publication in publications:
        progress = kc_progress.publication_progress(
            conn,
            source_id=publication.source_id,
            artifact_id=publication.artifact_id,
        )
        stages = progress.get("stages", {})
        completed = sum(
            stages.get(stage, {}).get("status") == "done"
            for stage in kc_pipeline.LOCAL_STAGES
        )
        complete = completed == len(kc_pipeline.LOCAL_STAGES)
        local_progress.append(
            {
                "source_id": publication.source_id,
                "artifact_id": publication.artifact_id,
                "completed_stage_count": completed,
                "total_stage_count": len(kc_pipeline.LOCAL_STAGES),
                "complete": complete,
            }
        )
        if not complete:
            incomplete.append(publication.source_id)
    if incomplete:
        return references, publications, local_progress, SyllabusKnowledgeNotReady(
            "local_kcs_incomplete",
            "every active Source Publication must complete all eleven local KC stages",
            source_ids=tuple(incomplete),
        )
    return references, publications, local_progress, None


def _durable_local_progress(
    conn: psycopg.Connection,
    publications: list[Publication],
) -> list[dict[str, Any]]:
    """Summarize trusted worker counters for exact current publications."""
    if not publications:
        return []
    work_rows = {
        artifact_id: (
            source_id,
            snapshot_id,
            content_hash,
            bool(was_previous_attempt),
            status,
            stage,
            dict(diagnostics or {}),
        )
        for (
            artifact_id,
            source_id,
            snapshot_id,
            content_hash,
            was_previous_attempt,
            status,
            stage,
            diagnostics,
        ) in conn.execute(
            "SELECT DISTINCT ON (artifact_id) artifact_id, source_id, snapshot_id,"
            " content_hash, publication_is_previous_attempt, status, stage,"
            " diagnostics FROM lesson_knowledge_work"
            " WHERE artifact_id = ANY(%s)"
            " ORDER BY artifact_id,"
            " (status = 'succeeded'"
            "  AND (stage IS NULL OR stage = 'local-complete')) DESC,"
            " updated_at DESC, id DESC",
            ([publication.artifact_id for publication in publications],),
        ).fetchall()
    }
    local_progress = []
    total = len(kc_pipeline.LOCAL_STAGES)
    for publication in publications:
        facts = work_rows.get(publication.artifact_id)
        completed = 0
        if facts is not None:
            (
                source_id,
                snapshot_id,
                content_hash,
                was_previous_attempt,
                status,
                stage,
                diagnostics,
            ) = facts
            try:
                completed = int(diagnostics.get("completed_stage_count") or 0)
                reported_total = int(diagnostics.get("total_stage_count") or 0)
            except (TypeError, ValueError):
                completed = 0
                reported_total = 0
            complete = bool(
                source_id == publication.source_id
                and snapshot_id == publication.snapshot_id
                and content_hash == publication.content_hash
                and not was_previous_attempt
                and status == "succeeded"
                # The production worker clears ``stage`` at terminal success.
                # ``local-complete`` remains readable for pre-worker rows.
                and stage in (None, "local-complete")
                and completed == total
                and reported_total == total
            )
            completed = min(max(completed, 0), total)
        else:
            complete = False
        local_progress.append(
            {
                "source_id": publication.source_id,
                "artifact_id": publication.artifact_id,
                "completed_stage_count": completed,
                "total_stage_count": total,
                "complete": complete,
            }
        )
    return local_progress


def _snapshot(conn: psycopg.Connection, manifest_id: str) -> dict[str, Any]:
    return kc_pipeline.read_snapshot(
        conn, kc_pipeline.CorpusManifestTarget(manifest_id)
    )


def _shared_progress(snapshot: Mapping[str, Any]) -> dict[str, int]:
    stages = snapshot.get("stages")
    stages = stages if isinstance(stages, Mapping) else {}
    counts = {
        status: sum(
            stages.get(stage, {}).get("status") == status
            for stage in kc_pipeline.SHARED_STAGES
        )
        for status in ("pending", "partial", "running", "failed", "done")
    }
    return {
        "total": len(kc_pipeline.SHARED_STAGES),
        "completed": counts["done"],
        "pending": counts["pending"],
        "partial": counts["partial"],
        "running": counts["running"],
        "failed": counts["failed"],
    }


def _durable_shared_progress(
    *,
    status: str,
    stage: str | None,
    diagnostics: Mapping[str, Any],
) -> dict[str, int]:
    """Project the four-stage counter without re-reading the corpus ledger."""
    total = len(kc_pipeline.SHARED_STAGES)
    if status == "succeeded":
        completed = total
    else:
        try:
            completed = int(diagnostics.get("shared_stage_count") or 0)
        except (TypeError, ValueError):
            completed = 0
        if stage in kc_pipeline.SHARED_STAGES:
            completed = max(completed, kc_pipeline.SHARED_STAGES.index(stage))
        completed = min(max(completed, 0), total)
    active_status = None
    if completed < total and stage in kc_pipeline.SHARED_STAGES:
        if status == "running":
            active_status = "running"
        elif status == "failed":
            reported = diagnostics.get("pipeline_stage_status")
            active_status = "partial" if reported == "partial" else "failed"
    active = int(active_status is not None)
    return {
        "total": total,
        "completed": completed,
        "pending": max(total - completed - active, 0),
        "partial": int(active_status == "partial"),
        "running": int(active_status == "running"),
        "failed": int(active_status == "failed"),
    }


def _project_summary(
    route: Mapping[str, Any],
    row: tuple[Any, ...],
) -> dict[str, Any]:
    (
        build_id,
        request_key,
        requested_by,
        manifest_id,
        status,
        stage,
        last_launched_stage,
        failure_code,
        diagnostics,
        claim_count,
        created_at,
        updated_at,
    ) = row
    diagnostics = dict(diagnostics or {})
    return {
        "id": build_id,
        "syllabus_id": route["syllabus_id"],
        "version_id": route["version_id"],
        "syllabus_title": route["syllabus_title"],
        "version_seq": route["version_seq"],
        "request_key": request_key,
        "requested_by": requested_by,
        "manifest_id": manifest_id,
        "status": status,
        "stage": stage,
        "last_launched_stage": last_launched_stage,
        "failure_code": failure_code,
        "diagnostics": diagnostics,
        "claim_count": claim_count,
        "created_at": created_at,
        "updated_at": updated_at,
        "progress": _durable_shared_progress(
            status=status,
            stage=stage,
            diagnostics=diagnostics,
        ),
    }


def _project(
    conn: psycopg.Connection,
    route: Mapping[str, Any],
    build_id: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT request_key, requested_by, manifest_id, status, stage,"
        " last_launched_stage, failure_code, diagnostics, claim_count,"
        " created_at, updated_at"
        " FROM syllabus_knowledge_build"
        " WHERE id = %s AND version_id = %s",
        (build_id, route["version_id"]),
    ).fetchone()
    if row is None:
        return None
    (
        request_key,
        requested_by,
        manifest_id,
        status,
        stage,
        last_launched_stage,
        failure_code,
        diagnostics,
        claim_count,
        created_at,
        updated_at,
    ) = row
    manifest = kc_corpus_manifest.read(conn, manifest_id)
    if manifest is None:
        raise RuntimeError(f"incomplete KC corpus manifest {manifest_id}")
    snapshot = _snapshot(conn, manifest_id)
    return {
        "id": build_id,
        "syllabus_id": route["syllabus_id"],
        "version_id": route["version_id"],
        "syllabus_title": route["syllabus_title"],
        "version_seq": route["version_seq"],
        "request_key": request_key,
        "requested_by": requested_by,
        "manifest_id": manifest_id,
        "manifest": manifest,
        "status": status,
        "stage": stage,
        "last_launched_stage": last_launched_stage,
        "failure_code": failure_code,
        "diagnostics": dict(diagnostics or {}),
        "claim_count": claim_count,
        "created_at": created_at,
        "updated_at": updated_at,
        "progress": _shared_progress(snapshot),
        "snapshot": snapshot,
    }


def offer(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
) -> dict[str, Any]:
    """Read readiness and the latest explicitly requested corpus build."""
    route = _route(conn, syllabus_id, version_id)
    references, publications, local_progress, error = _active_scope(conn, route)
    latest_id, published_id = conn.execute(
        "SELECT"
        " (SELECT id FROM syllabus_knowledge_build"
        "  WHERE version_id = %s ORDER BY request_seq DESC LIMIT 1),"
        " (SELECT id FROM syllabus_knowledge_build"
        "  WHERE version_id = %s AND status = 'succeeded'"
        "  ORDER BY request_seq DESC LIMIT 1)",
        (route["version_id"], route["version_id"]),
    ).fetchone()
    builds: dict[str, dict[str, Any]] = {}
    for build_id in (latest_id, published_id):
        if build_id is None or build_id in builds:
            continue
        build = _project(conn, route, build_id)
        if build is not None:
            build["current"] = _manifest_is_current(
                build["manifest_id"], publications
            )
            builds[build_id] = build
    latest_build = builds.get(latest_id)
    published_build = builds.get(published_id)
    return {
        **route,
        "active_reference_count": len(references),
        "publication_count": len(publications),
        "complete_publication_count": sum(
            item["complete"] for item in local_progress
        ),
        "local_progress": local_progress,
        "eligibility": _eligibility_projection(error),
        "latest_build": latest_build,
        "published_build": published_build,
    }


def offer_summary(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
) -> dict[str, Any]:
    """Read the Syllabi-page projection in a bounded number of queries.

    This projection trusts counters written by the local and shared workers;
    it never reconstructs eleven local ledgers per Source or the corpus
    snapshot.  ``request`` does not trust this summary: it keeps using the
    deep ``_active_scope`` checkpoint immediately before an immutable manifest
    is created.
    """
    route = _route(conn, syllabus_id, version_id)
    references, publications, publication_error = _active_publications(
        conn, route
    )
    local_progress = _durable_local_progress(conn, publications)
    incomplete = tuple(
        item["source_id"] for item in local_progress if not item["complete"]
    )
    error = publication_error
    if error is None and incomplete:
        error = SyllabusKnowledgeNotReady(
            "local_kcs_incomplete",
            "every active Source Publication must complete all eleven local KC stages",
            source_ids=incomplete,
        )
    rows = conn.execute(
        "WITH selected AS ("
        " SELECT DISTINCT ON (selection.kind) selection.kind,"
        " build.id, build.request_key, build.requested_by, build.manifest_id,"
        " build.status, build.stage, build.last_launched_stage,"
        " build.failure_code, build.diagnostics, build.claim_count,"
        " build.created_at, build.updated_at"
        " FROM syllabus_knowledge_build build"
        " CROSS JOIN (VALUES ('latest'), ('published')) AS selection(kind)"
        " WHERE build.version_id = %s"
        "   AND (selection.kind = 'latest' OR build.status = 'succeeded')"
        " ORDER BY selection.kind, build.request_seq DESC"
        ") SELECT * FROM selected",
        (route["version_id"],),
    ).fetchall()
    builds = {
        kind: _project_summary(route, row)
        for kind, *row in rows
    }
    for build in builds.values():
        build["current"] = _manifest_is_current(
            build["manifest_id"], publications
        )
    latest_build = builds.get("latest")
    published_build = builds.get("published")
    return {
        **route,
        "active_reference_count": len(references),
        "publication_count": len(publications),
        "complete_publication_count": sum(
            item["complete"] for item in local_progress
        ),
        "local_progress": local_progress,
        "eligibility": _eligibility_projection(error),
        "latest_build": latest_build,
        "published_build": published_build,
    }


def request(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
    request_key: str,
    *,
    actor: str,
) -> dict[str, Any]:
    """Seal and queue one exact corpus; route/key replay is idempotent."""
    route = _route(conn, syllabus_id, version_id)
    request_key = _text(request_key, field="request_key", limit=200)
    actor = _text(actor, field="actor", limit=200)
    existing = conn.execute(
        "SELECT id FROM syllabus_knowledge_build"
        " WHERE version_id = %s AND request_key = %s",
        (route["version_id"], request_key),
    ).fetchone()
    if existing is not None:
        replay = _project(conn, route, existing[0])
        if replay is None:
            raise RuntimeError(f"incomplete syllabus knowledge build {existing[0]}")
        _, publications, publication_error = _active_publications(conn, route)
        replay["current"] = _manifest_is_current(
            replay["manifest_id"], publications
        )
        return replay

    _, publications, _, error = _active_scope(conn, route)
    if error is not None:
        raise error
    try:
        manifest = kc_corpus_manifest.create(
            conn,
            publications,
            origin={
                "kind": "syllabus-version",
                "syllabus_id": route["syllabus_id"],
                "version_id": route["version_id"],
            },
        )
    except ValueError as exc:
        raise SyllabusKnowledgeNotReady(
            "publications_changed",
            "the active Source Publications changed while sealing the corpus",
            source_ids=tuple(item.source_id for item in publications),
        ) from exc

    build_id = f"syllabus-kc-build-{uuid.uuid4().hex}"
    with conn.transaction():
        inserted = conn.execute(
            "INSERT INTO syllabus_knowledge_build"
            " (id, version_id, request_key, requested_by, manifest_id)"
            " VALUES (%s, %s, %s, %s, %s)"
            " ON CONFLICT (version_id, request_key) DO NOTHING RETURNING id",
            (
                build_id,
                route["version_id"],
                request_key,
                actor,
                manifest["id"],
            ),
        ).fetchone()
        if inserted is None:
            build_id = conn.execute(
                "SELECT id FROM syllabus_knowledge_build"
                " WHERE version_id = %s AND request_key = %s",
                (route["version_id"], request_key),
            ).fetchone()[0]
    projection = _project(conn, route, build_id)
    if projection is None:
        raise RuntimeError(f"incomplete syllabus knowledge build {build_id}")
    projection["current"] = True
    return projection


def read(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
    build_id: str,
) -> dict[str, Any] | None:
    """Read one build only through its owning Syllabus Version route."""
    route = _route(conn, syllabus_id, version_id)
    projection = _project(conn, route, _text(build_id, field="build_id"))
    if projection is not None:
        _, publications, error = _active_publications(conn, route)
        projection["current"] = _manifest_is_current(
            projection["manifest_id"], publications
        )
    return projection


def latest(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
) -> dict[str, Any] | None:
    """Read the latest explicitly requested build for this exact version."""
    route = _route(conn, syllabus_id, version_id)
    row = conn.execute(
        "SELECT id FROM syllabus_knowledge_build"
        " WHERE version_id = %s ORDER BY request_seq DESC LIMIT 1",
        (route["version_id"],),
    ).fetchone()
    if row is None:
        return None
    projection = _project(conn, route, row[0])
    if projection is not None:
        _, publications, error = _active_publications(conn, route)
        projection["current"] = _manifest_is_current(
            projection["manifest_id"], publications
        )
    return projection


def _claim_next(
    conn: psycopg.Connection,
    *,
    build_id: str | None = None,
) -> dict[str, Any] | None:
    token = uuid.uuid4().hex
    row = conn.execute(
        "WITH candidate AS ("
        " SELECT id, created_at FROM syllabus_knowledge_build"
        " WHERE (%s::text IS NULL OR id = %s)"
        "   AND status IN ('queued', 'running')"
        "   AND available_at <= clock_timestamp()"
        "   AND (claim_token IS NULL OR lease_expires_at <= clock_timestamp())"
        " ORDER BY available_at, created_at, id"
        " FOR UPDATE SKIP LOCKED LIMIT 1"
        ")"
        " UPDATE syllabus_knowledge_build build SET"
        " status = 'running', failure_code = NULL,"
        " claim_count = build.claim_count + 1, claimed_at = clock_timestamp(),"
        " claim_token = %s, lease_expires_at = clock_timestamp()"
        "   + (%s * interval '1 second'), updated_at = now()"
        " FROM candidate WHERE build.id = candidate.id"
        " RETURNING build.id, build.version_id, build.manifest_id, build.status,"
        " build.stage, build.last_launched_stage, build.diagnostics,"
        " build.claim_count, build.claim_token, build.lease_expires_at,"
        " candidate.created_at",
        (build_id, build_id, token, CLAIM_TTL_SECONDS),
    ).fetchone()
    conn.commit()
    if row is None:
        return None
    return dict(
        zip(
            (
                "id",
                "version_id",
                "manifest_id",
                "status",
                "stage",
                "last_launched_stage",
                "diagnostics",
                "claim_count",
                "claim_token",
                "lease_expires_at",
                "build_created_at",
            ),
            row,
        )
    )


def _diagnostics(claim: Mapping[str, Any], **changes: Any) -> dict[str, Any]:
    current = claim.get("diagnostics")
    result = dict(current) if isinstance(current, Mapping) else {}
    result.update(changes)
    return result


def _finish_claim(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    *,
    status: str,
    stage: str | None,
    diagnostics: Mapping[str, Any],
    failure_code: str | None = None,
    last_launched_stage: str | None = None,
) -> bool:
    row = conn.execute(
        "UPDATE syllabus_knowledge_build SET status = %s, stage = %s,"
        " failure_code = %s, diagnostics = %s,"
        " last_launched_stage = coalesce(%s, last_launched_stage),"
        " available_at = clock_timestamp() + (%s * interval '1 second'),"
        " claimed_at = NULL, claim_token = NULL, lease_expires_at = NULL,"
        " updated_at = now()"
        " WHERE id = %s AND claim_token = %s"
        " AND lease_expires_at > clock_timestamp() RETURNING id",
        (
            status,
            stage,
            failure_code,
            Jsonb(dict(diagnostics)),
            last_launched_stage,
            POLL_SECONDS,
            claim["id"],
            claim["claim_token"],
        ),
    ).fetchone()
    conn.commit()
    return row is not None


def _result(
    claim: Mapping[str, Any],
    *,
    action: str,
    status: str,
    stage: str | None,
    pid: int | None = None,
) -> dict[str, Any]:
    return {
        "action": action,
        "build_id": claim["id"],
        "manifest_id": claim["manifest_id"],
        "status": status,
        "stage": stage,
        "pid": pid,
        "claim_count": claim["claim_count"],
    }


def _attention(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    *,
    failure_code: str,
    message: str,
    stage: str | None,
    exception: str | None = None,
    facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    changes: dict[str, Any] = {
        "category": "attention",
        "last_action": "attention",
        "message": message,
        "pipeline_stage": stage,
    }
    if exception is not None:
        changes["exception"] = exception
    if facts is not None:
        changes["pipeline_stage_status"] = facts.get("status")
        changes["pipeline_run_id"] = facts.get("run_id")
    stored = _finish_claim(
        conn,
        claim,
        status="failed",
        stage=stage,
        failure_code=failure_code,
        diagnostics=_diagnostics(claim, **changes),
    )
    return _result(
        claim,
        action="attention" if stored else "claim_lost",
        status="failed",
        stage=stage,
    )


def _complete(snapshot: Mapping[str, Any]) -> bool:
    stages = snapshot.get("stages")
    return (
        isinstance(stages, Mapping)
        and all(
            stages.get(stage, {}).get("status") == "done"
            for stage in kc_pipeline.SHARED_STAGES
        )
        and snapshot.get("next_stage") is None
    )


def _failed_stage(
    snapshot: Mapping[str, Any],
) -> tuple[str, Mapping[str, Any]] | None:
    stages = snapshot.get("stages")
    if not isinstance(stages, Mapping):
        return None
    for stage in kc_pipeline.SHARED_STAGES:
        facts = stages.get(stage)
        if isinstance(facts, Mapping) and facts.get("status") == "failed":
            return stage, facts
    return None


def _attempt_finished_at(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    stage: str,
    facts: Mapping[str, Any],
):
    cutoffs = [
        row[0]
        for row in conn.execute(
            "SELECT updated_at FROM syllabus_knowledge_build"
            " WHERE manifest_id = %s AND id <> %s AND status = 'failed'"
            " AND stage = %s ORDER BY updated_at DESC LIMIT 1",
            (claim["manifest_id"], claim["id"], stage),
        ).fetchall()
    ]
    run_id = facts.get("run_id")
    if isinstance(run_id, str):
        row = conn.execute(
            "SELECT finished_at FROM run WHERE id = %s"
            " AND status IN ('done', 'failed') AND finished_at IS NOT NULL",
            (run_id,),
        ).fetchone()
        if row is not None:
            cutoffs.append(row[0])
    row = conn.execute(
        "SELECT finished_at FROM run"
        " WHERE stage = %s AND status IN ('done', 'failed')"
        " AND finished_at IS NOT NULL"
        " AND params#>>'{pipeline_lease,scope_key}' = %s"
        " ORDER BY started_at DESC, id DESC LIMIT 1",
        (stage, f"corpus:{claim['manifest_id']}"),
    ).fetchone()
    if row is not None:
        cutoffs.append(row[0])
    return max(cutoffs) if cutoffs else None


def _explicit_retry_authorized(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    stage: str,
    facts: Mapping[str, Any],
) -> bool:
    if claim.get("last_launched_stage") == stage:
        return False
    cutoff = _attempt_finished_at(conn, claim, stage, facts)
    if cutoff is None:
        return facts.get("status") not in {"failed", "partial"}
    created_at = claim.get("build_created_at")
    return bool(created_at is not None and created_at > cutoff)


def _launch(
    conn: psycopg.Connection,
    target: kc_pipeline.CorpusManifestTarget,
    spawn: object,
) -> dict[str, Any]:
    if spawn is _DEFAULT_SPAWN:
        return kc_pipeline.advance(conn, target)
    if not callable(spawn):
        raise TypeError("spawn must be callable")
    return kc_pipeline.advance(conn, target, spawn=spawn)


def process_next(
    conn: psycopg.Connection,
    *,
    build_id: str | None = None,
    spawn: Callable | object = _DEFAULT_SPAWN,
) -> dict[str, Any] | None:
    """Claim one build and launch or observe at most one shared stage."""
    if build_id is not None:
        build_id = _text(build_id, field="build_id")
    claim = _claim_next(conn, build_id=build_id)
    if claim is None:
        return None
    target = kc_pipeline.CorpusManifestTarget(claim["manifest_id"])
    try:
        snapshot = _snapshot(conn, claim["manifest_id"])
    except (LookupError, RuntimeError, ValueError) as exc:
        return _attention(
            conn,
            claim,
            failure_code="manifest_unreadable",
            message=str(exc),
            stage=claim.get("stage"),
            exception=type(exc).__name__,
        )
    if _complete(snapshot):
        stored = _finish_claim(
            conn,
            claim,
            status="succeeded",
            stage=None,
            diagnostics=_diagnostics(
                claim,
                last_action="completed",
                shared_stage_count=len(kc_pipeline.SHARED_STAGES),
            ),
        )
        return _result(
            claim,
            action="completed" if stored else "claim_lost",
            status="succeeded",
            stage=None,
        )

    stage = snapshot.get("next_stage")
    if not isinstance(stage, str) or stage not in kc_pipeline.SHARED_STAGES:
        return _attention(
            conn,
            claim,
            failure_code="invalid_pipeline_projection",
            message="the corpus snapshot has no valid next shared stage",
            stage=None,
        )
    facts = snapshot["stages"][stage]
    if facts.get("status") == "running":
        stored = _finish_claim(
            conn,
            claim,
            status="running",
            stage=stage,
            diagnostics=_diagnostics(
                claim,
                last_action="observed",
                pipeline_stage=stage,
                pipeline_stage_status="running",
                pipeline_run_id=facts.get("run_id"),
            ),
        )
        return _result(
            claim,
            action="observed" if stored else "claim_lost",
            status="running",
            stage=stage,
        )
    failed = _failed_stage(snapshot)
    attempted_incomplete = (
        failed is not None
        or facts.get("status") == "partial"
        or claim.get("last_launched_stage") == stage
        or _attempt_finished_at(conn, claim, stage, facts) is not None
    )
    if attempted_incomplete and not _explicit_retry_authorized(
        conn, claim, stage, facts
    ):
        return _attention(
            conn,
            claim,
            failure_code=(
                "pipeline_stage_failed"
                if facts.get("status") == "failed"
                else "stage_ended_without_result"
            ),
            message=(
                f"shared pipeline stage {stage} ended without a complete result;"
                " a new explicit request created after that attempt is required"
            ),
            stage=stage,
            facts=facts,
        )
    try:
        launched = _launch(conn, target, spawn)
    except kc_pipeline.StepAlreadyRunning:
        refreshed = _snapshot(conn, claim["manifest_id"])
        refreshed_facts = refreshed.get("stages", {}).get(stage, {})
        stored = _finish_claim(
            conn,
            claim,
            status="running",
            stage=stage,
            diagnostics=_diagnostics(
                claim,
                last_action="observed",
                pipeline_stage=stage,
                pipeline_stage_status=refreshed_facts.get("status"),
                pipeline_run_id=refreshed_facts.get("run_id"),
            ),
        )
        return _result(
            claim,
            action="observed" if stored else "claim_lost",
            status="running",
            stage=stage,
        )
    except kc_pipeline.StepNotRunnable as exc:
        return _attention(
            conn,
            claim,
            failure_code="stage_not_runnable",
            message=str(exc),
            stage=stage,
            exception=type(exc).__name__,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _attention(
            conn,
            claim,
            failure_code="stage_launch_failed",
            message=str(exc),
            stage=stage,
            exception=type(exc).__name__,
        )
    stored = _finish_claim(
        conn,
        claim,
        status="running",
        stage=stage,
        last_launched_stage=stage,
        diagnostics=_diagnostics(
            claim,
            last_action="launched",
            pipeline_stage=stage,
            pipeline_stage_status=facts.get("status"),
            pipeline_lease_token=launched.get("lease_token"),
        ),
    )
    return _result(
        claim,
        action="launched" if stored else "claim_lost",
        status="running",
        stage=stage,
        pid=launched.get("pid"),
    )
