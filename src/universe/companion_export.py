"""Export immutable Graph Revisions as validated Companion packages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

import psycopg

from universe.companion_package import (
    CompanionPackage,
    CompanionPackageArchive,
    PackageAssemblyError,
    default_companion_repo,
    validated_package_archive,
)
from universe.syllabus import LESSON_SUBJECT_NAMES


def _selected_revision(
    conn: psycopg.Connection,
    *,
    graph_id: str | None = None,
    revision_id: str | None = None,
) -> tuple[str, str]:
    if (graph_id is None) == (revision_id is None):
        raise ValueError("select exactly one current graph or Graph Revision")
    if graph_id is not None:
        row = conn.execute(
            "SELECT revision.graph_id, revision.graph_body, revision.content_sha256"
            " FROM graph_current_revision current"
            " JOIN graph_revision revision ON revision.id = current.revision_id"
            " WHERE current.graph_id = %s",
            (graph_id,),
        ).fetchone()
        unknown = f"unknown accepted Subject graph {graph_id!r}"
    else:
        row = conn.execute(
            "SELECT graph_id, graph_body, content_sha256 FROM graph_revision"
            " WHERE id = %s",
            (revision_id,),
        ).fetchone()
        unknown = f"unknown Graph Revision {revision_id!r}"
    if row is None:
        raise LookupError(unknown)
    body = str(row[1])
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != row[2]:
        raise PackageAssemblyError(
            "The selected Graph Revision failed its immutable content hash."
        )
    return str(row[0]), body


def _identity(conn: psycopg.Connection, graph_id: str) -> tuple[str, str]:
    row = conn.execute(
        "SELECT syllabus.title, syllabus.institution_id,"
        " subject.lesson_subject_code FROM syllabus_subject subject"
        " JOIN syllabus ON syllabus.id = subject.syllabus_id"
        " WHERE subject.graph_id = %s",
        (graph_id,),
    ).fetchone()
    if row is None:
        raise PackageAssemblyError(
            f"Graph Revision is missing graph metadata for {graph_id!r}."
        )
    syllabus_title = str(row[0] or "").strip()
    institution_slug = str(row[1] or "").strip()
    lesson_subject_code = str(row[2] or "").strip()
    subject_name = LESSON_SUBJECT_NAMES.get(
        lesson_subject_code, lesson_subject_code
    )
    if not syllabus_title or not institution_slug or not subject_name:
        raise PackageAssemblyError(
            f"Graph Revision is missing graph metadata for {graph_id!r}."
        )
    return f"{syllabus_title} · {subject_name}", institution_slug


def _package(
    conn: psycopg.Connection,
    *,
    graph_id: str | None = None,
    revision_id: str | None = None,
    companion_repo: Path | None,
    occupied_graph_ids: Iterable[str],
) -> CompanionPackageArchive:
    selected_graph_id, body = _selected_revision(
        conn,
        graph_id=graph_id,
        revision_id=revision_id,
    )
    try:
        graph = json.loads(body)
    except json.JSONDecodeError as exc:
        raise PackageAssemblyError(
            "The selected Graph Revision is not valid JSON."
        ) from exc
    if not isinstance(graph, dict):
        raise PackageAssemblyError(
            "The selected Graph Revision must be a JSON object."
        )
    display_name, institution_slug = _identity(conn, selected_graph_id)
    package = CompanionPackage.from_graph_revision(
        graph,
        graph_id=selected_graph_id,
        display_name=display_name,
        institution_slug=institution_slug,
    )
    occupied = set(occupied_graph_ids)
    return validated_package_archive(
        package,
        companion_repo=companion_repo or default_companion_repo(),
        replace_graph_id=(selected_graph_id if selected_graph_id in occupied else None),
    )


def current_package(
    conn: psycopg.Connection,
    graph_id: str,
    *,
    companion_repo: Path | None = None,
    occupied_graph_ids: Iterable[str] = (),
) -> CompanionPackageArchive:
    """Return the current Graph Revision as a validated Companion package."""
    return _package(
        conn,
        graph_id=graph_id,
        companion_repo=companion_repo,
        occupied_graph_ids=occupied_graph_ids,
    )


def revision_package(
    conn: psycopg.Connection,
    revision_id: str,
    *,
    companion_repo: Path | None = None,
    occupied_graph_ids: Iterable[str] = (),
) -> CompanionPackageArchive:
    """Return one explicitly selected Graph Revision as a validated package."""
    return _package(
        conn,
        revision_id=revision_id,
        companion_repo=companion_repo,
        occupied_graph_ids=occupied_graph_ids,
    )
