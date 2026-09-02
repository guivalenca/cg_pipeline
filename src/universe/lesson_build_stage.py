"""Execute one future Lesson build stage and publish its fenced outcome."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Mapping

import psycopg
from psycopg.types.json import Jsonb

from universe import pipeline_lease
from universe.db import connect


def execute_module(module_name: str, argv: list[str]) -> None:
    if not module_name.startswith("universe."):
        raise ValueError("Lesson build stages must be universe modules")
    module = importlib.import_module(module_name)
    main = getattr(module, "main", None)
    if not callable(main):
        raise ValueError(f"{module_name} has no callable main")
    main(argv)


def _record(
    conn: psycopg.Connection,
    *,
    work_id: str,
    stage: str,
    succeeded: bool,
    exception: BaseException | None = None,
) -> None:
    supervisor = pipeline_lease.current_supervisor(required=True)
    if supervisor is None or not supervisor.enabled or supervisor.lease is None:
        raise pipeline_lease.LeaseLost("Lesson stage requires an active pipeline lease")
    if supervisor.lease.scope_key != f"lesson-build-work:{work_id}":
        raise pipeline_lease.LeaseLost("Lesson stage lease scope does not match its work")
    if supervisor.lease.stage != stage:
        raise pipeline_lease.LeaseLost("Lesson stage lease does not match its plan")
    row = conn.execute(
        "SELECT diagnostics FROM lesson_build_work"
        " WHERE id = %s AND status = 'running' AND stage = %s"
        " AND last_launched_stage = %s FOR UPDATE",
        (work_id, stage, stage),
    ).fetchone()
    if row is None:
        raise pipeline_lease.LeaseLost("Lesson stage work is no longer active")
    diagnostics = dict(row[0]) if isinstance(row[0], Mapping) else {}
    completed = diagnostics.get("completed_stages")
    completed = list(completed) if isinstance(completed, list) else []
    if succeeded and stage not in completed:
        completed.append(stage)
    diagnostics.update(
        {
            "completed_stages": completed,
            "last_action": "stage_completed" if succeeded else "attention",
        }
    )
    if exception is not None:
        diagnostics.update(
            {
                "exception": type(exception).__name__,
                "message": str(exception),
            }
        )
    supervisor.fence(conn)
    updated = conn.execute(
        "UPDATE lesson_build_work SET status = %s, stage = %s, failure_code = %s,"
        " diagnostics = %s, available_at = clock_timestamp(), updated_at = now()"
        " WHERE id = %s AND status = 'running' AND stage = %s"
        " AND last_launched_stage = %s RETURNING id",
        (
            "queued" if succeeded else "failed",
            None if succeeded else stage,
            None if succeeded else "stage_failed",
            Jsonb(diagnostics),
            work_id,
            stage,
            stage,
        ),
    ).fetchone()
    if updated is None:
        raise pipeline_lease.LeaseLost("Lesson stage lost its work before publication")
    conn.commit()


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 5:
        raise SystemExit(
            "usage: universe.lesson_build_stage WORK_ID MODULE SOURCE_ID"
            " ARTIFACT_ID CONTENT_HASH"
        )
    work_id, module_name, source_id, artifact_id, content_hash = args
    supervisor = pipeline_lease.current_supervisor(required=True)
    stage = supervisor.lease.stage if supervisor and supervisor.lease else ""
    try:
        execute_module(module_name, [source_id, artifact_id, content_hash])
    except BaseException as exc:
        with connect() as conn:
            _record(
                conn,
                work_id=work_id,
                stage=stage,
                succeeded=False,
                exception=exc,
            )
        raise
    with connect() as conn:
        _record(conn, work_id=work_id, stage=stage, succeeded=True)


if __name__ == "__main__":
    main()
