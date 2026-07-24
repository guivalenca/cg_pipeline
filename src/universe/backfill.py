"""Backfill an archived source fixture into the ingestion chain.

    python -m universe.backfill data/si-mod6-com

The fixture is the CG pipeline's historical archive of SI Module 6: an
inventory of 69 self-studies, 67 of which have extracted Markdown under
`source-bodies/`, and 2 that could not be acquired.

Ids are derived from the fixture, so the load is idempotent: running it twice
inserts nothing the second time.

    source     si-mod6-0003-bash-in-100-seconds
               "si-mod6", then the source-bodies filename, whose 4-digit
               prefix is the zero-padded `self_study_id`. That prefix maps
               one-to-one onto the inventory across the whole fixture, so the
               filename is the sanest available slug. The 2 unavailable
               sources have no file; their slug is the zero-padded id plus a
               slug of the workbook title.
    snapshot   <source_id>:snap:<content_hash first 12>   (status ok)
               <source_id>:snap:unavailable               (status failed)
    artifact   <snapshot_id>:markdown

Every snapshot here is an archival import: the capture date is unknown, so
`captured_at` is NULL and the archival origin is recorded on the artifact as
tool 'cg-pipeline-archive'.
"""

import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from universe.db import connect

COLLECTION = "si-mod6-com"
ARTIFACT_TOOL = "cg-pipeline-archive"


@dataclass(frozen=True)
class Ingestion:
    """One source and the single snapshot (and artifact) the archive holds."""

    source_id: str
    identity: dict
    title: str
    media_type: str
    snapshot_id: str
    content_hash: str | None
    status: str
    failure_note: str | None
    body: str | None


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_text.lower())).strip("-")


def plan(fixture_dir: Path) -> list[Ingestion]:
    """Read the fixture and lay out the rows it implies, in inventory order."""
    inventory = json.loads((fixture_dir / "reference" / "source-inventory.json").read_text())
    unavailable = json.loads((fixture_dir / "reference" / "unavailable-sources.json").read_text())
    notes = {record["self_study_id"]: failure_note(record) for record in unavailable}
    bodies = {path.name[:4]: path for path in (fixture_dir / "source-bodies").glob("*.md")}

    plans = []
    for record in inventory["self_studies"]:
        number = record["self_study_id"].zfill(4)
        meta = record["workbook_metadata"]
        body_path = bodies.get(number)
        slug = body_path.stem if body_path else f"{number}-{slugify(meta['title'])}"
        source_id = f"si-mod6-{slug}"

        if body_path is None:
            snapshot_id, content_hash, status = f"{source_id}:snap:unavailable", None, "failed"
            note, body = notes[record["self_study_id"]], None
        else:
            raw = body_path.read_bytes()
            content_hash = hashlib.sha256(raw).hexdigest()
            snapshot_id = f"{source_id}:snap:{content_hash[:12]}"
            status, note, body = "ok", None, raw.decode("utf-8")

        plans.append(
            Ingestion(
                source_id=source_id,
                identity={
                    "kind": "url",
                    "value": meta["url"],
                    "collection": COLLECTION,
                    "self_study_id": record["self_study_id"],
                },
                title=meta["title"],
                media_type=record["source_body"]["type"],
                snapshot_id=snapshot_id,
                content_hash=content_hash,
                status=status,
                failure_note=note,
                body=body,
            )
        )
    return plans


def failure_note(record: dict) -> str:
    """The archive's own account of why acquisition failed."""
    source_body = record["source_body"]
    reasons = ", ".join(source_body["availability_failures"]) or "no reason recorded"
    return f"{source_body['status']}: {reasons}"


def backfill(conn: psycopg.Connection, fixture_dir: Path) -> dict[str, int]:
    """Insert the fixture's facts. Existing rows are left untouched."""
    counts = dict.fromkeys(
        ["sources", "snapshots_ok", "snapshots_failed", "artifacts", "skipped"], 0
    )
    with conn.cursor() as cur:
        for item in plan(fixture_dir):
            cur.execute(
                "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (id) DO NOTHING",
                (item.source_id, Jsonb(item.identity), item.title, item.media_type),
            )
            inserted = cur.rowcount
            counts["sources"] += inserted
            counts["skipped"] += 1 - inserted

            cur.execute(
                "INSERT INTO source_snapshot"
                " (id, source_id, captured_at, content_hash, status, failure_note)"
                " VALUES (%s, %s, NULL, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (
                    item.snapshot_id,
                    item.source_id,
                    item.content_hash,
                    item.status,
                    item.failure_note,
                ),
            )
            if cur.rowcount:
                counts["snapshots_ok" if item.status == "ok" else "snapshots_failed"] += 1

            if item.body is not None:
                cur.execute(
                    "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
                    " VALUES (%s, %s, 'markdown', %s, %s) ON CONFLICT (id) DO NOTHING",
                    (f"{item.snapshot_id}:markdown", item.snapshot_id, ARTIFACT_TOOL, item.body),
                )
                counts["artifacts"] += cur.rowcount
    conn.commit()
    return counts


def main() -> None:
    fixture_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "data/si-mod6-com").resolve()
    with connect() as conn:
        counts = backfill(conn, fixture_dir)
    print(f"backfilled {fixture_dir}")
    print(
        f"  inserted: {counts['sources']} sources,"
        f" {counts['snapshots_ok']} ok + {counts['snapshots_failed']} failed snapshots,"
        f" {counts['artifacts']} artifacts"
    )
    print(f"  skipped: {counts['skipped']} sources already present")


if __name__ == "__main__":
    main()
