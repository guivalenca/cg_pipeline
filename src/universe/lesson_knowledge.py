"""Durable, explicitly requested KC work for one syllabus lesson."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Mapping
from typing import Any

import psycopg

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
    if counts["failed"]:
        return "failed", progress
    if work and counts["succeeded"] == len(work):
        return "succeeded", progress
    if counts["running"] or counts["succeeded"]:
        return "running", progress
    return "queued", progress


def _eligibility(
    conn: psycopg.Connection,
    route: Mapping[str, Any],
) -> tuple[list[tuple[str, str | None, bool]], dict[str, Publication], LessonKnowledgeNotReady | None]:
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


def _project(
    conn: psycopg.Connection,
    route: Mapping[str, Any],
    build_id: str,
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
        " diagnostics, created_at, updated_at"
        " FROM lesson_knowledge_work WHERE build_id = %s ORDER BY seq",
        (build_id,),
    ).fetchall()
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
            created_at,
            updated_at,
        ) in work_rows
    ]
    work_by_id = {item["id"]: item for item in work}

    reference_rows = conn.execute(
        "SELECT lr.seq, lr.reference_id, lr.work_id, lw.source_id,"
        " lw.snapshot_id, lw.artifact_id, lw.content_hash"
        " FROM lesson_knowledge_reference lr"
        " JOIN lesson_knowledge_work lw"
        "   ON lw.build_id = lr.build_id AND lw.id = lr.work_id"
        " WHERE lr.build_id = %s ORDER BY lr.seq",
        (build_id,),
    ).fetchall()
    references = []
    for seq, reference_id, work_id, source_id, snapshot_id, artifact_id, content_hash in reference_rows:
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
        "references": references,
        "work": work,
    }


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
    route = _route(conn, syllabus_id, version_id, lesson_id)
    reference_rows, publications, error = _eligibility(conn, route)
    row = conn.execute(
        "SELECT id FROM lesson_knowledge_build"
        " WHERE version_id = %s AND lesson_id = %s"
        " ORDER BY request_seq DESC LIMIT 1",
        (route["version_id"], route["lesson_id"]),
    ).fetchone()
    return {
        "syllabus_id": route["syllabus_id"],
        "version_id": route["version_id"],
        "lesson_id": route["lesson_id"],
        "lesson_title": route["lesson_title"],
        "active_reference_count": len(reference_rows),
        "publication_count": len(publications),
        "eligibility": _eligibility_projection(error),
        "latest_build": None if row is None else _project(conn, route, row[0]),
    }


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
