"""Durably turn one acquired source artifact into canonical clean Markdown."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from universe import blocks, harness, passage_cleanup
from universe.blocks import BLOCKER_VERSION
from universe.model_client import ModelClient, ModelError
from universe.settings import (
    acquisition_lease_minutes,
    openrouter_tool_provider_routing,
    source_cleanup_fallback_model,
    source_cleanup_model,
    source_cleanup_timeout_seconds,
)


JOB_COLUMNS = (
    "id", "acquisition_job_id", "source_id", "source_artifact_id", "status",
    "attempt_count", "cuts_run_id", "cleanup_id", "canonical_artifact_id",
    "failure_code", "diagnostics", "created_at", "claimed_at", "claim_token",
    "finished_at",
)

MAIN_CONTENT_TOOL = "article-main-content-boundary"
MAIN_CONTENT_VERSION = "v1"
TRIAGE_PROMPT_VERSION = "v005"


def _job(row: tuple | None) -> dict[str, Any] | None:
    return dict(zip(JOB_COLUMNS, row)) if row else None


def get_source_cleanup_job(conn: psycopg.Connection, job_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, acquisition_job_id, source_id, source_artifact_id, status,"
        " attempt_count, cuts_run_id, cleanup_id, canonical_artifact_id,"
        " failure_code, diagnostics, created_at, claimed_at, claim_token, finished_at"
        " FROM source_cleanup_job WHERE id = %s",
        (job_id,),
    ).fetchone()
    return _job(row)


def enqueue_source_cleanup(
    conn: psycopg.Connection,
    *,
    acquisition_job_id: str,
    source_artifact_id: str,
    commit: bool = True,
) -> dict[str, Any]:
    """Queue one artifact exactly once; safe from refreshes and worker races."""
    context = conn.execute(
        "SELECT j.source_id, j.status, j.provider, j.artifact_id, j.diagnostics,"
        " a.snapshot_id, a.tool, a.metadata, parent.snapshot_id"
        " FROM acquisition_job j"
        " JOIN artifact a ON a.id = %s"
        " JOIN artifact parent ON parent.id = j.artifact_id"
        " WHERE j.id = %s",
        (source_artifact_id, acquisition_job_id),
    ).fetchone()
    if context is None:
        raise ValueError("cleanup requires an acquisition artifact from a known job")
    (
        source_id,
        status,
        _provider,
        _parent_id,
        acquisition_diagnostics,
        snapshot_id,
        artifact_tool,
        artifact_metadata,
        parent_snapshot_id,
    ) = context
    requires_cleanup = bool(
        (acquisition_diagnostics or {}).get("pipeline_requires_cleanup")
        or (artifact_metadata or {}).get("pipeline_requires_cleanup")
        or artifact_tool == "article-image-association"
    )
    if status != "succeeded" or not requires_cleanup:
        raise ValueError(
            "automatic cleanup requires a successful acquisition artifact"
            " with the canonical-publication contract"
        )
    if snapshot_id != parent_snapshot_id:
        raise ValueError("cleanup artifact does not belong to the acquisition snapshot")

    job_id = f"cleanup-{acquisition_job_id.removeprefix('acq-')}"
    inserted = conn.execute(
        "INSERT INTO source_cleanup_job"
        " (id, acquisition_job_id, source_id, source_artifact_id)"
        " VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
        (job_id, acquisition_job_id, source_id, source_artifact_id),
    ).fetchone()
    if inserted is None:
        row = conn.execute(
            "SELECT id FROM source_cleanup_job WHERE acquisition_job_id = %s"
            " OR source_artifact_id = %s ORDER BY created_at, id LIMIT 1",
            (acquisition_job_id, source_artifact_id),
        ).fetchone()
        if row is None:
            conn.rollback()
            raise RuntimeError("cleanup queue conflict could not be resolved")
        job_id = row[0]
        deduplicated = True
    else:
        deduplicated = False
    if commit:
        conn.commit()
    result = get_source_cleanup_job(conn, job_id)
    assert result is not None
    result["deduplicated"] = deduplicated
    return result


def claim_next_source_cleanup(
    conn: psycopg.Connection, *, job_id: str | None = None
) -> dict[str, Any] | None:
    token = uuid.uuid4().hex
    row = conn.execute(
        "WITH candidate AS ("
        " SELECT id FROM source_cleanup_job"
        " WHERE (%s::text IS NULL OR id = %s) AND available_at <= now()"
        " AND (status = 'queued' OR (status = 'running' AND lease_expires_at < now()))"
        " ORDER BY available_at, created_at, id FOR UPDATE SKIP LOCKED LIMIT 1"
        ") UPDATE source_cleanup_job j SET status = 'running',"
        " attempt_count = j.attempt_count + 1, claimed_at = now(), claim_token = %s,"
        " lease_expires_at = now() + (%s * interval '1 minute'), updated_at = now(),"
        " diagnostics = '{}'::jsonb FROM candidate WHERE j.id = candidate.id"
        " RETURNING j.id, j.acquisition_job_id, j.source_id, j.source_artifact_id,"
        " j.status, j.attempt_count, j.cuts_run_id, j.cleanup_id,"
        " j.canonical_artifact_id, j.failure_code, j.diagnostics, j.created_at,"
        " j.claimed_at, j.claim_token, j.finished_at",
        (job_id, job_id, token, acquisition_lease_minutes()),
    ).fetchone()
    conn.commit()
    return _job(row)


class ResilientToolClient:
    """Retry one malformed forced-tool response through an independent model."""

    def __init__(self, primary: ModelClient, fallback: ModelClient) -> None:
        self.primary = primary
        self.fallback = fallback
        self.model = primary.model

    @property
    def params(self) -> dict[str, Any]:
        return {
            **self.primary.params,
            "tool_fallback_model": self.fallback.model,
            "tool_fallback_limit": 1,
        }

    def complete(self, prompt: str) -> tuple[str, dict, int]:
        try:
            return self.primary.complete(prompt)
        except ModelError as primary_error:
            text, fallback_usage, fallback_duration = self.fallback.complete(prompt)
            usage = _combined_attempt_usage(
                primary_error.usage,
                fallback_usage,
                primary_model=self.primary.model,
                fallback_model=self.fallback.model,
                primary_error=primary_error,
            )
            return text, usage, primary_error.duration_ms + fallback_duration


def _combined_attempt_usage(
    primary: dict[str, Any],
    fallback: dict[str, Any],
    *,
    primary_model: str,
    fallback_model: str,
    primary_error: Exception,
) -> dict[str, Any]:
    """Aggregate billable counters while retaining an auditable attempt ledger."""
    combined = dict(fallback)
    numeric_keys = {
        "prompt_tokens", "completion_tokens", "total_tokens", "cost", "total_cost"
    }
    for key in numeric_keys:
        values = [value for value in (primary.get(key), fallback.get(key))
                  if isinstance(value, (int, float)) and not isinstance(value, bool)]
        if values:
            combined[key] = sum(values)
    combined["fallback_used"] = True
    combined["attempts"] = [
        {
            "model": primary_model,
            "status": "failed",
            "error": type(primary_error).__name__,
            "usage": primary,
        },
        {
            "model": fallback_model,
            "status": "succeeded",
            "usage": fallback,
        },
    ]
    return combined


def _main_content_artifact(
    conn: psycopg.Connection, source_artifact_id: str, body: str
) -> tuple[str, str]:
    """Create an immutable article view beginning at its first real H1.

    Navigation, cookie shells and author chrome often precede the article H1.
    The original enriched artifact and every image outcome remain untouched;
    cleanup simply addresses a derived, auditable main-content view.
    """
    parsed = blocks.split_blocks(body)
    first_h1 = next(
        (
            block
            for block in parsed
            if block.kind == "heading"
            and block.text.lstrip().startswith("# ")
        ),
        None,
    )
    if first_h1 is None or not body[: first_h1.start_char].strip():
        return source_artifact_id, body

    main_body = body[first_h1.start_char :].rstrip() + "\n"
    main_artifact_id = f"{source_artifact_id}:main"
    snapshot = conn.execute(
        "SELECT snapshot_id FROM artifact WHERE id = %s", (source_artifact_id,)
    ).fetchone()
    if snapshot is None:
        raise ValueError("cleanup source artifact is missing")
    conn.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, tool_version, body, metadata)"
        " VALUES (%s, %s, 'markdown', %s, %s, %s, %s)"
        " ON CONFLICT (id) DO NOTHING",
        (
            main_artifact_id,
            snapshot[0],
            MAIN_CONTENT_TOOL,
            MAIN_CONTENT_VERSION,
            main_body,
            Jsonb(
                {
                    "source_markdown_artifact_id": source_artifact_id,
                    "boundary": "first_h1",
                    "omitted_prefix_chars": first_h1.start_char,
                }
            ),
        ),
    )
    conn.commit()
    return main_artifact_id, main_body


def _model_client(tool_path: Path, model: str, *, fallback: bool = False) -> ModelClient:
    extra = {
        **harness.load_tool(str(tool_path)),
        "provider": openrouter_tool_provider_routing(),
    }
    if not fallback:
        extra.update({
            "reasoning": {"effort": "high", "exclude": True},
        })
    return ModelClient(
        model,
        temperature=0,
        timeout=source_cleanup_timeout_seconds(),
        extra=extra,
    )


def _client(tool_path: Path) -> ResilientToolClient:
    return ResilientToolClient(
        _model_client(tool_path, source_cleanup_model()),
        _model_client(tool_path, source_cleanup_fallback_model(), fallback=True),
    )


def _default_clients() -> tuple[
    ResilientToolClient, ResilientToolClient, ResilientToolClient, ResilientToolClient
]:
    prompts = harness.PROMPTS_DIR
    return (
        _client(prompts / "passage-cuts" / "tool-v001.json"),
        _client(prompts / "passage-triage" / "tool-v003.json"),
        _client(prompts / "passage-triage" / "tool-v003-atomic.json"),
        _client(prompts / "passage-refine" / "tool-v002.json"),
    )


def _finish_failed(
    conn: psycopg.Connection, job: dict[str, Any], exc: Exception
) -> dict[str, Any]:
    diagnostics = {"category": "source_cleanup_failed", "exception": type(exc).__name__}
    updated = conn.execute(
        "UPDATE source_cleanup_job SET status = 'failed',"
        " failure_code = 'source_cleanup_failed', diagnostics = %s,"
        " finished_at = now(), lease_expires_at = NULL, claim_token = NULL,"
        " updated_at = now() WHERE id = %s AND status = 'running' AND claim_token = %s",
        (Jsonb(diagnostics), job["id"], job["claim_token"]),
    )
    if updated.rowcount != 1:
        conn.rollback()
    else:
        conn.commit()
    result = get_source_cleanup_job(conn, job["id"])
    assert result is not None
    return result


def _finish_without_teachable_content(
    conn: psycopg.Connection,
    job: dict[str, Any],
    *,
    cleanup_id: str,
    candidate_artifact_id: str,
    passages: int,
) -> dict[str, Any]:
    """Keep an empty cleanup candidate auditable without publishing it."""
    diagnostics = {
        "category": "no_teachable_content_preserved",
        "cleanup_id": cleanup_id,
        "candidate_artifact_id": candidate_artifact_id,
        "passages": passages,
    }
    updated = conn.execute(
        "UPDATE source_cleanup_job SET status = 'failed', cleanup_id = %s,"
        " failure_code = 'no_teachable_content_preserved', diagnostics = %s,"
        " finished_at = now(), lease_expires_at = NULL, claim_token = NULL,"
        " updated_at = now() WHERE id = %s AND status = 'running' AND claim_token = %s",
        (cleanup_id, Jsonb(diagnostics), job["id"], job["claim_token"]),
    )
    if updated.rowcount != 1:
        conn.rollback()
    else:
        conn.commit()
    result = get_source_cleanup_job(conn, job["id"])
    assert result is not None
    return result


def process_next_source_cleanup(
    conn: psycopg.Connection,
    *,
    job_id: str | None = None,
    cuts_client: ModelClient | None = None,
    triage_client: ModelClient | None = None,
    atomic_triage_client: ModelClient | None = None,
    refine_client: ModelClient | None = None,
) -> dict[str, Any] | None:
    """Claim and run blocks → cuts → triage/refine → canonical artifact."""
    job = claim_next_source_cleanup(conn, job_id=job_id)
    if job is None:
        return None
    try:
        defaults = None
        if not all((cuts_client, triage_client, atomic_triage_client, refine_client)):
            defaults = _default_clients()
        cuts_client = cuts_client or defaults[0]
        triage_client = triage_client or defaults[1]
        atomic_triage_client = atomic_triage_client or defaults[2]
        refine_client = refine_client or defaults[3]

        artifact = conn.execute(
            "SELECT body FROM artifact WHERE id = %s",
            (job["source_artifact_id"],),
        ).fetchone()
        if artifact is None:
            raise ValueError("cleanup source artifact is missing")
        cleanup_artifact_id, cleanup_body = _main_content_artifact(
            conn, job["source_artifact_id"], artifact[0]
        )
        blocks.store_blocks(
            conn, cleanup_artifact_id, blocks.split_blocks(cleanup_body)
        )

        cuts_run_id = job.get("cuts_run_id")
        if cuts_run_id is None:
            source = harness.fetch_sources(conn, [cleanup_artifact_id])[
                cleanup_artifact_id
            ]
            target = harness.Target(
                source[0], source[1], cleanup_artifact_id,
                harness.blocks_body(conn, cleanup_artifact_id),
            )
            cuts_summary = harness.execute(
                conn,
                harness.load_prompt("passage-cuts", "v001"),
                cuts_client,
                [target],
                workers=1,
                run_params={
                    "blocker_version": BLOCKER_VERSION,
                    "source_cleanup_job_id": job["id"],
                },
            )
            if cuts_summary["status"] != "done" or cuts_summary["failed"]:
                raise RuntimeError("passage cuts failed")
            cuts_run_id = cuts_summary["run_id"]
            conn.execute(
                "UPDATE source_cleanup_job SET cuts_run_id = %s, updated_at = now()"
                " WHERE id = %s AND status = 'running' AND claim_token = %s",
                (cuts_run_id, job["id"], job["claim_token"]),
            )
            conn.commit()

        cleanup = passage_cleanup.run_cleanup(
            conn,
            cuts_run_id=cuts_run_id,
            model=source_cleanup_model(),
            triage_prompt=harness.load_prompt(
                "passage-triage", TRIAGE_PROMPT_VERSION
            ),
            refine_prompt=harness.load_prompt("passage-refine", "v002", require_body=False),
            triage_client=triage_client,
            atomic_triage_client=atomic_triage_client,
            refine_client=refine_client,
        )
        if cleanup["status"] != "done" or len(cleanup.get("artifacts", [])) != 1:
            raise RuntimeError("passage cleanup failed")
        canonical_id = cleanup["artifacts"][0]
        canonical = conn.execute(
            "SELECT body FROM artifact WHERE id = %s", (canonical_id,)
        ).fetchone()
        if canonical is None:
            raise RuntimeError("passage cleanup artifact is missing")
        if not canonical[0].strip():
            return _finish_without_teachable_content(
                conn,
                job,
                cleanup_id=cleanup["cleanup_id"],
                candidate_artifact_id=canonical_id,
                passages=cleanup["passages"],
            )
        updated = conn.execute(
            "UPDATE source_cleanup_job SET status = 'succeeded', cleanup_id = %s,"
            " canonical_artifact_id = %s, diagnostics = %s, finished_at = now(),"
            " lease_expires_at = NULL, claim_token = NULL, updated_at = now()"
            " WHERE id = %s AND status = 'running' AND claim_token = %s",
            (
                cleanup["cleanup_id"], canonical_id,
                Jsonb({"category": "success", "passages": cleanup["passages"]}),
                job["id"], job["claim_token"],
            ),
        )
        if updated.rowcount != 1:
            conn.rollback()
        else:
            conn.commit()
        result = get_source_cleanup_job(conn, job["id"])
        assert result is not None
        return result
    except (Exception, SystemExit) as exc:
        conn.rollback()
        return _finish_failed(conn, job, exc)
