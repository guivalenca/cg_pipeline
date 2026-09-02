"""Durable, explicitly requested creation work for one syllabus Lesson."""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

import psycopg

from universe.source_publication import current_many


class LessonBuildNotReady(ValueError):
    """The current Lesson projection cannot safely start creation work."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _route(
    conn: psycopg.Connection,
    *,
    syllabus_id: str,
    version_id: str,
    lesson_id: str,
) -> tuple[str, bool]:
    row = conn.execute(
        "SELECT lesson.title, lesson.is_hidden"
        " FROM syllabus_version version"
        " JOIN syllabus_lesson lesson ON lesson.version_id = version.id"
        " WHERE version.syllabus_id = %s AND version.id = %s"
        " AND lesson.id = %s",
        (syllabus_id, version_id, lesson_id),
    ).fetchone()
    if row is None:
        raise LookupError(
            f"unknown Lesson {lesson_id!r} for {syllabus_id!r}/{version_id!r}"
        )
    return row[0], bool(row[1])


def _pinned_publications(
    conn: psycopg.Connection,
    *,
    version_id: str,
    lesson_id: str,
) -> list:
    rows = conn.execute(
        "SELECT reference.id, reference.source_id,"
        " coalesce(review.is_validated, false), review.validated_artifact_id,"
        " review.validated_content_hash"
        " FROM syllabus_source_reference reference"
        " LEFT JOIN syllabus_source_review review"
        " ON review.reference_id = reference.id"
        " WHERE reference.version_id = %s AND reference.lesson_id = %s"
        " AND NOT reference.is_hidden ORDER BY reference.seq, reference.id",
        (version_id, lesson_id),
    ).fetchall()
    if not rows:
        raise LessonBuildNotReady(
            "no_active_references", "the Lesson has no active Source References"
        )
    if any(source_id is None for _, source_id, *_ in rows):
        raise LessonBuildNotReady(
            "references_without_source",
            "every active Source Reference must resolve to a Source",
        )
    source_ids = list(dict.fromkeys(source_id for _, source_id, *_ in rows))
    publications = current_many(conn, source_ids)
    if any(source_id not in publications for source_id in source_ids):
        raise LessonBuildNotReady(
            "publications_unavailable",
            "every active Source must have a Source Publication",
        )
    if any(publications[source_id].is_previous_attempt for source_id in source_ids):
        raise LessonBuildNotReady(
            "publications_not_current",
            "every active Source Publication must belong to its current attempt",
        )
    if any(
        not validated
        or publications[source_id].artifact_id != validated_artifact_id
        or publications[source_id].content_hash != validated_content_hash
        for _, source_id, validated, validated_artifact_id, validated_content_hash in rows
    ):
        raise LessonBuildNotReady(
            "references_not_validated",
            "every active Source Publication must be validated",
        )
    return [publications[source_id] for source_id in source_ids]


def _status(work: list[dict[str, Any]]) -> str:
    counts = Counter(row["status"] for row in work)
    if counts["running"]:
        return "running"
    if counts["queued"]:
        return "queued"
    if counts["failed"]:
        return "failed"
    return "succeeded" if work else "queued"


def read(conn: psycopg.Connection, build_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT version.syllabus_id, build.version_id, build.lesson_id,"
        " lesson.title, build.request_key, build.requested_by, build.created_at"
        " FROM lesson_build build"
        " JOIN syllabus_version version ON version.id = build.version_id"
        " JOIN syllabus_lesson lesson"
        " ON lesson.version_id = build.version_id AND lesson.id = build.lesson_id"
        " WHERE build.id = %s",
        (build_id,),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown Lesson build {build_id!r}")
    work = [
        dict(
            zip(
                (
                    "id",
                    "seq",
                    "source_id",
                    "snapshot_id",
                    "artifact_id",
                    "content_hash",
                    "status",
                    "stage",
                ),
                work_row,
            )
        )
        for work_row in conn.execute(
            "SELECT id, seq, source_id, snapshot_id, artifact_id, content_hash,"
            " status, stage FROM lesson_build_work"
            " WHERE build_id = %s ORDER BY seq",
            (build_id,),
        ).fetchall()
    ]
    return {
        "id": build_id,
        "syllabus_id": row[0],
        "version_id": row[1],
        "lesson_id": row[2],
        "lesson_title": row[3],
        "request_key": row[4],
        "requested_by": row[5],
        "created_at": row[6],
        "status": _status(work),
        "work": work,
    }


def request(
    conn: psycopg.Connection,
    *,
    syllabus_id: str,
    version_id: str,
    lesson_id: str,
    request_key: str,
    requested_by: str = "founder",
) -> dict[str, Any]:
    """Pin current validated Source Publications into one immutable build."""
    lesson_title, hidden = _route(
        conn,
        syllabus_id=syllabus_id,
        version_id=version_id,
        lesson_id=lesson_id,
    )
    if hidden:
        raise LessonBuildNotReady("lesson_hidden", "the Lesson is hidden")
    request_key = str(request_key or "").strip()
    requested_by = str(requested_by or "").strip()
    if not request_key:
        raise ValueError("request_key must be a non-empty string")
    if not requested_by:
        raise ValueError("requested_by must be a non-empty string")
    existing = conn.execute(
        "SELECT id FROM lesson_build WHERE version_id = %s AND lesson_id = %s"
        " AND request_key = %s",
        (version_id, lesson_id, request_key),
    ).fetchone()
    if existing is not None:
        return read(conn, existing[0])

    publications = _pinned_publications(
        conn, version_id=version_id, lesson_id=lesson_id
    )
    build_id = f"lesson-build-{uuid.uuid4().hex}"
    conn.execute(
        "INSERT INTO lesson_build"
        " (id, version_id, lesson_id, request_key, requested_by)"
        " VALUES (%s, %s, %s, %s, %s)",
        (build_id, version_id, lesson_id, request_key, requested_by),
    )
    for seq, publication in enumerate(publications, 1):
        conn.execute(
            "INSERT INTO lesson_build_work"
            " (id, build_id, seq, source_id, snapshot_id, artifact_id, content_hash)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                f"lesson-work-{uuid.uuid4().hex}",
                build_id,
                seq,
                publication.source_id,
                publication.snapshot_id,
                publication.artifact_id,
                publication.content_hash,
            ),
        )
    conn.commit()
    result = read(conn, build_id)
    result["lesson_title"] = lesson_title
    return result
