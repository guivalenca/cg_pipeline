"""Exact, durable handoff from the KC judge to grouping.

The judge run is the certificate owner; its normalized rows are the selected
verdict facts. JSON parameters carry only a count and digest so downstream
readers can cheaply reject a forged, truncated, or cross-run manifest.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True, slots=True)
class JudgeManifest:
    judge_run_id: str
    build_key: str
    run_item_ids: tuple[str, ...]
    count: int
    sha256: str


def manifest_sha256(run_item_ids: Iterable[str]) -> str:
    """Hash one ordered id sequence with an unambiguous canonical encoding."""
    ids = list(run_item_ids)
    payload = json.dumps(ids, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def certify(
    conn: psycopg.Connection,
    *,
    judge_run_id: str,
    run_item_ids: Iterable[str],
) -> JudgeManifest:
    """Insert one run's immutable selected-verdict manifest, without commit."""
    ids = tuple(run_item_ids)
    if any(not isinstance(item_id, str) or not item_id for item_id in ids):
        raise ValueError("judge manifest ids must be non-empty strings")
    if len(set(ids)) != len(ids):
        raise ValueError("judge manifest ids must be unique")
    row = conn.execute(
        "SELECT params->>'build_key' FROM run"
        " WHERE id = %s AND stage = 'kc-judge'",
        (judge_run_id,),
    ).fetchone()
    if row is None or not row[0]:
        raise LookupError(f"no KC judge run {judge_run_id}")
    build_key = row[0]
    for seq, run_item_id in enumerate(ids, 1):
        conn.execute(
            "INSERT INTO kc_judge_manifest (judge_run_id, seq, run_item_id)"
            " VALUES (%s, %s, %s)",
            (judge_run_id, seq, run_item_id),
        )
    return JudgeManifest(
        judge_run_id=judge_run_id,
        build_key=build_key,
        run_item_ids=ids,
        count=len(ids),
        sha256=manifest_sha256(ids),
    )


def read(
    conn: psycopg.Connection,
    judge_run_id: str,
) -> JudgeManifest | None:
    """Return a judge manifest only when rows and certificate agree exactly."""
    row = conn.execute(
        "SELECT params FROM run"
        " WHERE id = %s AND stage = 'kc-judge' AND status = 'done'",
        (judge_run_id,),
    ).fetchone()
    if row is None:
        return None
    params = row[0] or {}
    count = params.get("candidate_count")
    expected_sha = params.get("candidate_manifest_sha256")
    build_key = params.get("build_key")
    if not (
        params.get("candidate_manifest_complete") is True
        and type(count) is int
        and count >= 0
        and isinstance(expected_sha, str)
        and len(expected_sha) == 64
        and isinstance(build_key, str)
        and build_key
    ):
        return None
    rows = conn.execute(
        "SELECT seq, run_item_id FROM kc_judge_manifest"
        " WHERE judge_run_id = %s ORDER BY seq",
        (judge_run_id,),
    ).fetchall()
    ids = tuple(run_item_id for _, run_item_id in rows)
    if (
        len(rows) != count
        or [seq for seq, _ in rows] != list(range(1, count + 1))
        or len(set(ids)) != count
        or manifest_sha256(ids) != expected_sha
    ):
        return None
    # Count/hash prove which verdict rows were selected, but not that their
    # endpoints belong to this judge build. Reject a hand-edited or stale
    # cross-corpus row before grouping/snapshot readers try to resolve task
    # evidence that the certified statement witness never contained.
    statement_runs = params.get("statements_from")
    if not (
        isinstance(statement_runs, list)
        and all(isinstance(run_id, str) and run_id for run_id in statement_runs)
    ):
        return None
    try:
        from universe.effective_evidence import resolve_statement_tasks

        statement_task_ids = {
            task["id"] for task in resolve_statement_tasks(conn, statement_runs)
        }
    except (LookupError, RuntimeError, SystemExit):
        return None
    verdict_rows = conn.execute(
        "SELECT run_item_id, task_a_id, task_b_id FROM kc_verdict"
        " WHERE run_item_id = ANY(%s)",
        (list(ids),),
    ).fetchall()
    if (
        len(verdict_rows) != count
        or {run_item_id for run_item_id, _, _ in verdict_rows} != set(ids)
        or any(
            task_a_id not in statement_task_ids
            or task_b_id not in statement_task_ids
            for _, task_a_id, task_b_id in verdict_rows
        )
    ):
        return None
    return JudgeManifest(
        judge_run_id=judge_run_id,
        build_key=build_key,
        run_item_ids=ids,
        count=count,
        sha256=expected_sha,
    )


def require(conn: psycopg.Connection, judge_run_id: str) -> JudgeManifest:
    """Read a certified manifest or reject the downstream publication."""
    manifest = read(conn, judge_run_id)
    if manifest is None:
        raise LookupError(f"no certified judge run {judge_run_id}")
    return manifest
