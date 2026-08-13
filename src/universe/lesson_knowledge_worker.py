"""Run lesson-local KC builds one safely claimed Source Publication at a time.

The Interface stays deliberately small: ``process_next`` may launch at most
one of the eleven local stages, while ``sync_build`` only observes durable
pipeline facts.  Work claims serialize schedulers; the child-owned
``kc_pipeline`` lease remains authoritative for the launched stage itself.
"""

from __future__ import annotations

import subprocess
import uuid
from collections.abc import Callable, Mapping
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from universe import kc_pipeline, lesson_knowledge


CLAIM_TTL_SECONDS = 300.0
POLL_SECONDS = 1.0
_DEFAULT_SPAWN = object()


def _claim(row: tuple | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(
        zip(
            (
                "id",
                "build_id",
                "source_id",
                "snapshot_id",
                "artifact_id",
                "status",
                "stage",
                "last_launched_stage",
                "failure_code",
                "diagnostics",
                "claim_count",
                "claim_token",
                "lease_expires_at",
                "build_created_at",
            ),
            row,
        )
    )


def _claim_next(
    conn: psycopg.Connection,
    *,
    build_id: str | None = None,
    work_id: str | None = None,
) -> dict[str, Any] | None:
    token = uuid.uuid4().hex
    row = conn.execute(
        "WITH candidate AS ("
        " SELECT work.id, build.created_at AS build_created_at"
        " FROM lesson_knowledge_work work"
        " JOIN lesson_knowledge_build build ON build.id = work.build_id"
        " WHERE (%s::text IS NULL OR work.build_id = %s)"
        "   AND (%s::text IS NULL OR work.id = %s)"
        "   AND work.status IN ('queued', 'running')"
        "   AND work.available_at <= clock_timestamp()"
        "   AND (work.claim_token IS NULL"
        "        OR work.lease_expires_at <= clock_timestamp())"
        " ORDER BY work.available_at, work.created_at, work.id"
        " FOR UPDATE SKIP LOCKED LIMIT 1"
        ")"
        " UPDATE lesson_knowledge_work work SET"
        " status = 'running', failure_code = NULL,"
        " claim_count = work.claim_count + 1,"
        " claimed_at = clock_timestamp(), claim_token = %s,"
        " lease_expires_at = clock_timestamp()"
        "   + (%s * interval '1 second'),"
        " updated_at = now()"
        " FROM candidate WHERE work.id = candidate.id"
        " RETURNING work.id, work.build_id, work.source_id, work.snapshot_id,"
        " work.artifact_id, work.status, work.stage, work.last_launched_stage,"
        " work.failure_code, work.diagnostics, work.claim_count,"
        " work.claim_token, work.lease_expires_at, candidate.build_created_at",
        (
            build_id,
            build_id,
            work_id,
            work_id,
            token,
            CLAIM_TTL_SECONDS,
        ),
    ).fetchone()
    conn.commit()
    return _claim(row)


def _diagnostics(claim: Mapping[str, Any], **changes: Any) -> dict[str, Any]:
    current = claim.get("diagnostics")
    result = dict(current) if isinstance(current, Mapping) else {}
    result.update(changes)
    return result


def _finish_claim(
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
        "UPDATE lesson_knowledge_work SET status = %s, stage = %s,"
        " failure_code = %s, diagnostics = %s,"
        " last_launched_stage = coalesce(%s, last_launched_stage),"
        " available_at = clock_timestamp() + (%s * interval '1 second'),"
        " claimed_at = NULL, claim_token = NULL, lease_expires_at = NULL,"
        " updated_at = now()"
        " WHERE id = %s AND claim_token = %s"
        " AND lease_expires_at > clock_timestamp() RETURNING id",
        (
            status,
            stage,
            failure_code,
            Jsonb(dict(diagnostics)),
            last_launched_stage,
            POLL_SECONDS,
            claim["id"],
            claim["claim_token"],
        ),
    ).fetchone()
    conn.commit()
    return row is not None


def _result(
    claim: Mapping[str, Any],
    *,
    action: str,
    status: str,
    stage: str | None,
    pid: int | None = None,
) -> dict[str, Any]:
    return {
        "action": action,
        "build_id": claim["build_id"],
        "work_id": claim["id"],
        "source_id": claim["source_id"],
        "artifact_id": claim["artifact_id"],
        "status": status,
        "stage": stage,
        "pid": pid,
        "claim_count": claim["claim_count"],
    }


def _complete(snapshot: Mapping[str, Any]) -> bool:
    stages = snapshot.get("stages")
    return (
        isinstance(stages, Mapping)
        and tuple(stages) == tuple(kc_pipeline.LOCAL_STAGES)
        and len(stages) == 11
        and all(stages[name].get("status") == "done" for name in stages)
        and snapshot.get("next_stage") is None
    )


def _failed_stage(snapshot: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]] | None:
    stages = snapshot.get("stages")
    if not isinstance(stages, Mapping):
        return None
    for stage in kc_pipeline.LOCAL_STAGES:
        facts = stages.get(stage)
        if isinstance(facts, Mapping) and facts.get("status") == "failed":
            return stage, facts
    return None


def _attempt_finished_at(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    stage: str,
    facts: Mapping[str, Any],
) -> Any:
    """Return the newest exact terminal attempt visible to this target."""
    cutoffs = [
        row[0]
        for row in conn.execute(
            "SELECT updated_at FROM lesson_knowledge_work"
            " WHERE artifact_id = %s AND id <> %s AND status = 'failed'"
            " AND stage = %s ORDER BY updated_at DESC LIMIT 1",
            (claim["artifact_id"], claim["id"], stage),
        ).fetchall()
    ]
    run_id = facts.get("run_id")
    if isinstance(run_id, str):
        row = conn.execute(
            "SELECT finished_at FROM run WHERE id = %s"
            " AND status IN ('done', 'failed') AND finished_at IS NOT NULL",
            (run_id,),
        ).fetchone()
        if row is not None:
            cutoffs.append(row[0])
    row = conn.execute(
        "SELECT finished_at FROM run"
        " WHERE stage = %s AND status IN ('done', 'failed')"
        " AND finished_at IS NOT NULL"
        " AND params#>>'{pipeline_lease,scope_key}' = %s"
        " ORDER BY started_at DESC, id DESC LIMIT 1",
        (stage, f"source:{claim['source_id']}"),
    ).fetchone()
    if row is not None:
        cutoffs.append(row[0])
    return max(cutoffs) if cutoffs else None


def _explicit_retry_authorized(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    stage: str,
    facts: Mapping[str, Any],
) -> bool:
    """A retry is paid only by a request created after the prior attempt."""
    if claim.get("last_launched_stage") == stage:
        return False
    cutoff = _attempt_finished_at(conn, claim, stage, facts)
    if cutoff is None:
        return facts.get("status") not in {"failed", "partial"}
    created_at = claim.get("build_created_at")
    return bool(created_at is not None and created_at > cutoff)


def _snapshot_diagnostics(snapshot: Mapping[str, Any]) -> dict[str, int]:
    stages = snapshot.get("stages")
    stages = stages if isinstance(stages, Mapping) else {}
    components = snapshot.get("components")
    return {
        "completed_stage_count": sum(
            stages.get(stage, {}).get("status") == "done"
            for stage in kc_pipeline.LOCAL_STAGES
        ),
        "total_stage_count": len(kc_pipeline.LOCAL_STAGES),
        "kc_count": len(components) if isinstance(components, list) else 0,
    }


def _attention(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    *,
    failure_code: str,
    message: str,
    stage: str | None,
    exception: str | None = None,
    facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    changes: dict[str, Any] = {
        "category": "attention",
        "last_action": "attention",
        "message": message,
        "pipeline_stage": stage,
    }
    if exception is not None:
        changes["exception"] = exception
    if facts is not None:
        changes.update(
            {
                "pipeline_stage_status": facts.get("status"),
                "pipeline_run_id": facts.get("run_id"),
            }
        )
    stored = _finish_claim(
        conn,
        claim,
        status="failed",
        stage=stage,
        failure_code=failure_code,
        diagnostics=_diagnostics(claim, **changes),
    )
    return _result(
        claim,
        action="attention" if stored else "claim_lost",
        status="failed",
        stage=stage,
    )


def _read_or_attention(
    conn: psycopg.Connection,
    claim: Mapping[str, Any],
    target: kc_pipeline.SourcePublicationTarget,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        return kc_pipeline.read_snapshot(conn, target), None
    except kc_pipeline.StepNotRunnable as exc:
        return None, _attention(
            conn,
            claim,
            failure_code="publication_stale",
            message=str(exc),
            stage=claim.get("stage") or claim.get("last_launched_stage") or "blocks",
            exception=type(exc).__name__,
        )
    except (LookupError, RuntimeError, ValueError) as exc:
        return None, _attention(
            conn,
            claim,
            failure_code="publication_unreadable",
            message=str(exc),
            stage=claim.get("stage") or claim.get("last_launched_stage"),
            exception=type(exc).__name__,
        )


def _launch(
    conn: psycopg.Connection,
    target: kc_pipeline.SourcePublicationTarget,
    spawn: object,
) -> dict[str, Any]:
    if spawn is _DEFAULT_SPAWN:
        return kc_pipeline.advance(conn, target)
    if not callable(spawn):
        raise TypeError("spawn must be callable")
    return kc_pipeline.advance(conn, target, spawn=spawn)


def process_next(
    conn: psycopg.Connection,
    *,
    build_id: str | None = None,
    spawn: Callable | object = _DEFAULT_SPAWN,
) -> dict[str, Any] | None:
    """Claim and advance at most one lesson-local Source Publication."""
    if build_id is not None:
        if not isinstance(build_id, str) or not build_id.strip():
            raise ValueError("build_id must be a non-empty string")
        build_id = build_id.strip()
    claim = _claim_next(conn, build_id=build_id)
    if claim is None:
        return None
    target = kc_pipeline.SourcePublicationTarget(
        claim["source_id"], claim["artifact_id"]
    )
    snapshot, attention = _read_or_attention(conn, claim, target)
    if attention is not None:
        return attention
    assert snapshot is not None
    if _complete(snapshot):
        diagnostics = _diagnostics(
            claim,
            last_action="completed",
            local_stage_count=11,
            **_snapshot_diagnostics(snapshot),
        )
        _finish_claim(
            conn,
            claim,
            status="succeeded",
            stage=None,
            diagnostics=diagnostics,
        )
        return _result(
            claim, action="completed", status="succeeded", stage=None
        )

    stage = snapshot.get("next_stage")
    if not isinstance(stage, str) or stage not in kc_pipeline.LOCAL_STAGES:
        raise RuntimeError("local pipeline snapshot has no valid next stage")
    stage_facts = snapshot["stages"][stage]
    if stage_facts["status"] == "running":
        diagnostics = _diagnostics(
            claim,
            last_action="observed",
            pipeline_stage=stage,
            pipeline_stage_status="running",
            pipeline_run_id=stage_facts.get("run_id"),
            **_snapshot_diagnostics(snapshot),
        )
        stored = _finish_claim(
            conn,
            claim,
            status="running",
            stage=stage,
            diagnostics=diagnostics,
        )
        return _result(
            claim,
            action="observed" if stored else "claim_lost",
            status="running",
            stage=stage,
        )
    failed = _failed_stage(snapshot)
    attempted_incomplete = (
        failed is not None
        or stage_facts.get("status") == "partial"
        or claim.get("last_launched_stage") == stage
        or _attempt_finished_at(conn, claim, stage, stage_facts) is not None
    )
    if attempted_incomplete and not _explicit_retry_authorized(
        conn, claim, stage, stage_facts
    ):
        return _attention(
            conn,
            claim,
            failure_code=(
                "pipeline_stage_failed"
                if stage_facts.get("status") == "failed"
                else "stage_ended_without_result"
            ),
            message=(
                f"local pipeline stage {stage} ended without a complete result;"
                " a new explicit request created after that attempt is required"
            ),
            stage=stage,
            facts=stage_facts,
        )
    try:
        launched = _launch(conn, target, spawn)
    except kc_pipeline.StepAlreadyRunning:
        refreshed = kc_pipeline.read_snapshot(conn, target)
        refreshed_facts = refreshed.get("stages", {}).get(stage, {})
        diagnostics = _diagnostics(
            claim,
            last_action="observed",
            pipeline_stage=stage,
            pipeline_stage_status=refreshed_facts.get("status"),
            pipeline_run_id=refreshed_facts.get("run_id"),
            **_snapshot_diagnostics(refreshed),
        )
        stored = _finish_claim(
            conn,
            claim,
            status="running",
            stage=stage,
            diagnostics=diagnostics,
        )
        return _result(
            claim,
            action="observed" if stored else "claim_lost",
            status="running",
            stage=stage,
        )
    except kc_pipeline.StepNotRunnable as exc:
        return _attention(
            conn,
            claim,
            failure_code="stage_not_runnable",
            message=str(exc),
            stage=stage,
            exception=type(exc).__name__,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _attention(
            conn,
            claim,
            failure_code="stage_launch_failed",
            message=str(exc),
            stage=stage,
            exception=type(exc).__name__,
        )
    diagnostics = _diagnostics(
        claim,
        last_action="launched",
        pipeline_stage=stage,
        pipeline_stage_status=stage_facts["status"],
        pipeline_lease_token=launched.get("lease_token"),
        **_snapshot_diagnostics(snapshot),
    )
    stored = _finish_claim(
        conn,
        claim,
        status="running",
        stage=stage,
        last_launched_stage=stage,
        diagnostics=diagnostics,
    )
    if not stored:
        return _result(
            claim, action="claim_lost", status="running", stage=stage
        )
    return _result(
        claim,
        action="launched",
        status="running",
        stage=stage,
        pid=launched.get("pid"),
    )


def sync_build(conn: psycopg.Connection, build_id: str) -> dict[str, Any]:
    """Observe durable local progress for a build without launching work."""
    if not isinstance(build_id, str) or not build_id.strip():
        raise ValueError("build_id must be a non-empty string")
    row = conn.execute(
        "SELECT sv.syllabus_id, build.version_id, build.lesson_id"
        " FROM lesson_knowledge_build build"
        " JOIN syllabus_version sv ON sv.id = build.version_id"
        " WHERE build.id = %s",
        (build_id,),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown lesson knowledge build {build_id!r}")
    work_ids = [
        work_id
        for work_id, in conn.execute(
            "SELECT id FROM lesson_knowledge_work"
            " WHERE build_id = %s AND status IN ('queued', 'running')"
            " ORDER BY seq",
            (build_id,),
        ).fetchall()
    ]
    for work_id in work_ids:
        claim = _claim_next(conn, build_id=build_id, work_id=work_id)
        if claim is None:
            continue
        target = kc_pipeline.SourcePublicationTarget(
            claim["source_id"], claim["artifact_id"]
        )
        snapshot, attention = _read_or_attention(conn, claim, target)
        if attention is not None:
            continue
        assert snapshot is not None
        if _complete(snapshot):
            _finish_claim(
                conn,
                claim,
                status="succeeded",
                stage=None,
                diagnostics=_diagnostics(
                    claim,
                    last_action="completed",
                    local_stage_count=11,
                    **_snapshot_diagnostics(snapshot),
                ),
            )
            continue
        failed = _failed_stage(snapshot)
        if failed is not None:
            failed_stage, facts = failed
            _attention(
                conn,
                claim,
                failure_code="pipeline_stage_failed",
                message=f"local pipeline stage {failed_stage} has a durable failure",
                stage=failed_stage,
                facts=facts,
            )
            continue
        stage = snapshot.get("next_stage")
        stage_facts = snapshot.get("stages", {}).get(stage, {})
        _finish_claim(
            conn,
            claim,
            status="running" if stage_facts.get("status") == "running" else "queued",
            stage=stage if isinstance(stage, str) else None,
            diagnostics=_diagnostics(
                claim,
                last_action="observed",
                pipeline_stage=stage,
                pipeline_stage_status=stage_facts.get("status"),
                pipeline_run_id=stage_facts.get("run_id"),
                **_snapshot_diagnostics(snapshot),
            ),
        )
    projection = lesson_knowledge.read(conn, row[0], row[1], row[2], build_id)
    if projection is None:
        raise RuntimeError(f"incomplete lesson knowledge build {build_id}")
    return projection
