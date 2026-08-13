"""Durable, explicitly requested KC work for one syllabus lesson."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Mapping
from typing import Any

import psycopg

from universe import kc_pipeline
from universe.source_publication import Publication, current_many


class LessonKnowledgeNotReady(ValueError):
    """The current lesson projection cannot safely start local KC work."""

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
    lesson_id: str,
) -> dict[str, Any]:
    syllabus_id = _text(syllabus_id, field="syllabus_id")
    version_id = _text(version_id, field="version_id")
    lesson_id = _text(lesson_id, field="lesson_id")
    row = conn.execute(
        "SELECT sl.title, sl.is_hidden"
        " FROM syllabus_version sv"
        " JOIN syllabus_lesson sl ON sl.version_id = sv.id"
        " WHERE sv.syllabus_id = %s AND sv.id = %s AND sl.id = %s",
        (syllabus_id, version_id, lesson_id),
    ).fetchone()
    if row is None:
        raise LookupError(
            f"unknown lesson {lesson_id!r} for syllabus/version"
            f" {syllabus_id!r}/{version_id!r}"
        )
    return {
        "syllabus_id": syllabus_id,
        "version_id": version_id,
        "lesson_id": lesson_id,
        "lesson_title": row[0],
        "hidden": bool(row[1]),
    }


def _status(work: list[dict[str, Any]]) -> tuple[str, dict[str, int]]:
    counts = Counter(row["status"] for row in work)
    progress = {
        "total": len(work),
        "queued": counts["queued"],
        "running": counts["running"],
        "succeeded": counts["succeeded"],
        "failed": counts["failed"],
    }
    if counts["queued"] or counts["running"]:
        return "running" if counts["running"] or counts["succeeded"] else "queued", progress
    if counts["failed"]:
        return "failed", progress
    if work and counts["succeeded"] == len(work):
        return "succeeded", progress
    return "queued", progress


def _eligibility(
    conn: psycopg.Connection,
    route: Mapping[str, Any],
) -> tuple[
    list[tuple[str, str | None, bool]],
    dict[str, Publication],
    LessonKnowledgeNotReady | None,
]:
    if route["hidden"]:
        return [], {}, LessonKnowledgeNotReady(
            "lesson_hidden", "the lesson is hidden"
        )

    reference_rows = conn.execute(
        "SELECT sr.id, sr.source_id, coalesce(review.is_validated, false)"
        " FROM syllabus_source_reference sr"
        " LEFT JOIN syllabus_source_review review ON review.reference_id = sr.id"
        " WHERE sr.version_id = %s AND sr.lesson_id = %s AND NOT sr.is_hidden"
        " ORDER BY sr.seq, sr.id",
        (route["version_id"], route["lesson_id"]),
    ).fetchall()
    if not reference_rows:
        return [], {}, LessonKnowledgeNotReady(
            "no_active_references", "the lesson has no active source references"
        )

    unvalidated = tuple(
        reference_id
        for reference_id, _, validated in reference_rows
        if not validated
    )
    if unvalidated:
        return reference_rows, {}, LessonKnowledgeNotReady(
            "references_not_validated",
            "every active source reference must be validated",
            reference_ids=unvalidated,
        )
    without_source = tuple(
        reference_id
        for reference_id, source_id, _ in reference_rows
        if not source_id
    )
    if without_source:
        return reference_rows, {}, LessonKnowledgeNotReady(
            "references_without_source",
            "every active source reference must resolve to a Source",
            reference_ids=without_source,
        )

    source_ids = list(
        dict.fromkeys(source_id for _, source_id, _ in reference_rows if source_id)
    )
    publications = current_many(conn, source_ids)
    missing_sources = tuple(
        source_id for source_id in source_ids if source_id not in publications
    )
    if missing_sources:
        return reference_rows, publications, LessonKnowledgeNotReady(
            "publications_unavailable",
            "every active Source must have a current Source Publication",
            source_ids=missing_sources,
        )
    previous_sources = tuple(
        source_id
        for source_id in source_ids
        if publications[source_id].is_previous_attempt
    )
    if previous_sources:
        return reference_rows, publications, LessonKnowledgeNotReady(
            "publications_not_current",
            "some Source Publications belong to a previous attempt",
            source_ids=previous_sources,
        )
    return reference_rows, publications, None


def _eligibility_projection(
    error: LessonKnowledgeNotReady | None,
) -> dict[str, Any]:
    return {
        "eligible": error is None,
        "code": "ready" if error is None else error.code,
        "message": "lesson is ready for local KC work" if error is None else str(error),
        "reference_ids": [] if error is None else list(error.reference_ids),
        "source_ids": [] if error is None else list(error.source_ids),
    }


def _counter(
    diagnostics: Mapping[str, Any],
    field: str,
    *,
    maximum: int | None = None,
) -> int:
    try:
        value = max(int(diagnostics.get(field) or 0), 0)
    except (TypeError, ValueError):
        return 0
    return min(value, maximum) if maximum is not None else value


def _assemble_projection(
    conn: psycopg.Connection,
    route: Mapping[str, Any],
    build_id: str,
    build_row: tuple[Any, Any, Any],
    work_rows: list[tuple[Any, ...]],
    reference_rows: list[tuple[Any, ...]],
    *,
    include_snapshots: bool = True,
    current_artifacts: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    row = build_row
    work = [
        {
            "id": work_id,
            "seq": seq,
            "source_id": source_id,
            "snapshot_id": snapshot_id,
            "artifact_id": artifact_id,
            "content_hash": content_hash,
            "publication_is_previous_attempt": is_previous_attempt,
            "status": status,
            "stage": stage,
            "failure_code": failure_code,
            "diagnostics": dict(diagnostics or {}),
            "last_launched_stage": last_launched_stage,
            "created_at": created_at,
            "updated_at": updated_at,
            "reference_ids": [],
        }
        for (
            work_id,
            seq,
            source_id,
            snapshot_id,
            artifact_id,
            content_hash,
            is_previous_attempt,
            status,
            stage,
            failure_code,
            diagnostics,
            last_launched_stage,
            created_at,
            updated_at,
        ) in work_rows
    ]
    work_by_id = {item["id"]: item for item in work}

    references = []
    for (
        seq,
        reference_id,
        work_id,
        source_id,
        snapshot_id,
        artifact_id,
        content_hash,
    ) in reference_rows:
        references.append(
            {
                "seq": seq,
                "reference_id": reference_id,
                "work_id": work_id,
                "source_id": source_id,
                "snapshot_id": snapshot_id,
                "artifact_id": artifact_id,
                "content_hash": content_hash,
            }
        )
        if work_id in work_by_id:
            work_by_id[work_id]["reference_ids"].append(reference_id)

    if (
        not work
        or not references
        or [item["seq"] for item in work] != list(range(1, len(work) + 1))
        or [item["seq"] for item in references]
        != list(range(1, len(references) + 1))
        or any(not item["reference_ids"] for item in work)
    ):
        return None

    completed_stages = 0
    total_stages = len(kc_pipeline.LOCAL_STAGES) * len(work)
    for item in work:
        if not include_snapshots:
            diagnostics = item["diagnostics"]
            completed_stages += _counter(
                diagnostics,
                "completed_stage_count",
                maximum=len(kc_pipeline.LOCAL_STAGES),
            )
            item["kc_count"] = _counter(diagnostics, "kc_count")
            item["current"] = bool(
                current_artifacts is not None
                and current_artifacts.get(item["source_id"]) == item["artifact_id"]
                and not item["publication_is_previous_attempt"]
            )
            continue
        target = kc_pipeline.SourcePublicationTarget(
            item["source_id"], item["artifact_id"]
        )
        try:
            snapshot = kc_pipeline.read_publication_snapshot(
                conn,
                target,
                require_current=False,
            )
        except (LookupError, RuntimeError, ValueError) as exc:
            # Keep the durable request inspectable even if its pinned ledger
            # evidence was externally corrupted. The worker will fail closed;
            # the read model exposes the reason instead of inventing progress.
            item["snapshot"] = None
            item["snapshot_error"] = str(exc)
            item["current"] = False
            continue
        item["snapshot"] = snapshot
        item["snapshot_error"] = None
        item["current"] = bool(snapshot["source"].get("current"))
        item["kc_count"] = len(snapshot.get("components") or [])
        completed_stages += sum(
            snapshot["stages"].get(stage, {}).get("status") == "done"
            for stage in kc_pipeline.LOCAL_STAGES
        )

    status, progress = _status(work)
    return {
        "id": build_id,
        "syllabus_id": route["syllabus_id"],
        "version_id": route["version_id"],
        "lesson_id": route["lesson_id"],
        "lesson_title": route["lesson_title"],
        "request_key": row[0],
        "requested_by": row[1],
        "created_at": row[2],
        "status": status,
        "progress": progress,
        "stage_progress": {
            "completed": completed_stages,
            "total": total_stages,
        },
        "current": all(item["current"] for item in work),
        "references": references,
        "work": work,
    }


def _project(
    conn: psycopg.Connection,
    route: Mapping[str, Any],
    build_id: str,
    *,
    include_snapshots: bool = True,
    current_artifacts: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT request_key, requested_by, created_at"
        " FROM lesson_knowledge_build"
        " WHERE id = %s AND version_id = %s AND lesson_id = %s",
        (build_id, route["version_id"], route["lesson_id"]),
    ).fetchone()
    if row is None:
        return None
    work_rows = conn.execute(
        "SELECT id, seq, source_id, snapshot_id, artifact_id, content_hash,"
        " publication_is_previous_attempt, status, stage, failure_code,"
        " diagnostics, last_launched_stage, created_at, updated_at"
        " FROM lesson_knowledge_work WHERE build_id = %s ORDER BY seq",
        (build_id,),
    ).fetchall()
    reference_rows = conn.execute(
        "SELECT lr.seq, lr.reference_id, lr.work_id, lw.source_id,"
        " lw.snapshot_id, lw.artifact_id, lw.content_hash"
        " FROM lesson_knowledge_reference lr"
        " JOIN lesson_knowledge_work lw"
        "   ON lw.build_id = lr.build_id AND lw.id = lr.work_id"
        " WHERE lr.build_id = %s ORDER BY lr.seq",
        (build_id,),
    ).fetchall()
    return _assemble_projection(
        conn,
        route,
        build_id,
        row,
        work_rows,
        reference_rows,
        include_snapshots=include_snapshots,
        current_artifacts=current_artifacts,
    )


def _project_many_summaries(
    conn: psycopg.Connection,
    routes: Mapping[str, Mapping[str, Any]],
    build_rows: list[tuple[Any, ...]],
    *,
    current_artifacts: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    """Assemble latest lesson builds with three queries for any page size."""
    if not build_rows:
        return {}
    build_ids = [row[1] for row in build_rows]
    work_by_build: dict[str, list[tuple[Any, ...]]] = {
        build_id: [] for build_id in build_ids
    }
    for row in conn.execute(
        "SELECT build_id, id, seq, source_id, snapshot_id, artifact_id,"
        " content_hash, publication_is_previous_attempt, status, stage,"
        " failure_code, diagnostics, last_launched_stage, created_at, updated_at"
        " FROM lesson_knowledge_work WHERE build_id = ANY(%s)"
        " ORDER BY build_id, seq",
        (build_ids,),
    ).fetchall():
        work_by_build[row[0]].append(row[1:])

    references_by_build: dict[str, list[tuple[Any, ...]]] = {
        build_id: [] for build_id in build_ids
    }
    for row in conn.execute(
        "SELECT lr.build_id, lr.seq, lr.reference_id, lr.work_id, lw.source_id,"
        " lw.snapshot_id, lw.artifact_id, lw.content_hash"
        " FROM lesson_knowledge_reference lr"
        " JOIN lesson_knowledge_work lw"
        "   ON lw.build_id = lr.build_id AND lw.id = lr.work_id"
        " WHERE lr.build_id = ANY(%s) ORDER BY lr.build_id, lr.seq",
        (build_ids,),
    ).fetchall():
        references_by_build[row[0]].append(row[1:])

    projected: dict[str, dict[str, Any]] = {}
    for lesson_id, build_id, request_key, requested_by, created_at in build_rows:
        build = _assemble_projection(
            conn,
            routes[lesson_id],
            build_id,
            (request_key, requested_by, created_at),
            work_by_build[build_id],
            references_by_build[build_id],
            include_snapshots=False,
            current_artifacts=current_artifacts,
        )
        if build is not None:
            projected[lesson_id] = build
    return projected


def request(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
    lesson_id: str,
    request_key: str,
    *,
    actor: str,
) -> dict[str, Any]:
    """Queue one pinned lesson build; the route/key replay is idempotent."""
    route = _route(conn, syllabus_id, version_id, lesson_id)
    request_key = _text(request_key, field="request_key", limit=200)
    actor = _text(actor, field="actor", limit=200)

    existing = conn.execute(
        "SELECT id FROM lesson_knowledge_build"
        " WHERE version_id = %s AND lesson_id = %s AND request_key = %s",
        (route["version_id"], route["lesson_id"], request_key),
    ).fetchone()
    if existing is not None:
        replay = _project(conn, route, existing[0])
        if replay is None:
            raise RuntimeError(f"incomplete lesson knowledge build {existing[0]}")
        return replay

    reference_rows, publications, error = _eligibility(conn, route)
    if error is not None:
        raise error

    build_id = f"lesson-kc-build-{uuid.uuid4().hex}"
    publication_order: list[Publication] = []
    work_for_artifact: dict[str, tuple[str, int]] = {}
    for _, source_id, _ in reference_rows:
        publication = publications[source_id]
        if publication.artifact_id not in work_for_artifact:
            seq = len(publication_order) + 1
            work_for_artifact[publication.artifact_id] = (
                f"lesson-kc-work-{uuid.uuid4().hex}",
                seq,
            )
            publication_order.append(publication)

    with conn.transaction():
        inserted = conn.execute(
            "INSERT INTO lesson_knowledge_build"
            " (id, version_id, lesson_id, request_key, requested_by)"
            " VALUES (%s, %s, %s, %s, %s)"
            " ON CONFLICT (version_id, lesson_id, request_key) DO NOTHING"
            " RETURNING id",
            (
                build_id,
                route["version_id"],
                route["lesson_id"],
                request_key,
                actor,
            ),
        ).fetchone()
        if inserted is not None:
            with conn.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO lesson_knowledge_work"
                    " (id, build_id, seq, source_id, snapshot_id, artifact_id,"
                    "  content_hash, publication_is_previous_attempt)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        (
                            work_for_artifact[publication.artifact_id][0],
                            build_id,
                            work_for_artifact[publication.artifact_id][1],
                            publication.source_id,
                            publication.snapshot_id,
                            publication.artifact_id,
                            publication.content_hash,
                            publication.is_previous_attempt,
                        )
                        for publication in publication_order
                    ],
                )
                cursor.executemany(
                    "INSERT INTO lesson_knowledge_reference"
                    " (build_id, seq, reference_id, work_id)"
                    " VALUES (%s, %s, %s, %s)",
                    [
                        (
                            build_id,
                            seq,
                            reference_id,
                            work_for_artifact[publications[source_id].artifact_id][0],
                        )
                        for seq, (reference_id, source_id, _) in enumerate(
                            reference_rows, 1
                        )
                    ],
                )
        else:
            build_id = conn.execute(
                "SELECT id FROM lesson_knowledge_build"
                " WHERE version_id = %s AND lesson_id = %s AND request_key = %s",
                (route["version_id"], route["lesson_id"], request_key),
            ).fetchone()[0]

    projection = _project(conn, route, build_id)
    if projection is None:
        raise RuntimeError(f"incomplete lesson knowledge build {build_id}")
    return projection


def offer(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
    lesson_id: str,
) -> dict[str, Any]:
    """Project start eligibility and the latest build without requesting work."""
    projection = offer_many(
        conn,
        syllabus_id,
        version_id,
        [lesson_id],
    )[lesson_id]
    latest_build = projection.get("latest_build")
    if latest_build is not None:
        projection["latest_build"] = _project(
            conn,
            _route(conn, syllabus_id, version_id, lesson_id),
            latest_build["id"],
        )
    return projection


def offer_many(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
    lesson_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Project many lesson gates with one Source Publication resolution.

    A real imported syllabus has dozens of lessons.  This bulk read keeps the
    Syllabi page from turning one detail request into hundreds of publication
    queries while preserving the exact same per-reference gate as ``request``.
    """
    syllabus_id = _text(syllabus_id, field="syllabus_id")
    version_id = _text(version_id, field="version_id")
    lesson_ids = list(dict.fromkeys(
        _text(lesson_id, field="lesson_id") for lesson_id in lesson_ids
    ))
    if not lesson_ids:
        return {}
    owner = conn.execute(
        "SELECT 1 FROM syllabus_version WHERE syllabus_id = %s AND id = %s",
        (syllabus_id, version_id),
    ).fetchone()
    if owner is None:
        raise LookupError(
            f"unknown syllabus/version {syllabus_id!r}/{version_id!r}"
        )
    lesson_rows = conn.execute(
        "SELECT id, title, is_hidden FROM syllabus_lesson"
        " WHERE version_id = %s AND id = ANY(%s) ORDER BY seq, id",
        (version_id, lesson_ids),
    ).fetchall()
    routes = {
        lesson_id: {
            "syllabus_id": syllabus_id,
            "version_id": version_id,
            "lesson_id": lesson_id,
            "lesson_title": title,
            "hidden": bool(hidden),
        }
        for lesson_id, title, hidden in lesson_rows
    }
    missing = [lesson_id for lesson_id in lesson_ids if lesson_id not in routes]
    if missing:
        raise LookupError(
            "unknown lessons for syllabus/version: " + ", ".join(missing)
        )
    references_by_lesson: dict[str, list[tuple[str, str | None, bool]]] = {
        lesson_id: [] for lesson_id in lesson_ids
    }
    for lesson_id, reference_id, source_id, validated in conn.execute(
        "SELECT sr.lesson_id, sr.id, sr.source_id,"
        " coalesce(review.is_validated, false)"
        " FROM syllabus_source_reference sr"
        " LEFT JOIN syllabus_source_review review ON review.reference_id = sr.id"
        " WHERE sr.version_id = %s AND sr.lesson_id = ANY(%s)"
        " AND NOT sr.is_hidden ORDER BY sr.lesson_id, sr.seq, sr.id",
        (version_id, lesson_ids),
    ).fetchall():
        references_by_lesson[lesson_id].append(
            (reference_id, source_id, bool(validated))
        )
    source_ids = list(dict.fromkeys(
        source_id
        for lesson_id, rows in references_by_lesson.items()
        if not routes[lesson_id]["hidden"]
        for _, source_id, _ in rows
        if source_id
    ))
    publications = current_many(conn, source_ids)
    latest_rows = conn.execute(
        "SELECT DISTINCT ON (lesson_id) lesson_id, id, request_key,"
        " requested_by, created_at FROM lesson_knowledge_build"
        " WHERE version_id = %s AND lesson_id = ANY(%s)"
        " ORDER BY lesson_id, request_seq DESC",
        (version_id, lesson_ids),
    ).fetchall()
    latest_builds = _project_many_summaries(
        conn,
        routes,
        latest_rows,
        current_artifacts={
            source_id: publication.artifact_id
            for source_id, publication in publications.items()
            if not publication.is_previous_attempt
        },
    )
    projected: dict[str, dict[str, Any]] = {}
    for lesson_id in lesson_ids:
        route = routes[lesson_id]
        reference_rows = references_by_lesson[lesson_id]
        if route["hidden"]:
            error = LessonKnowledgeNotReady("lesson_hidden", "the lesson is hidden")
        elif not reference_rows:
            error = LessonKnowledgeNotReady(
                "no_active_references",
                "the lesson has no active source references",
            )
        else:
            unvalidated = tuple(
                reference_id
                for reference_id, _, validated in reference_rows
                if not validated
            )
            without_source = tuple(
                reference_id
                for reference_id, source_id, _ in reference_rows
                if not source_id
            )
            lesson_sources = list(dict.fromkeys(
                source_id for _, source_id, _ in reference_rows if source_id
            ))
            missing_sources = tuple(
                source_id
                for source_id in lesson_sources
                if source_id not in publications
            )
            previous_sources = tuple(
                source_id
                for source_id in lesson_sources
                if source_id in publications
                and publications[source_id].is_previous_attempt
            )
            if unvalidated:
                error = LessonKnowledgeNotReady(
                    "references_not_validated",
                    "every active source reference must be validated",
                    reference_ids=unvalidated,
                )
            elif without_source:
                error = LessonKnowledgeNotReady(
                    "references_without_source",
                    "every active source reference must resolve to a Source",
                    reference_ids=without_source,
                )
            elif missing_sources:
                error = LessonKnowledgeNotReady(
                    "publications_unavailable",
                    "every active Source must have a current Source Publication",
                    source_ids=missing_sources,
                )
            elif previous_sources:
                error = LessonKnowledgeNotReady(
                    "publications_not_current",
                    "some Source Publications belong to a previous attempt",
                    source_ids=previous_sources,
                )
            else:
                error = None
        visible_reference_rows = [] if route["hidden"] else reference_rows
        lesson_source_ids = {
            source_id
            for _, source_id, _ in visible_reference_rows
            if source_id
        }
        projected[lesson_id] = {
            "syllabus_id": syllabus_id,
            "version_id": version_id,
            "lesson_id": lesson_id,
            "lesson_title": route["lesson_title"],
            "active_reference_count": len(visible_reference_rows),
            "publication_count": sum(
                source_id in publications for source_id in lesson_source_ids
            ),
            "eligibility": _eligibility_projection(error),
            "latest_build": latest_builds.get(lesson_id),
        }
    return projected


def read(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
    lesson_id: str,
    build_id: str,
) -> dict[str, Any] | None:
    """Read a build only through its owning syllabus/version/lesson route."""
    route = _route(conn, syllabus_id, version_id, lesson_id)
    build_id = _text(build_id, field="build_id")
    return _project(conn, route, build_id)


def latest(
    conn: psycopg.Connection,
    syllabus_id: str,
    version_id: str,
    lesson_id: str,
) -> dict[str, Any] | None:
    """Read the latest explicitly requested build for an owned lesson."""
    route = _route(conn, syllabus_id, version_id, lesson_id)
    row = conn.execute(
        "SELECT id FROM lesson_knowledge_build"
        " WHERE version_id = %s AND lesson_id = %s"
        " ORDER BY request_seq DESC LIMIT 1",
        (route["version_id"], route["lesson_id"]),
    ).fetchone()
    return None if row is None else _project(conn, route, row[0])


def read_by_id(
    conn: psycopg.Connection,
    build_id: str,
) -> dict[str, Any] | None:
    """Read one build after resolving its immutable route ownership."""
    build_id = _text(build_id, field="build_id")
    row = conn.execute(
        "SELECT sv.syllabus_id, build.version_id, build.lesson_id"
        " FROM lesson_knowledge_build build"
        " JOIN syllabus_version sv ON sv.id = build.version_id"
        " WHERE build.id = %s",
        (build_id,),
    ).fetchone()
    if row is None:
        return None
    return read(conn, row[0], row[1], row[2], build_id)
