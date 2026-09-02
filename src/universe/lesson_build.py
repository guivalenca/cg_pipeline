"""Durable, explicitly requested creation work for one syllabus Lesson."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

import psycopg
from psycopg.types.json import Jsonb

from concept_graph_creation.runtime.stage_runner import ModelRouter
from universe import lesson_build_identity, lesson_build_plan
from universe.source_publication import Publication, current_many


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class LessonBuildNotReady(ValueError):
    """The current Lesson projection cannot safely start creation work."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _prompt_manifest() -> dict[str, dict[str, Any]]:
    result = {}
    implementation_sha256 = lesson_build_identity.creation_implementation_sha256(
        PROJECT_ROOT
    )
    for stage in lesson_build_plan.registered_stages():
        entry: dict[str, Any] = {
            "path": stage.prompt_path,
            "implementation_sha256": implementation_sha256,
        }
        if stage.prompt_path:
            path = PROJECT_ROOT / stage.prompt_path
            entry["sha256"] = lesson_build_identity.path_sha256(path)
        result[stage.name] = entry
    return result


def _routing_manifest() -> dict[str, dict[str, Any]]:
    return {
        alias: {
            "provider": route.provider,
            "model": route.model,
            "thinking_enabled": route.thinking_enabled,
            "reasoning_effort": route.reasoning_effort,
            "provider_sort": route.provider_sort,
            "allow_provider_fallbacks": route.allow_provider_fallbacks,
            "require_provider_parameters": route.require_provider_parameters,
        }
        for alias, route in sorted(ModelRouter.default().routes.items())
    }


def _route(
    conn: psycopg.Connection,
    *,
    syllabus_id: str,
    version_id: str,
    lesson_id: str,
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT lesson.title, lesson.is_hidden, lesson.kind, lesson.description,"
        " lesson.subjects, lesson.subject, lesson.lesson_date, lesson.seq,"
        " syllabus.title, subject.graph_id, syllabus.institution_id, lesson.week,"
        " lesson.fields, lesson.activity_uuid, lesson.folder_uuid,"
        " lesson.week_order, lesson.activity_order"
        " FROM syllabus_version version"
        " JOIN syllabus ON syllabus.id = version.syllabus_id"
        " JOIN syllabus_lesson lesson ON lesson.version_id = version.id"
        " LEFT JOIN syllabus_subject subject"
        " ON subject.syllabus_id = syllabus.id"
        " AND subject.lesson_subject_code = lesson.subject"
        " WHERE version.syllabus_id = %s AND version.id = %s"
        " AND lesson.id = %s",
        (syllabus_id, version_id, lesson_id),
    ).fetchone()
    if row is None:
        raise LookupError(
            f"unknown Lesson {lesson_id!r} for {syllabus_id!r}/{version_id!r}"
        )
    return {
        "id": lesson_id,
        "title": row[0],
        "is_hidden": bool(row[1]),
        "kind": row[2],
        "description": row[3],
        "subjects": list(row[4] or []),
        "subject": row[5],
        "date": row[6].isoformat() if row[6] else None,
        "seq": row[7],
        "syllabus_title": row[8],
        "subject_graph_id": row[9],
        "institution_id": row[10],
        "week": row[11],
        "fields": row[12] or {},
        "activity_uuid": row[13],
        "folder_uuid": row[14],
        "week_order": row[15],
        "activity_order": row[16],
    }


def _selected_rows(
    conn: psycopg.Connection,
    *,
    version_id: str,
    lesson_id: str,
    reference_ids: Iterable[str] | None,
) -> list[tuple]:
    rows = conn.execute(
        "SELECT reference.id, reference.source_id, reference.title,"
        " reference.description, reference.url, reference.media_type,"
        " reference.resource_code, reference.fields, reference.seq,"
        " coalesce(review.is_validated, false), review.validated_artifact_id,"
        " review.validated_content_hash"
        " FROM syllabus_source_reference reference"
        " LEFT JOIN syllabus_source_review review ON review.reference_id = reference.id"
        " WHERE reference.version_id = %s AND reference.lesson_id = %s"
        " AND NOT reference.is_hidden ORDER BY reference.seq, reference.id",
        (version_id, lesson_id),
    ).fetchall()
    requested = None if reference_ids is None else [str(value) for value in reference_ids]
    if requested is not None:
        if not requested or any(not value.strip() for value in requested):
            raise LessonBuildNotReady(
                "no_selected_references", "select at least one Source Publication"
            )
        if len(set(requested)) != len(requested):
            raise ValueError("reference_ids must not contain duplicates")
        by_id = {row[0]: row for row in rows}
        missing = [value for value in requested if value not in by_id]
        if missing:
            raise LessonBuildNotReady(
                "references_not_visible",
                "every selected Source Reference must be visible in this Lesson",
            )
        rows = [by_id[value] for value in requested]
    if not rows:
        raise LessonBuildNotReady(
            "no_active_references", "the Lesson has no selected Source References"
        )
    return rows


def _pinned_publications(
    conn: psycopg.Connection,
    *,
    version_id: str,
    lesson_id: str,
    reference_ids: Iterable[str] | None = None,
) -> list[tuple[tuple, Publication]]:
    rows = _selected_rows(
        conn,
        version_id=version_id,
        lesson_id=lesson_id,
        reference_ids=reference_ids,
    )
    if any(row[1] is None for row in rows):
        raise LessonBuildNotReady(
            "references_without_source",
            "every selected Source Reference must resolve to a Source",
        )
    source_ids = list(dict.fromkeys(row[1] for row in rows))
    publications = current_many(conn, source_ids)
    if any(source_id not in publications for source_id in source_ids):
        raise LessonBuildNotReady(
            "publications_unavailable",
            "every selected Source must have a Source Publication",
        )
    if any(publications[source_id].is_previous_attempt for source_id in source_ids):
        raise LessonBuildNotReady(
            "publications_not_current",
            "every selected Source Publication must belong to its current attempt",
        )
    if any(
        not row[9]
        or publications[row[1]].artifact_id != row[10]
        or publications[row[1]].content_hash != row[11]
        for row in rows
    ):
        raise LessonBuildNotReady(
            "references_not_validated",
            "every selected Source Publication must be validated",
        )
    return [(row, publications[row[1]]) for row in rows]


def _status(work: list[dict[str, Any]], stored: str | None = None) -> str:
    if stored in {"failed", "succeeded"}:
        return stored
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
        " lesson.title, build.request_key, build.requested_by, build.created_at,"
        " build.status, build.manifest, build.manifest_sha256, build.lineage_id,"
        " build.previous_build_id, build.failure_code, build.failure_message"
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
                    "id", "seq", "source_id", "snapshot_id", "artifact_id",
                    "content_hash", "status", "stage",
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
    checkpoints = [
        {
            "id": item[0], "stage": item[1], "family": item[2], "path": item[3],
            "content_sha256": item[4], "stage_fingerprint": item[5],
            "is_stage_result": item[6], "created_at": item[7],
        }
        for item in conn.execute(
            "SELECT id, stage, family, path, content_sha256, stage_fingerprint,"
            " is_stage_result, created_at FROM lesson_build_checkpoint"
            " WHERE build_id = %s ORDER BY created_at, path",
            (build_id,),
        ).fetchall()
    ]
    attempts = [
        {
            "id": item[0], "stage": item[1], "requested_model": item[2],
            "response_model": item[3], "provider": item[4],
            "generation_id": item[5], "outcome": item[6], "usage": item[7] or {},
            "duration_ms": item[8],
        }
        for item in conn.execute(
            "SELECT item.id, run.stage, item.requested_model, item.response_model,"
            " item.provider, item.generation_id, item.outcome, item.usage,"
            " item.duration_ms FROM run_item item JOIN run ON run.id = item.run_id"
            " WHERE item.lesson_build_id = %s ORDER BY item.created_at, item.id",
            (build_id,),
        ).fetchall()
    ]
    cost = 0.0
    tokens = 0
    for attempt in attempts:
        usage = attempt["usage"]
        raw_cost = usage.get("cost", usage.get("total_cost", 0))
        raw_tokens = usage.get("total_tokens", 0)
        if isinstance(raw_cost, (int, float)) and not isinstance(raw_cost, bool):
            cost += float(raw_cost)
        if isinstance(raw_tokens, (int, float)) and not isinstance(raw_tokens, bool):
            tokens += int(raw_tokens)
    return {
        "id": build_id, "syllabus_id": row[0], "version_id": row[1],
        "lesson_id": row[2], "lesson_title": row[3], "request_key": row[4],
        "requested_by": row[5], "created_at": row[6],
        "status": _status(work, row[7]), "manifest": row[8],
        "manifest_sha256": row[9], "lineage_id": row[10],
        "previous_build_id": row[11], "failure_code": row[12],
        "failure_message": row[13], "work": work, "checkpoints": checkpoints,
        "attempts": attempts,
        "usage": {"calls": len(attempts), "cost_usd": round(cost, 10), "total_tokens": tokens},
        "stages": [
            {"name": stage.name, "label": stage.label}
            for stage in lesson_build_plan.registered_stages()
        ],
    }


def offer(
    conn: psycopg.Connection,
    *, syllabus_id: str, version_id: str, lesson_id: str,
) -> dict[str, Any]:
    lesson = _route(
        conn, syllabus_id=syllabus_id, version_id=version_id, lesson_id=lesson_id
    )
    try:
        rows = _selected_rows(
            conn, version_id=version_id, lesson_id=lesson_id, reference_ids=None
        )
    except LessonBuildNotReady as exc:
        if exc.code != "no_active_references":
            raise
        rows = []
    source_ids = [row[1] for row in rows if row[1]]
    publications = current_many(conn, list(dict.fromkeys(source_ids)))
    references = []
    for row in rows:
        publication = publications.get(row[1])
        eligible = bool(
            publication and not publication.is_previous_attempt and row[9]
            and publication.artifact_id == row[10]
            and publication.content_hash == row[11]
        )
        references.append(
            {"reference_id": row[0], "title": row[2], "eligible": eligible, "selected": eligible}
        )
    latest = conn.execute(
        "SELECT id FROM lesson_build WHERE version_id = %s AND lesson_id = %s"
        " ORDER BY request_seq DESC LIMIT 1", (version_id, lesson_id),
    ).fetchone()
    return {
        "lesson": {key: lesson[key] for key in ("id", "title", "kind")},
        "references": references,
        "latest_build": read(conn, latest[0]) if latest else None,
    }


def request(
    conn: psycopg.Connection,
    *,
    syllabus_id: str,
    version_id: str,
    lesson_id: str,
    request_key: str,
    reference_ids: Iterable[str] | None = None,
    requested_by: str = "founder",
    previous_build_id: str | None = None,
) -> dict[str, Any]:
    """Pin selected current validated Source Publications into one immutable build."""
    lesson = _route(
        conn, syllabus_id=syllabus_id, version_id=version_id, lesson_id=lesson_id
    )
    if lesson["is_hidden"]:
        raise LessonBuildNotReady("lesson_hidden", "the Lesson is hidden")
    request_key = str(request_key or "").strip()
    requested_by = str(requested_by or "").strip()
    if not request_key:
        raise ValueError("request_key must be a non-empty string")
    if not requested_by:
        raise ValueError("requested_by must be a non-empty string")
    if reference_ids is None:
        raise LessonBuildNotReady(
            "no_selected_references",
            "reference_ids must contain the operator-selected Source References",
        )
    conn.execute(
        "SELECT id FROM syllabus_lesson WHERE version_id = %s AND id = %s FOR UPDATE",
        (version_id, lesson_id),
    )
    existing = conn.execute(
        "SELECT id FROM lesson_build WHERE version_id = %s AND lesson_id = %s"
        " AND request_key = %s", (version_id, lesson_id, request_key),
    ).fetchone()
    if existing is not None:
        return read(conn, existing[0])
    pinned = _pinned_publications(
        conn, version_id=version_id, lesson_id=lesson_id, reference_ids=reference_ids,
    )
    active = conn.execute(
        "SELECT id FROM lesson_build WHERE version_id = %s AND lesson_id = %s"
        " AND is_active FOR UPDATE", (version_id, lesson_id),
    ).fetchone()
    if active is not None:
        raise LessonBuildNotReady(
            "build_already_active", "this Lesson already has an active build"
        )
    build_id = f"lesson-build-{uuid.uuid4().hex}"
    lineage_id = f"lesson-lineage-{uuid.uuid4().hex}"
    manifest_references = []
    for seq, (row, publication) in enumerate(pinned, 1):
        manifest_references.append(
            {
                "seq": seq, "reference_id": row[0], "title": row[2],
                "description": row[3], "url": row[4], "media_type": row[5],
                "resource_code": row[6], "fields": row[7] or {},
                "publication": {
                    "source_id": publication.source_id,
                    "snapshot_id": publication.snapshot_id,
                    "artifact_id": publication.artifact_id,
                    "content_hash": publication.content_hash,
                    "created_at": publication.created_at.isoformat(),
                    "language": publication.metadata.get("caption_language"),
                },
            }
        )
    manifest = {
        "schema_version": "lesson_build_manifest.v1", "lineage_id": lineage_id,
        "syllabus": {
            "id": syllabus_id, "title": lesson["syllabus_title"],
            "version_id": version_id, "institution_id": lesson["institution_id"],
        },
        "lesson": {
            "id": lesson_id, "title": lesson["title"], "kind": lesson["kind"],
            "description": lesson["description"], "subjects": lesson["subjects"],
            "lesson_subject_code": lesson["subject"],
            "subject_graph_id": lesson["subject_graph_id"],
            "week": lesson["week"], "seq": lesson["seq"],
            "date": lesson["date"], "fields": lesson["fields"],
            "activity_uuid": lesson["activity_uuid"],
            "folder_uuid": lesson["folder_uuid"],
            "week_order": lesson["week_order"],
            "activity_order": lesson["activity_order"],
        },
        "references": manifest_references, "prompts": _prompt_manifest(),
        "routing": _routing_manifest(),
    }
    manifest_sha256 = _sha256(manifest)
    conn.execute(
        "INSERT INTO lesson_build"
        " (id, version_id, lesson_id, request_key, requested_by, manifest,"
        " manifest_sha256, lineage_id, previous_build_id)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (build_id, version_id, lesson_id, request_key, requested_by, Jsonb(manifest),
         manifest_sha256, lineage_id, previous_build_id),
    )
    work_by_artifact: dict[str, str] = {}
    for seq, (row, publication) in enumerate(pinned, 1):
        work_id = work_by_artifact.get(publication.artifact_id)
        if work_id is None:
            work_id = f"lesson-work-{uuid.uuid4().hex}"
            work_by_artifact[publication.artifact_id] = work_id
            conn.execute(
                "INSERT INTO lesson_build_work"
                " (id, build_id, seq, source_id, snapshot_id, artifact_id, content_hash)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (work_id, build_id, len(work_by_artifact), publication.source_id,
                 publication.snapshot_id, publication.artifact_id,
                 publication.content_hash),
            )
        conn.execute(
            "INSERT INTO lesson_build_reference"
            " (build_id, seq, reference_id, work_id) VALUES (%s, %s, %s, %s)",
            (build_id, seq, row[0], work_id),
        )
    conn.commit()
    return read(conn, build_id)


def resume(conn: psycopg.Connection, build_id: str) -> dict[str, Any]:
    """Resume the same checkpoint lineage after an explicit failure."""
    row = conn.execute(
        "SELECT status, version_id, lesson_id FROM lesson_build"
        " WHERE id = %s FOR UPDATE", (build_id,)
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown Lesson build {build_id!r}")
    if row[0] != "failed":
        raise LessonBuildNotReady("build_not_failed", "only a failed build can resume")
    active = conn.execute(
        "SELECT id FROM lesson_build WHERE version_id = %s AND lesson_id = %s"
        " AND is_active AND id <> %s",
        (row[1], row[2], build_id),
    ).fetchone()
    if active is not None:
        raise LessonBuildNotReady(
            "build_already_active", "this Lesson already has an active build"
        )
    conn.execute(
        "UPDATE lesson_build SET status = 'queued', is_active = true,"
        " failure_code = NULL, failure_message = NULL, finished_at = NULL"
        " WHERE id = %s", (build_id,),
    )
    conn.execute(
        "UPDATE lesson_build_work SET status = 'queued', stage = NULL,"
        " failure_code = NULL, available_at = now(), claim_token = NULL,"
        " claimed_at = NULL, lease_expires_at = NULL WHERE build_id = %s", (build_id,),
    )
    conn.commit()
    return read(conn, build_id)


def regenerate(
    conn: psycopg.Connection, build_id: str, *, request_key: str,
    requested_by: str = "founder",
) -> dict[str, Any]:
    """Start a fresh lineage from the original frozen reference selection."""
    prior = read(conn, build_id)
    request_key = str(request_key or "").strip()
    requested_by = str(requested_by or "").strip()
    if not request_key or not requested_by:
        raise ValueError("request_key and requested_by must be non-empty strings")
    conn.execute(
        "SELECT id FROM syllabus_lesson WHERE version_id = %s AND id = %s FOR UPDATE",
        (prior["version_id"], prior["lesson_id"]),
    )
    existing = conn.execute(
        "SELECT id FROM lesson_build WHERE version_id = %s AND lesson_id = %s"
        " AND request_key = %s",
        (prior["version_id"], prior["lesson_id"], request_key),
    ).fetchone()
    if existing is not None:
        return read(conn, existing[0])
    active = conn.execute(
        "SELECT id FROM lesson_build WHERE version_id = %s AND lesson_id = %s"
        " AND is_active FOR UPDATE",
        (prior["version_id"], prior["lesson_id"]),
    ).fetchone()
    if active is not None:
        raise LessonBuildNotReady(
            "build_already_active", "this Lesson already has an active build"
        )
    new_build_id = f"lesson-build-{uuid.uuid4().hex}"
    lineage_id = f"lesson-lineage-{uuid.uuid4().hex}"
    manifest = deepcopy(prior["manifest"])
    manifest["lineage_id"] = lineage_id
    manifest["prompts"] = _prompt_manifest()
    manifest["routing"] = _routing_manifest()
    manifest_sha256 = _sha256(manifest)
    conn.execute(
        "INSERT INTO lesson_build"
        " (id, version_id, lesson_id, request_key, requested_by, manifest,"
        " manifest_sha256, lineage_id, previous_build_id)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            new_build_id,
            prior["version_id"],
            prior["lesson_id"],
            request_key,
            requested_by,
            Jsonb(manifest),
            manifest_sha256,
            lineage_id,
            build_id,
        ),
    )
    work_by_artifact: dict[str, str] = {}
    for reference in manifest["references"]:
        publication = reference["publication"]
        work_id = work_by_artifact.get(publication["artifact_id"])
        if work_id is None:
            work_id = f"lesson-work-{uuid.uuid4().hex}"
            work_by_artifact[publication["artifact_id"]] = work_id
            conn.execute(
                "INSERT INTO lesson_build_work"
                " (id, build_id, seq, source_id, snapshot_id, artifact_id, content_hash)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    work_id,
                    new_build_id,
                    len(work_by_artifact),
                    publication["source_id"],
                    publication["snapshot_id"],
                    publication["artifact_id"],
                    publication["content_hash"],
                ),
            )
        conn.execute(
            "INSERT INTO lesson_build_reference"
            " (build_id, seq, reference_id, work_id) VALUES (%s, %s, %s, %s)",
            (new_build_id, reference["seq"], reference["reference_id"], work_id),
        )
    conn.commit()
    return read(conn, new_build_id)


def checkpoint_body(
    conn: psycopg.Connection, build_id: str, checkpoint_id: str
) -> tuple[str, str]:
    row = conn.execute(
        "SELECT path, body FROM lesson_build_checkpoint"
        " WHERE id = %s AND build_id = %s", (checkpoint_id, build_id),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown Lesson build checkpoint {checkpoint_id!r}")
    return row[0], row[1]
