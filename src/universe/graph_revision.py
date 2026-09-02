"""Whole-Lesson review and deterministic immutable Subject graph assembly."""

from __future__ import annotations

import hashlib
import json
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable

import psycopg


class WholeLessonReviewError(ValueError):
    """A Lesson Build cannot receive the requested review decision."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class AcceptedLessonRef:
    """The accepted immutable Lesson fragment selected for graph assembly."""

    lesson_id: str
    build_id: str
    checkpoint_id: str
    body: str
    content_sha256: str


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha256(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _review(conn: psycopg.Connection, build_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT decision, actor, note, created_at FROM whole_lesson_review"
        " WHERE build_id = %s",
        (build_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "build_id": build_id,
        "decision": row[0],
        "actor": row[1],
        "note": row[2],
        "created_at": row[3],
    }


def review_for_build(
    conn: psycopg.Connection, build_id: str
) -> dict[str, Any] | None:
    """Return the immutable operator decision for one Lesson Build, if any."""
    return _review(conn, build_id)


def _finished_build(
    conn: psycopg.Connection, build_id: str
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT status, is_active, lesson_id, manifest FROM lesson_build"
        " WHERE id = %s FOR UPDATE",
        (build_id,),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown Lesson Build {build_id!r}")
    if row[0] != "succeeded" or bool(row[1]):
        raise WholeLessonReviewError(
            "build_not_finished", "only a finished Lesson Build can be reviewed"
        )
    return {
        "id": build_id,
        "lesson_id": row[2],
        "manifest": row[3] if isinstance(row[3], dict) else {},
    }


def _acceptance_build(
    conn: psycopg.Connection, build: dict[str, Any]
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT id, body, content_sha256 FROM lesson_build_checkpoint"
        " WHERE build_id = %s AND path = 'final_graph/runtime_graph.json'"
        " AND is_stage_result",
        (build["id"],),
    ).fetchone()
    if row is None:
        raise WholeLessonReviewError(
            "lesson_fragment_missing",
            "the finished Lesson Build has no final Lesson fragment",
        )
    if _sha256(row[1]) != row[2]:
        raise WholeLessonReviewError(
            "lesson_fragment_invalid", "the final Lesson fragment failed its hash"
        )
    manifest = build["manifest"]
    lesson_manifest = manifest.get("lesson")
    if not isinstance(lesson_manifest, dict):
        raise WholeLessonReviewError(
            "lesson_manifest_invalid", "the Lesson Build manifest has no Lesson"
        )
    graph_id = str(lesson_manifest.get("subject_graph_id") or "").strip()
    if not graph_id:
        raise WholeLessonReviewError(
            "subject_graph_missing", "the Lesson Build has no Subject graph id"
        )
    try:
        fragment = json.loads(row[1])
    except json.JSONDecodeError as exc:
        raise WholeLessonReviewError(
            "lesson_fragment_invalid", "the final Lesson fragment is not valid JSON"
        ) from exc
    lessons = fragment.get("lessons") if isinstance(fragment, dict) else None
    if (
        not isinstance(lessons, list)
        or len(lessons) != 1
        or not isinstance(lessons[0], dict)
        or str(lessons[0].get("lesson_id") or "") != build["lesson_id"]
    ):
        raise WholeLessonReviewError(
            "lesson_fragment_invalid",
            "the final Lesson fragment must contain exactly its curricular Lesson",
        )
    return {
        **build,
        "manifest": manifest,
        "lesson_manifest": lesson_manifest,
        "graph_id": graph_id,
        "checkpoint_id": row[0],
        "fragment_body": row[1],
        "fragment_sha256": row[2],
        "fragment": fragment,
    }


def _revision_metadata(row: tuple) -> dict[str, Any]:
    return {
        "id": row[0],
        "graph_id": row[1],
        "number": row[2],
        "content_sha256": row[3],
        "created_by_build_id": row[4],
        "accepted_by": row[5],
        "created_at": row[6],
    }


def _revision_for_build(
    conn: psycopg.Connection, build_id: str
) -> tuple[dict[str, Any], str] | None:
    row = conn.execute(
        "SELECT id, graph_id, revision_number, content_sha256,"
        " created_by_build_id, accepted_by, created_at, graph_body"
        " FROM graph_revision WHERE created_by_build_id = %s",
        (build_id,),
    ).fetchone()
    if row is None:
        return None
    return _revision_metadata(row[:7]), row[7]


def revision_for_build(
    conn: psycopg.Connection, build_id: str
) -> dict[str, Any] | None:
    """Return the Graph Revision minted by accepting a Lesson Build."""
    stored = _revision_for_build(conn, build_id)
    return stored[0] if stored else None


def assemble(
    graph_id: str,
    lesson_fragments: Iterable[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Deterministically project ordered accepted Lesson fragments into a graph."""
    graph_id = str(graph_id or "").strip()
    if not graph_id:
        raise ValueError("graph_id must be a non-empty string")
    fragments = list(lesson_fragments)
    if not fragments:
        raise ValueError("at least one accepted Lesson fragment is required")

    subject: dict[str, Any] | None = None
    concepts: list[dict[str, Any]] = []
    lessons: list[dict[str, Any]] = []
    resources_by_id: dict[str, dict[str, Any]] = {}
    generated_at_values: list[str] = []
    concept_ids: set[str] = set()
    segment_ids: set[str] = set()
    seen_lesson_ids: set[str] = set()
    schema_version = "runtime_graph.v0"

    for expected_lesson_id, fragment in fragments:
        if not isinstance(fragment, dict):
            raise ValueError("every accepted Lesson fragment must be an object")
        fragment_lessons = fragment.get("lessons")
        if not isinstance(fragment_lessons, list) or len(fragment_lessons) != 1:
            raise ValueError("every accepted Lesson fragment must contain one Lesson")
        lesson = deepcopy(fragment_lessons[0])
        lesson_id = str(lesson.get("lesson_id") or "")
        if lesson_id != expected_lesson_id or lesson_id in seen_lesson_ids:
            raise ValueError("accepted Lesson fragment identity is inconsistent")
        seen_lesson_ids.add(lesson_id)

        fragment_subject = fragment.get("subject")
        if not isinstance(fragment_subject, dict):
            raise ValueError("every accepted Lesson fragment must contain its Subject")
        if subject is None:
            subject = deepcopy(fragment_subject)
        elif (
            fragment_subject.get("pipeline_subject_id")
            != subject.get("pipeline_subject_id")
        ):
            raise ValueError("accepted Lesson fragments belong to different Subjects")

        schema_version = str(fragment.get("schema_version") or schema_version)
        if fragment.get("generated_at"):
            generated_at_values.append(str(fragment["generated_at"]))
        concept_namespace = hashlib.sha1(lesson_id.encode("utf-8")).hexdigest()[:6]
        subject_prefix = str(fragment_subject.get("pipeline_subject_id") or "CG")
        for local_index, raw_concept in enumerate(
            fragment.get("concepts") or [], 1
        ):
            concept = deepcopy(raw_concept)
            concept_id = str(concept.get("concept_id") or "")
            if not concept_id or concept_id in concept_ids:
                raise ValueError("accepted Lesson fragments contain duplicate Concept IDs")
            concept_ids.add(concept_id)
            concept["display_code"] = (
                f"{subject_prefix}-{concept_namespace}-{local_index:03d}"
            )
            concepts.append(concept)
        for segment in lesson.get("segments") or []:
            segment_id = str(segment.get("segment_id") or "")
            if not segment_id or segment_id in segment_ids:
                raise ValueError(
                    "accepted Lesson fragments contain duplicate Lesson Segment IDs"
                )
            segment_ids.add(segment_id)
        lessons.append(lesson)
        for resource in fragment.get("self_study_resources") or []:
            resource_id = str(resource.get("resource_id") or "")
            if not resource_id:
                raise ValueError("accepted Lesson fragment has an unidentified resource")
            prior = resources_by_id.get(resource_id)
            if prior is not None and prior != resource:
                raise ValueError("accepted Lesson fragments disagree about a resource")
            resources_by_id[resource_id] = deepcopy(resource)

    for lesson in lessons:
        for segment in lesson.get("segments") or []:
            unknown = [
                str(concept_id)
                for concept_id in segment.get("concept_ids") or []
                if str(concept_id) not in concept_ids
            ]
            if unknown:
                raise ValueError(
                    "accepted Lesson fragment references unknown Concept IDs"
                )
    subject = subject or {}
    subject["graph_id"] = graph_id
    return {
        "artifact_type": "runtime_graph",
        "schema_version": schema_version,
        **(
            {"generated_at": max(generated_at_values)}
            if generated_at_values
            else {}
        ),
        "graph_id": graph_id,
        "subject": subject,
        "concepts": concepts,
        "lessons": lessons,
        "self_study_resources": list(resources_by_id.values()),
    }


def accept(
    conn: psycopg.Connection,
    build_id: str,
    *,
    actor: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Accept one finished build and atomically mint the next Graph Revision."""
    actor = str(actor or "").strip()
    if not actor:
        raise ValueError("actor must be a non-empty string")
    build = _finished_build(conn, build_id)
    existing = _review(conn, build_id)
    if existing is not None:
        if existing["decision"] != "accepted":
            raise WholeLessonReviewError(
                "build_already_reviewed", "the Lesson Build was already rejected"
            )
        prior = _revision_for_build(conn, build_id)
        if prior is None:
            raise RuntimeError("accepted Lesson Build has no Graph Revision")
        metadata, body = prior
        return {
            "review": existing,
            "revision": metadata,
            "graph": json.loads(body),
            "body": body,
        }

    build = _acceptance_build(conn, build)
    graph_id = build["graph_id"]
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (graph_id,))
    conn.execute(
        "INSERT INTO accepted_lesson_ref"
        " (graph_id, lesson_id, build_id, checkpoint_id, week_order,"
        " activity_order, lesson_seq, accepted_by)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (graph_id, lesson_id) DO UPDATE SET"
        " build_id = EXCLUDED.build_id, checkpoint_id = EXCLUDED.checkpoint_id,"
        " week_order = EXCLUDED.week_order,"
        " activity_order = EXCLUDED.activity_order,"
        " lesson_seq = EXCLUDED.lesson_seq, accepted_by = EXCLUDED.accepted_by,"
        " accepted_at = now()",
        (
            graph_id,
            build["lesson_id"],
            build_id,
            build["checkpoint_id"],
            build["lesson_manifest"].get("week_order"),
            build["lesson_manifest"].get("activity_order"),
            build["lesson_manifest"].get("seq"),
            actor,
        ),
    )
    rows = conn.execute(
        "SELECT current.lesson_id, current.build_id, current.checkpoint_id,"
        " checkpoint.body, checkpoint.content_sha256"
        " FROM accepted_lesson_ref current"
        " JOIN lesson_build_checkpoint checkpoint"
        " ON checkpoint.id = current.checkpoint_id"
        " WHERE current.graph_id = %s"
        " ORDER BY current.week_order NULLS LAST,"
        " current.activity_order NULLS LAST, current.lesson_seq NULLS LAST,"
        " current.lesson_id",
        (graph_id,),
    ).fetchall()
    accepted_refs = [AcceptedLessonRef(*row) for row in rows]
    fragments: list[tuple[str, dict[str, Any]]] = []
    for ref in accepted_refs:
        if _sha256(ref.body) != ref.content_sha256:
            raise WholeLessonReviewError(
                "lesson_fragment_invalid",
                f"accepted Lesson fragment {ref.checkpoint_id} failed its hash",
            )
        fragments.append((ref.lesson_id, json.loads(ref.body)))
    graph = assemble(graph_id, fragments)
    body = _canonical(graph)
    revision_number = conn.execute(
        "SELECT coalesce(max(revision_number), 0) + 1 FROM graph_revision"
        " WHERE graph_id = %s",
        (graph_id,),
    ).fetchone()[0]
    revision_id = f"graph-revision-{uuid.uuid4().hex}"
    conn.execute(
        "INSERT INTO whole_lesson_review"
        " (build_id, decision, actor, note) VALUES (%s, 'accepted', %s, %s)",
        (build_id, actor, note),
    )
    conn.execute(
        "INSERT INTO graph_revision"
        " (id, graph_id, revision_number, graph_body, content_sha256,"
        " created_by_build_id, accepted_by)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            revision_id,
            graph_id,
            revision_number,
            body,
            _sha256(body),
            build_id,
            actor,
        ),
    )
    for seq, ref in enumerate(accepted_refs, 1):
        conn.execute(
            "INSERT INTO graph_revision_lesson"
            " (revision_id, seq, lesson_id, build_id, checkpoint_id,"
            " fragment_sha256) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                revision_id,
                seq,
                ref.lesson_id,
                ref.build_id,
                ref.checkpoint_id,
                ref.content_sha256,
            ),
        )
    conn.execute(
        "INSERT INTO graph_current_revision (graph_id, revision_id)"
        " VALUES (%s, %s) ON CONFLICT (graph_id) DO UPDATE SET"
        " revision_id = EXCLUDED.revision_id, updated_at = now()",
        (graph_id, revision_id),
    )
    conn.commit()
    review = _review(conn, build_id)
    revision = _revision_for_build(conn, build_id)
    assert review is not None and revision is not None
    return {
        "review": review,
        "revision": revision[0],
        "graph": graph,
        "body": body,
    }


def reject(
    conn: psycopg.Connection,
    build_id: str,
    *,
    actor: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Reject one finished build without changing the accepted graph pointer."""
    actor = str(actor or "").strip()
    if not actor:
        raise ValueError("actor must be a non-empty string")
    _finished_build(conn, build_id)
    existing = _review(conn, build_id)
    if existing is not None:
        if existing["decision"] != "rejected":
            raise WholeLessonReviewError(
                "build_already_reviewed", "the Lesson Build was already accepted"
            )
        return existing
    conn.execute(
        "INSERT INTO whole_lesson_review"
        " (build_id, decision, actor, note) VALUES (%s, 'rejected', %s, %s)",
        (build_id, actor, note),
    )
    conn.commit()
    review = _review(conn, build_id)
    assert review is not None
    return review


def read_graph(conn: psycopg.Connection, graph_id: str) -> dict[str, Any]:
    """Return the current pointer and immutable revision history for a graph."""
    rows = conn.execute(
        "SELECT revision.id, revision.graph_id, revision.revision_number,"
        " revision.content_sha256, revision.created_by_build_id,"
        " revision.accepted_by, revision.created_at,"
        " (current.revision_id = revision.id)"
        " FROM graph_revision revision"
        " LEFT JOIN graph_current_revision current"
        " ON current.graph_id = revision.graph_id"
        " WHERE revision.graph_id = %s ORDER BY revision.revision_number DESC",
        (graph_id,),
    ).fetchall()
    if not rows:
        raise LookupError(f"unknown accepted Subject graph {graph_id!r}")
    revisions = [
        {**_revision_metadata(row[:7]), "is_current": bool(row[7])}
        for row in rows
    ]
    return {
        "graph_id": graph_id,
        "current_revision": next(item for item in revisions if item["is_current"]),
        "revisions": revisions,
    }


def revision_body(
    conn: psycopg.Connection, revision_id: str
) -> tuple[str, str]:
    row = conn.execute(
        "SELECT graph_body FROM graph_revision WHERE id = %s", (revision_id,)
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown Graph Revision {revision_id!r}")
    return "graph.json", row[0]


def current_body(conn: psycopg.Connection, graph_id: str) -> tuple[str, str]:
    row = conn.execute(
        "SELECT revision.graph_body FROM graph_current_revision current"
        " JOIN graph_revision revision ON revision.id = current.revision_id"
        " WHERE current.graph_id = %s",
        (graph_id,),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown accepted Subject graph {graph_id!r}")
    return "graph.json", row[0]
