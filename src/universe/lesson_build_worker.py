"""Fair Postgres worker for explicitly requested per-Lesson builds."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Mapping
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from universe import lesson_build_plan, lesson_creation, pipeline_lease
from universe.db import connect


CLAIM_TTL_SECONDS = 300.0
POLL_SECONDS = 1.0
PROJECT_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_SPAWN = object()


def _claim_next(conn: psycopg.Connection) -> dict[str, Any] | None:
    token = uuid.uuid4().hex
    row = conn.execute(
        "WITH candidate AS ("
        " SELECT work.id FROM lesson_build_work work"
        " JOIN lesson_build build ON build.id = work.build_id"
        " WHERE work.status IN ('queued', 'running')"
        " AND work.seq = 1 AND build.is_active"
        " AND work.available_at <= clock_timestamp()"
        " AND (work.claim_token IS NULL"
        "      OR work.lease_expires_at <= clock_timestamp())"
        " ORDER BY work.available_at, build.request_seq, work.seq, work.id"
        " FOR UPDATE SKIP LOCKED LIMIT 1"
        ")"
        " UPDATE lesson_build_work work SET"
        " status = 'running', failure_code = NULL,"
        " claim_count = work.claim_count + 1,"
        " claimed_at = clock_timestamp(), claim_token = %s,"
        " lease_expires_at = clock_timestamp()"
        "   + (%s * interval '1 second'), updated_at = now()"
        " FROM candidate WHERE work.id = candidate.id"
        " RETURNING work.id, work.build_id, work.source_id, work.artifact_id,"
        " work.content_hash, work.status, work.stage, work.last_launched_stage,"
        " work.diagnostics, work.claim_count, work.claim_token",
        (token, CLAIM_TTL_SECONDS),
    ).fetchone()
    conn.commit()
    if row is None:
        return None
    return dict(
        zip(
            (
                "id",
                "build_id",
                "source_id",
                "artifact_id",
                "content_hash",
                "status",
                "stage",
                "last_launched_stage",
                "diagnostics",
                "claim_count",
                "claim_token",
            ),
            row,
        )
    )


def _completed_stages(
    claim: Mapping[str, Any], conn: psycopg.Connection | None = None
) -> tuple[str, ...]:
    if conn is not None:
        checkpointed = lesson_creation.completed_stages(conn, str(claim["build_id"]))
        if checkpointed:
            return checkpointed
    diagnostics = claim.get("diagnostics")
    raw = diagnostics.get("completed_stages", []) if isinstance(diagnostics, Mapping) else []
    if not isinstance(raw, list):
        return ()
    return tuple(value for value in raw if isinstance(value, str) and value)


def _finish(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    *,
    status: str,
    stage: str | None,
    diagnostics: Mapping[str, Any],
    failure_code: str | None = None,
    last_launched_stage: str | None = None,
) -> bool:
    row = conn.execute(
        "UPDATE lesson_build_work SET status = %s, stage = %s,"
        " failure_code = %s, diagnostics = %s,"
        " last_launched_stage = coalesce(%s, last_launched_stage),"
        " available_at = clock_timestamp() + (%s * interval '1 second'),"
        " claimed_at = NULL, claim_token = NULL, lease_expires_at = NULL,"
        " updated_at = now()"
        " WHERE id = %s AND claim_token = %s RETURNING id",
        (
            status,
            stage,
            failure_code,
            Jsonb(dict(diagnostics)),
            last_launched_stage,
            POLL_SECONDS if status == "running" else 0,
            claim["id"],
            claim["claim_token"],
        ),
    ).fetchone()
    conn.commit()
    return row is not None


def _diagnostics(claim: Mapping[str, Any], **changes: Any) -> dict[str, Any]:
    stored = claim.get("diagnostics")
    diagnostics = dict(stored) if isinstance(stored, Mapping) else {}
    diagnostics.update(changes)
    return diagnostics


def _planned_argv(
    claim: Mapping[str, Any], stage: lesson_build_plan.StagePlan
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "universe.lesson_build_stage",
        str(claim["id"]),
        stage.module,
        str(claim["source_id"]),
        str(claim["artifact_id"]),
        str(claim["content_hash"]),
    ]


def _spawn(
    argv: list[str],
    lease: pipeline_lease.Lease,
    *,
    database_url: str,
) -> subprocess.Popen:
    """Launch one stage through the authoritative same-process lease wrapper."""
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "PYTHONPATH": str(PROJECT_DIR / "src"),
            "UNIVERSE_PIPELINE_LEASE_SCOPE": lease.scope_key,
            "UNIVERSE_PIPELINE_LEASE_STAGE": lease.stage,
            "UNIVERSE_PIPELINE_LEASE_TOKEN": lease.token,
            "UNIVERSE_PIPELINE_LEASE_OWNER": lease.owner_id,
        }
    )
    wrapped = [
        sys.executable,
        "-m",
        "universe.pipeline_worker",
        lease.stage,
        argv[2],
        "--",
        *argv[3:],
    ]
    return subprocess.Popen(wrapped, cwd=PROJECT_DIR, env=environment)


def _release_lease(database_url: str, lease: pipeline_lease.Lease) -> None:
    with psycopg.connect(database_url) as lease_conn:
        pipeline_lease.release(lease_conn, lease)


def _fail_launch(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    stage: str,
    exc: BaseException,
) -> None:
    diagnostics = _diagnostics(
        claim,
        completed_stages=list(_completed_stages(claim, conn)),
        last_action="attention",
        exception=type(exc).__name__,
        message=str(exc),
    )
    conn.execute(
        "UPDATE lesson_build_work SET status = 'failed',"
        " failure_code = 'stage_launch_failed', diagnostics = %s, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND stage = %s"
        " AND last_launched_stage = %s",
        (Jsonb(diagnostics), claim["id"], stage, stage),
    )
    conn.execute(
        "UPDATE lesson_build SET status = 'failed', is_active = false,"
        " failure_code = 'stage_launch_failed', failure_message = %s,"
        " finished_at = now() WHERE id = %s",
        (str(exc), claim["build_id"]),
    )
    conn.commit()


def _active_lease(
    conn: psycopg.Connection, claim: Mapping[str, Any], stage: str
) -> pipeline_lease.Lease | None:
    return pipeline_lease.active(
        conn,
        scope_key=f"lesson-build-work:{claim['id']}",
        stage=stage,
    )


def _acquire_lease(
    database_url: str, claim: Mapping[str, Any], stage: str
) -> pipeline_lease.Lease | None:
    with psycopg.connect(database_url) as lease_conn:
        return pipeline_lease.acquire(
            lease_conn,
            scope_key=f"lesson-build-work:{claim['id']}",
            stage=stage,
            owner_id=f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}",
        )


def process_next(
    conn: psycopg.Connection,
    *,
    spawn: object = _DEFAULT_SPAWN,
) -> dict[str, Any] | None:
    """Claim and launch or observe at most one registered Lesson stage."""
    if spawn is not _DEFAULT_SPAWN and not callable(spawn):
        raise TypeError("spawn must be callable")
    claim = _claim_next(conn)
    if claim is None:
        return None
    try:
        completed = _completed_stages(claim, conn)
    except RuntimeError as exc:
        diagnostics = _diagnostics(
            claim,
            last_action="attention",
            exception=type(exc).__name__,
            message=str(exc),
        )
        stored = _finish(
            conn,
            claim,
            status="failed",
            stage=None,
            diagnostics=diagnostics,
            failure_code="checkpoint_invalid",
        )
        if stored:
            conn.execute(
                "UPDATE lesson_build SET status = 'failed', is_active = false,"
                " failure_code = 'checkpoint_invalid', failure_message = %s,"
                " finished_at = now() WHERE id = %s",
                (str(exc), claim["build_id"]),
            )
            conn.commit()
        return {
            "action": "attention" if stored else "claim_lost",
            "build_id": claim["build_id"],
            "work_id": claim["id"],
            "status": "failed" if stored else "running",
            "stage": None,
            "claim_count": claim["claim_count"],
        }
    stage = lesson_build_plan.next_stage(completed=completed)
    if stage is None:
        _finish(
            conn,
            claim,
            status="succeeded",
            stage=None,
            diagnostics={"completed_stages": list(completed)},
        )
        action = "completed"
        status = "succeeded"
        stage_name = None
        conn.execute(
            "UPDATE lesson_build SET status = 'succeeded', is_active = false,"
            " failure_code = NULL, failure_message = NULL, finished_at = now()"
            " WHERE id = %s",
            (claim["build_id"],),
        )
        conn.execute(
            "UPDATE lesson_build_work SET status = 'succeeded', stage = NULL,"
            " failure_code = NULL, updated_at = now() WHERE build_id = %s",
            (claim["build_id"],),
        )
        conn.commit()
    else:
        stage_name = stage.name
        held = _active_lease(conn, claim, stage_name)
        if held is not None:
            _finish(
                conn,
                claim,
                status="running",
                stage=stage_name,
                diagnostics=_diagnostics(
                    claim,
                    completed_stages=list(completed),
                    last_action="observed",
                    pipeline_lease_token=held.token,
                ),
            )
            action = "observed"
            status = "running"
        else:
            database_url = pipeline_lease.connection_dsn(conn)
            lease = _acquire_lease(database_url, claim, stage_name)
            if lease is None:
                _finish(
                    conn,
                    claim,
                    status="running",
                    stage=stage_name,
                    diagnostics=_diagnostics(
                        claim,
                        completed_stages=list(completed),
                        last_action="observed",
                    ),
                )
                action = "observed"
                status = "running"
            else:
                argv = _planned_argv(claim, stage)
                stored = _finish(
                    conn,
                    claim,
                    status="running",
                    stage=stage_name,
                    last_launched_stage=stage_name,
                    diagnostics=_diagnostics(
                        claim,
                        completed_stages=list(completed),
                        last_action="launching",
                        pipeline_lease_token=lease.token,
                    ),
                )
                if not stored:
                    _release_lease(database_url, lease)
                    action = "claim_lost"
                    status = "running"
                else:
                    conn.execute(
                        "UPDATE lesson_build SET status = 'running' WHERE id = %s",
                        (claim["build_id"],),
                    )
                    conn.commit()
                    try:
                        if spawn is _DEFAULT_SPAWN:
                            process = _spawn(argv, lease, database_url=database_url)
                        elif callable(spawn):
                            process = spawn(argv, lease)
                        else:
                            raise TypeError("spawn must be callable")
                    except (OSError, subprocess.SubprocessError) as exc:
                        _release_lease(database_url, lease)
                        _fail_launch(conn, claim, stage_name, exc)
                        action = "attention"
                        status = "failed"
                    else:
                        action = "launched"
                        status = "running"
                        pid = getattr(process, "pid", None)
    result = {
        "action": action,
        "build_id": claim["build_id"],
        "work_id": claim["id"],
        "status": status,
        "stage": stage_name,
        "claim_count": claim["claim_count"],
    }
    if action == "launched":
        result["pid"] = pid
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.lesson_build_worker")
    parser.add_argument("--forever", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    while True:
        with connect() as conn:
            result = process_next(conn)
        if not args.forever or result is not None:
            if not args.forever:
                return
            continue
        time.sleep(max(args.poll_seconds, 0.1))


if __name__ == "__main__":
    main()
