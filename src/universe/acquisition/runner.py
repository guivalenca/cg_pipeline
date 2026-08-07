"""Acquire source content and stamp immutable snapshots, artifacts, and runs."""

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import psycopg

from universe.acquisition.articles import fetch_article
from universe.acquisition.gates import GATE_CODES, build_gate_report
from universe.db import connect
from universe.harness import claim_run


@dataclass(frozen=True)
class Outcome:
    source: dict
    markdown: str | None
    failure_code: str | None
    notes: str

    @property
    def succeeded(self) -> bool:
        return self.markdown is not None and self.failure_code is None

    @property
    def model(self) -> str:
        return "firecrawl/v2" if self.source["media_type"] == "article" else "none"


def _source_ids(value: str) -> list[str]:
    ids = list(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))
    if not ids:
        raise argparse.ArgumentTypeError("--sources must contain at least one source id")
    return ids


def _positive_workers(value: str) -> int:
    workers = int(value)
    if workers < 1:
        raise argparse.ArgumentTypeError("--workers must be at least 1")
    return workers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="universe.acquisition", description="Acquire source content."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="acquire selected sources")
    selection = run.add_mutually_exclusive_group(required=True)
    selection.add_argument("--sources", dest="source_ids", type=_source_ids)
    selection.add_argument("--syllabus", dest="syllabus_id")
    run.add_argument("--only-missing", action="store_true")
    run.add_argument("--workers", type=_positive_workers, default=1)
    run.set_defaults(func=cmd_run)
    return parser


def _rows_for_sources(conn: psycopg.Connection, source_ids: list[str]) -> list[dict]:
    rows = conn.execute(
        "SELECT s.id, s.identity, s.title, s.media_type, NULL::text AS description"
        " FROM unnest(%s::text[]) WITH ORDINALITY AS chosen(id, position)"
        " JOIN source s ON s.id = chosen.id ORDER BY chosen.position",
        (source_ids,),
    ).fetchall()
    keys = ("id", "identity", "title", "media_type", "description")
    return [dict(zip(keys, row)) for row in rows]


def _syllabus_version(conn: psycopg.Connection, syllabus_id: str) -> str:
    exact = conn.execute(
        "SELECT id FROM syllabus_version WHERE id = %s", (syllabus_id,)
    ).fetchone()
    if exact:
        return exact[0]
    latest = conn.execute(
        "SELECT id FROM syllabus_version WHERE syllabus_id = %s"
        " ORDER BY seq DESC LIMIT 1",
        (syllabus_id,),
    ).fetchone()
    if not latest:
        raise SystemExit(f"no syllabus or syllabus version {syllabus_id}")
    return latest[0]


def _rows_for_syllabus(conn: psycopg.Connection, syllabus_id: str) -> list[dict]:
    version_id = _syllabus_version(conn, syllabus_id)
    rows = conn.execute(
        "SELECT s.id, s.identity, s.title, s.media_type, si.description"
        " FROM syllabus_item si JOIN source s ON s.id = si.source_id"
        " WHERE si.version_id = %s"
        " ORDER BY si.week NULLS LAST, si.seq NULLS LAST, si.id",
        (version_id,),
    ).fetchall()
    keys = ("id", "identity", "title", "media_type", "description")
    unique = {}
    for row in rows:
        item = dict(zip(keys, row))
        unique.setdefault(item["id"], item)
    return list(unique.values())


def select_sources(
    conn: psycopg.Connection,
    *,
    source_ids: list[str] | None = None,
    syllabus_id: str | None = None,
    only_missing: bool = False,
) -> tuple[list[dict], int]:
    """Return acquisition targets and the count skipped by ``only_missing``."""
    if (source_ids is None) == (syllabus_id is None):
        raise ValueError("provide exactly one of source_ids or syllabus_id")
    rows = (
        _rows_for_sources(conn, source_ids)
        if source_ids is not None
        else _rows_for_syllabus(conn, syllabus_id)
    )
    if not only_missing or not rows:
        return rows, 0
    acquired = {
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT source_id FROM source_snapshot"
            " WHERE status = 'ok' AND source_id = ANY(%s)",
            ([source["id"] for source in rows],),
        ).fetchall()
    }
    targets = [source for source in rows if source["id"] not in acquired]
    return targets, len(rows) - len(targets)


def _fetch(source: dict) -> Outcome:
    if source["media_type"] != "article":
        code = "unsupported_media_kind"
        return Outcome(source, None, code, GATE_CODES[code]["description"])
    try:
        markdown, failure_code = fetch_article(source)
    except Exception:
        markdown, failure_code = None, "fetch_failed"
    notes = "" if failure_code is None else GATE_CODES[failure_code]["description"]
    return Outcome(source, markdown, failure_code, notes)


def _record(
    conn: psycopg.Connection, indexed_outcomes: list[tuple[int, Outcome]]
) -> str:
    model = indexed_outcomes[0][1].model
    source_ids = [outcome.source["id"] for _, outcome in indexed_outcomes]
    run_id = claim_run(
        conn, "acquisition", model, "none", "none", {"source_ids": source_ids}
    )

    for index, outcome in indexed_outcomes:
        source_id = outcome.source["id"]
        if outcome.succeeded:
            content_hash = hashlib.sha256(outcome.markdown.encode()).hexdigest()
            snapshot_id = f"{source_id}:snap:{content_hash[:12]}"
            artifact_id = f"{snapshot_id}:markdown"
            conn.execute(
                "INSERT INTO source_snapshot"
                " (id, source_id, captured_at, content_hash, status, failure_note)"
                " VALUES (%s, %s, NULL, %s, 'ok', NULL) ON CONFLICT (id) DO NOTHING",
                (snapshot_id, source_id, content_hash),
            )
            conn.execute(
                "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
                " VALUES (%s, %s, 'markdown', 'firecrawl-v2', %s)"
                " ON CONFLICT (id) DO NOTHING",
                (artifact_id, snapshot_id, outcome.markdown),
            )
            report = build_gate_report("passed", [], [], None)
        else:
            snapshot_id = f"{source_id}:snap:failed"
            artifact_id = None
            conn.execute(
                "INSERT INTO source_snapshot"
                " (id, source_id, captured_at, content_hash, status, failure_note)"
                " VALUES (%s, %s, NULL, NULL, 'failed', %s) ON CONFLICT (id) DO NOTHING",
                (snapshot_id, source_id, outcome.failure_code),
            )
            report = build_gate_report(
                "failed_gate", [outcome.failure_code], [], outcome.notes
            )
        conn.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, response, error)"
            " VALUES (%s, %s, %s, %s, NULL)",
            (f"{run_id}-{index:04d}", run_id, artifact_id, json.dumps(report)),
        )
    run_status = (
        "done" if any(outcome.succeeded for _, outcome in indexed_outcomes) else "failed"
    )
    conn.execute(
        "UPDATE run SET status = %s, finished_at = now() WHERE id = %s",
        (run_status, run_id),
    )
    conn.commit()
    return run_id


def acquire(
    conn: psycopg.Connection,
    *,
    source_ids: list[str] | None = None,
    syllabus_id: str | None = None,
    only_missing: bool = False,
    workers: int = 1,
) -> dict:
    """Fetch and record every selected source, returning outcome counts."""
    if workers < 1:
        raise ValueError("workers must be at least 1")
    targets, skipped = select_sources(
        conn,
        source_ids=source_ids,
        syllabus_id=syllabus_id,
        only_missing=only_missing,
    )
    with ThreadPoolExecutor(max_workers=min(workers, len(targets)) or 1) as pool:
        outcomes = list(pool.map(_fetch, targets))
    indexed = list(enumerate(outcomes, 1))
    models = dict.fromkeys(outcome.model for outcome in outcomes)
    groups = [
        [item for item in indexed if item[1].model == model] for model in models
    ]
    run_ids = [_record(conn, group) for group in groups if group]
    ok = sum(outcome.succeeded for outcome in outcomes)
    return {
        "sources_processed": len(outcomes),
        "snapshots_ok": ok,
        "snapshots_failed": len(outcomes) - ok,
        "skipped": skipped,
        "run_ids": run_ids,
    }


def cmd_run(args: argparse.Namespace) -> None:
    with connect() as conn:
        summary = acquire(
            conn,
            source_ids=args.source_ids,
            syllabus_id=args.syllabus_id,
            only_missing=args.only_missing,
            workers=args.workers,
        )
    print(f"sources processed: {summary['sources_processed']}")
    print(f"snapshots ok: {summary['snapshots_ok']}")
    print(f"snapshots failed: {summary['snapshots_failed']}")
    if summary["skipped"]:
        print(f"sources skipped: {summary['skipped']}")


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
