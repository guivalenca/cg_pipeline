"""Seal exact Canonical Source Publications into an immutable KC corpus."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from universe.source_publication import Publication, current_many


def _member(publication: Publication | Mapping[str, Any]) -> tuple[str, str]:
    if isinstance(publication, Mapping):
        source_id = publication.get("source_id")
        artifact_id = publication.get("artifact_id")
    else:
        source_id = getattr(publication, "source_id", None)
        artifact_id = getattr(publication, "artifact_id", None)
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("a publication must have a non-empty source_id")
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        raise ValueError("a publication must have a non-empty artifact_id")
    return source_id, artifact_id


def _sha256(members: tuple[tuple[str, str], ...]) -> str:
    payload = json.dumps(
        [
            {"source_id": source_id, "artifact_id": artifact_id}
            for source_id, artifact_id in members
        ],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def id_for(
    publications: Iterable[Publication | Mapping[str, Any]],
) -> str:
    """Return the content identity for one exact non-empty Source corpus."""
    members = tuple(sorted(_member(publication) for publication in publications))
    if not members:
        raise ValueError("a KC corpus manifest cannot be empty")
    source_ids = [source_id for source_id, _ in members]
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("a KC corpus manifest permits one publication per Source")
    return f"kc-corpus-{_sha256(members)}"


def _origin(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("origin must be an object")
    copied = dict(value)
    try:
        json.dumps(copied)
    except (TypeError, ValueError) as exc:
        raise ValueError("origin must be JSON-serializable") from exc
    return copied


def create(
    conn: psycopg.Connection,
    publications: Iterable[Publication | Mapping[str, Any]],
    origin: Mapping[str, Any] = {},
) -> dict[str, Any]:
    """Seal current Source Publications; repeated equivalent calls are free."""
    members = tuple(sorted(_member(publication) for publication in publications))
    if not members:
        raise ValueError("a KC corpus manifest cannot be empty")
    source_ids = [source_id for source_id, _ in members]
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("a KC corpus manifest permits one publication per Source")

    manifest_sha256 = _sha256(members)
    manifest_id = f"kc-corpus-{manifest_sha256}"
    first_origin = _origin(origin)
    with conn.transaction():
        # Acquisition requests take the same Source-row locks.  Holding them
        # across revalidation and insertion closes the readiness/seal race:
        # either a refresh exists first and this fails closed, or the manifest
        # is sealed before that refresh can become durable.
        locked = {
            row[0]
            for row in conn.execute(
                "SELECT id FROM source WHERE id = ANY(%s)"
                " ORDER BY id FOR UPDATE",
                (source_ids,),
            ).fetchall()
        }
        current = current_many(conn, source_ids)
        for source_id, artifact_id in members:
            resolved = current.get(source_id)
            if (
                source_id not in locked
                or resolved is None
                or resolved.is_previous_attempt
                or resolved.artifact_id != artifact_id
            ):
                raise ValueError(
                    f"artifact {artifact_id} is not the current publication for {source_id}"
                )

        inserted = conn.execute(
            "INSERT INTO kc_corpus_manifest (id, manifest_sha256, origin)"
            " VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING RETURNING id",
            (manifest_id, manifest_sha256, Jsonb(first_origin)),
        ).fetchone()
        if inserted is not None:
            with conn.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO kc_corpus_manifest_member"
                    " (manifest_id, seq, source_id, artifact_id)"
                    " VALUES (%s, %s, %s, %s)",
                    [
                        (manifest_id, seq, source_id, artifact_id)
                        for seq, (source_id, artifact_id) in enumerate(members, 1)
                    ],
                )
    manifest = read(conn, manifest_id)
    if manifest is None:  # Defensive: an inserted manifest is never partial.
        raise RuntimeError(f"incomplete KC corpus manifest {manifest_id}")
    return manifest


def read(conn: psycopg.Connection, manifest_id: str) -> dict[str, Any] | None:
    """Read a complete manifest, rejecting corrupted identity or ordering."""
    row = conn.execute(
        "SELECT manifest_sha256, origin, created_at"
        " FROM kc_corpus_manifest WHERE id = %s",
        (manifest_id,),
    ).fetchone()
    if row is None:
        return None
    manifest_sha256, origin, created_at = row
    rows = conn.execute(
        "SELECT seq, source_id, artifact_id FROM kc_corpus_manifest_member"
        " WHERE manifest_id = %s ORDER BY seq",
        (manifest_id,),
    ).fetchall()
    members = tuple((source_id, artifact_id) for _, source_id, artifact_id in rows)
    if (
        not members
        or [seq for seq, _, _ in rows] != list(range(1, len(rows) + 1))
        or members != tuple(sorted(members))
        or _sha256(members) != manifest_sha256
        or manifest_id != f"kc-corpus-{manifest_sha256}"
    ):
        return None
    return {
        "id": manifest_id,
        "manifest_sha256": manifest_sha256,
        "origin": dict(origin or {}),
        "created_at": created_at,
        "publications": [
            {"source_id": source_id, "artifact_id": artifact_id}
            for source_id, artifact_id in members
        ],
    }
