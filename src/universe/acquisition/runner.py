"""Durable, explicit, one-source-at-a-time Markdown acquisition.

Queueing and claiming are deliberately separate transactions.  The job is
therefore visible before Firecrawl is contacted, and a crashed web process
does not erase the user's request.  Workers claim with ``SKIP LOCKED`` so
several Railway workers can share PostgreSQL without a Redis queue.

The acquisition fact still stops at its ``markdown`` artifact. Public article
jobs then enqueue image enrichment and canonical passage cleanup as separate
durable work; Tasks and Knowledge Components remain outside this worker.
"""

import argparse
import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from universe.acquisition.articles import ArticleFetch, fetch_article_detailed
from universe.acquisition.book_acquisition import (
    BOOK_PROVIDER,
    BookCaptureAdapter,
    book_capture_outcome,
)
from universe.acquisition.gates import GATE_CODES
from universe.acquisition.image_jobs import (
    finalize_article_image_association,
    insert_article_image_candidates,
    insert_teaching_beat_candidates,
    insert_video_frame_candidates,
    process_next_article_image,
    process_next_source_image_analysis,
    queue_source_image_analysis_if_ready,
)
from universe.acquisition.video_teaching_beats import persist_teaching_beat_reading
from universe.acquisition.manual_uploads import (
    MANUAL_PROVIDER,
    manual_upload_outcome,
)
from universe.acquisition.pdfs import (
    PDF_PAGE_TOOL_VERSION,
    PDF_TEXT_TOOL,
    PDF_TEXT_TOOL_VERSION,
)
from universe.acquisition.source_cleanup_jobs import (
    enqueue_source_cleanup,
    process_next_source_cleanup,
)
from universe.acquisition.videos import (
    YOUTUBE_PROVIDER,
    VideoAcquisition,
    VideoAdapter,
    VideoAdapterError,
    acquire_video,
    acquisition_input,
    get_preflight,
    persist_video_transcript,
)
from universe.assets import AssetStore, asset_store_from_env
from universe.db import connect
from universe.settings import acquisition_lease_minutes, acquisition_poll_seconds

ARTICLE_PROVIDER = "firecrawl/v2"


@dataclass(frozen=True)
class Outcome:
    markdown: str | None
    failure_code: str | None
    provider: str
    tool: str
    diagnostics: dict[str, Any]
    # Appended defaults deliberately preserve the original five-position API.
    tool_version: str | None = None
    content_hash: str | None = None
    raw_markdown: str | None = None
    image_urls: tuple[str, ...] = ()
    retryable: bool = False
    retry_after_seconds: int = 0
    video_acquisition: VideoAcquisition | None = None

    @property
    def succeeded(self) -> bool:
        return self.markdown is not None and self.failure_code is None


JOB_COLUMNS = (
    "id",
    "source_id",
    "status",
    "provider",
    "attempt_count",
    "artifact_id",
    "failure_code",
    "diagnostics",
    "created_at",
    "claimed_at",
    "claim_token",
    "finished_at",
    "video_preflight_id",
    "request_input",
    "input_fingerprint",
)


def _job_dict(row: tuple | None) -> dict | None:
    return dict(zip(JOB_COLUMNS, row)) if row else None


def _provider_for(media_type: str | None) -> str:
    if media_type == "article":
        return ARTICLE_PROVIDER
    if media_type == "book":
        return BOOK_PROVIDER
    if media_type == "video":
        return YOUTUBE_PROVIDER
    return "none"


def _one_source_id(value: str) -> str:
    source_id = value.strip()
    if not source_id or "," in source_id:
        raise argparse.ArgumentTypeError("provide exactly one source id")
    return source_id


def get_job(conn: psycopg.Connection, job_id: str) -> dict | None:
    """Return one queue job in a JSON-friendly shape."""
    row = conn.execute(
        "SELECT id, source_id, status, provider, attempt_count, artifact_id,"
        " failure_code, diagnostics, created_at, claimed_at, claim_token, finished_at,"
        " video_preflight_id, request_input, input_fingerprint"
        " FROM acquisition_job WHERE id = %s",
        (job_id,),
    ).fetchone()
    return _job_dict(row)


def enqueue_source(
    conn: psycopg.Connection,
    source_id: str,
    *,
    actor: str = "founder",
    authorize_paid_transcription: bool = False,
) -> dict:
    """Queue exactly one source, deduplicating a queued/running double-click.

    This function commits before returning.  A caller may safely schedule a
    worker only after it receives the returned job id; the provider cannot be
    called before the durable row exists.
    """
    if not isinstance(source_id, str) or not source_id.strip() or "," in source_id:
        raise ValueError("enqueue_source requires exactly one source id")
    source_id = source_id.strip()
    source = conn.execute(
        "SELECT media_type FROM source WHERE id = %s FOR UPDATE", (source_id,)
    ).fetchone()
    if source is None:
        conn.rollback()
        raise ValueError(f"unknown source {source_id}")

    downstream = conn.execute(
        "SELECT j.id FROM acquisition_job j WHERE j.source_id = %s AND ("
        " EXISTS (SELECT 1 FROM source_cleanup_job c"
        "   WHERE c.acquisition_job_id = j.id AND c.status IN ('queued', 'running'))"
        " OR EXISTS (SELECT 1 FROM source_image_candidate i"
        "   WHERE i.acquisition_job_id = j.id"
        "   AND i.status IN ('queued', 'running', 'downloaded'))"
        " OR EXISTS (SELECT 1 FROM source_image_analysis_call v"
        "   JOIN artifact a ON a.id = v.markdown_artifact_id"
        "   WHERE a.snapshot_id = (SELECT snapshot_id FROM artifact"
        "     WHERE id = j.artifact_id)"
        "   AND v.status IN ('waiting', 'queued', 'running'))"
        ") ORDER BY j.created_at DESC, j.id DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    if downstream is not None:
        conn.commit()
        job = get_job(conn, downstream[0])
        assert job is not None
        job["deduplicated"] = True
        return job

    request_input: dict[str, Any] = {}
    input_fingerprint = None
    video_preflight_id = None
    if source[0] == "video":
        request_input, input_fingerprint, video_preflight_id = acquisition_input(
            conn,
            source_id,
            authorize_paid_transcription=authorize_paid_transcription,
        )

    job_id = f"acq-{uuid.uuid4().hex}"
    inserted = conn.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, provider, video_preflight_id, request_input, input_fingerprint)"
        " VALUES (%s, %s, %s, %s, %s, %s)"
        " ON CONFLICT DO NOTHING RETURNING id",
        (
            job_id,
            source_id,
            _provider_for(source[0]),
            video_preflight_id,
            Jsonb(request_input),
            input_fingerprint,
        ),
    ).fetchone()
    if inserted is None:
        existing = conn.execute(
            "SELECT id FROM acquisition_job"
            " WHERE source_id = %s AND status IN ('queued', 'running')"
            " ORDER BY created_at, id LIMIT 1",
            (source_id,),
        ).fetchone()
        if existing is None:  # a terminal transition raced the insert
            conn.rollback()
            return enqueue_source(
                conn,
                source_id,
                actor=actor,
                authorize_paid_transcription=authorize_paid_transcription,
            )
        job_id = existing[0]
        deduplicated = True
    else:
        deduplicated = False
        conn.execute(
            "INSERT INTO curation_event (id, actor, action, subject)"
            " VALUES (%s, %s, 'source_acquisition_queued', %s)",
            (
                f"ce-acq-{uuid.uuid4().hex}",
                actor,
                Jsonb({"source_id": source_id, "job_id": job_id}),
            ),
        )
    conn.commit()

    job = get_job(conn, job_id)
    assert job is not None
    job["deduplicated"] = deduplicated
    return job


def claim_next_job(
    conn: psycopg.Connection, *, job_id: str | None = None
) -> dict | None:
    """Claim one ready job with a PostgreSQL row lock that never blocks peers.

    An expired lease is claimable again.  This is recovery for a dead worker,
    not a batch retry: the same source-local job advances its attempt counter.
    The running state is committed before this function returns.
    """
    claim_token = uuid.uuid4().hex
    row = conn.execute(
        "WITH candidate AS ("
        " SELECT id FROM acquisition_job"
        " WHERE (%s::text IS NULL OR id = %s)"
        "   AND available_at <= now()"
        "   AND (status = 'queued'"
        "        OR (status = 'running' AND lease_expires_at < now()))"
        " ORDER BY available_at, created_at, id"
        " FOR UPDATE SKIP LOCKED LIMIT 1"
        ")"
        " UPDATE acquisition_job j SET"
        " status = 'running',"
        " attempt_count = j.attempt_count + 1,"
        " claimed_at = now(),"
        " claim_token = %s,"
        " lease_expires_at = now() + (%s * interval '1 minute'),"
        " updated_at = now(),"
        " diagnostics = '{}'::jsonb"
        " FROM candidate WHERE j.id = candidate.id"
        " RETURNING j.id, j.source_id, j.status, j.provider, j.attempt_count,"
        " j.artifact_id, j.failure_code, j.diagnostics, j.created_at,"
        " j.claimed_at, j.claim_token, j.finished_at, j.video_preflight_id,"
        " j.request_input, j.input_fingerprint",
        (job_id, job_id, claim_token, acquisition_lease_minutes()),
    ).fetchone()
    conn.commit()
    return _job_dict(row)


def _source(conn: psycopg.Connection, source_id: str) -> dict:
    row = conn.execute(
        "SELECT id, identity, title, media_type FROM source WHERE id = %s",
        (source_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown source {source_id}")
    return dict(zip(("id", "identity", "title", "media_type"), row))


def _fetch(
    source: dict,
    *,
    video_preflight: dict[str, Any] | None = None,
    video_adapter: VideoAdapter | None = None,
    video_job: dict[str, Any] | None = None,
    conn: psycopg.Connection | None = None,
) -> Outcome:
    if source["media_type"] == "video":
        if video_preflight is None:
            return Outcome(
                None,
                "video_metadata_unavailable",
                YOUTUBE_PROVIDER,
                "youtube-evidence",
                {"category": "video_preflight_missing"},
            )
        try:
            acquired = acquire_video(
                source,
                video_preflight,
                adapter=video_adapter,
                conn=conn,
                job=video_job,
            )
        except VideoAdapterError as exc:
            retry_after = exc.diagnostics.get("retry_after_seconds", 0)
            return Outcome(
                None,
                exc.code,
                YOUTUBE_PROVIDER,
                "youtube-evidence",
                {
                    "category": exc.category,
                    "retriable": exc.retriable,
                    "video_preflight_id": video_preflight["id"],
                    **exc.diagnostics,
                },
                tool_version="youtube-evidence/v1",
                retryable=exc.retriable,
                retry_after_seconds=(
                    int(retry_after)
                    if isinstance(retry_after, (int, float)) and not isinstance(retry_after, bool)
                    else 0
                ),
            )
        except Exception as exc:
            return Outcome(
                None,
                "video_transcript_assembly_failed",
                YOUTUBE_PROVIDER,
                "youtube-evidence",
                {
                    "category": type(exc).__name__,
                    "video_preflight_id": video_preflight["id"],
                },
                tool_version="youtube-evidence/v1",
            )
        return Outcome(
            acquired.markdown,
            None,
            YOUTUBE_PROVIDER,
            "youtube-evidence",
            {
                "category": "success",
                "video_preflight_id": video_preflight["id"],
                "transcript_route": acquired.route,
                "caption_language": acquired.language,
                "segment_count": len(acquired.segments),
                "frame_count": len(acquired.frames),
                "speech_evidence": "present" if acquired.segments else "absent",
                "visual_analysis": "pending" if acquired.frames else "absent",
                "source_media_type": "video",
                "pipeline_requires_cleanup": True,
            },
            tool_version="youtube-evidence/v1",
            content_hash=acquired.content_hash,
            video_acquisition=acquired,
        )

    if source["media_type"] != "article":
        code = "unsupported_media_kind"
        return Outcome(
            None,
            code,
            "none",
            "none",
            {
                "category": "unsupported_media_kind",
                "media_type": source["media_type"],
                "message": GATE_CODES[code]["description"],
            },
        )

    try:
        result: ArticleFetch = fetch_article_detailed(source)
    except Exception as exc:  # an adapter bug must still close the durable job
        return Outcome(
            None,
            "fetch_failed",
            ARTICLE_PROVIDER,
            "firecrawl-v2",
            {"category": "adapter_error", "exception": type(exc).__name__},
        )
    diagnostics = dict(result.diagnostics)
    diagnostics["provider_attempts"] = result.attempts
    if result.failure_code is None and result.markdown:
        diagnostics["pipeline_requires_cleanup"] = True
    return Outcome(
        result.markdown,
        result.failure_code,
        ARTICLE_PROVIDER,
        "firecrawl-v2",
        diagnostics,
        tool_version="firecrawl-v2",
        raw_markdown=result.raw_markdown,
        image_urls=result.image_urls,
    )


def _manual_outcome(
    conn: psycopg.Connection,
    job: dict,
    *,
    asset_store: AssetStore | None = None,
) -> Outcome:
    result = manual_upload_outcome(conn, job, asset_store=asset_store)
    manifest_hash = result.diagnostics.get("input_manifest_sha256")
    return Outcome(
        result.markdown,
        result.failure_code,
        result.provider,
        result.tool,
        result.diagnostics,
        tool_version=result.tool_version,
        content_hash=(
            manifest_hash
            if isinstance(manifest_hash, str) and manifest_hash
            else None
        ),
        raw_markdown=result.raw_markdown,
    )


def _record_success(
    conn: psycopg.Connection,
    job: dict,
    outcome: Outcome,
    *,
    asset_store: AssetStore | None = None,
) -> dict:
    assert outcome.markdown is not None
    captured_body = outcome.raw_markdown or outcome.markdown
    content_hash = outcome.content_hash or hashlib.sha256(
        captured_body.encode()
    ).hexdigest()
    # A snapshot is the fact that this acquisition attempt captured the source
    # at a moment in time.  Its identity is therefore event-scoped, even when
    # two captures happen to yield byte-identical content.  The artifact is the
    # Markdown tool output *from that snapshot*, not the snapshot itself.
    snapshot_id = (
        f"{job['source_id']}:snap:{job['id']}:{job['attempt_count']:02d}"
    )
    artifact_id = f"{snapshot_id}:markdown"
    raw_artifact_id = (
        f"{snapshot_id}:raw-markdown"
        if outcome.raw_markdown is not None
        else None
    )
    has_image_candidates = False
    has_preanalyzed_video_candidates = False

    # Existing good artifacts remain untouched on every later failure.
    artifact_metadata: dict[str, Any] = {}
    if raw_artifact_id is not None:
        artifact_metadata = {
            "raw_artifact_id": raw_artifact_id,
            **(
                {"image_branch": "nonblocking"}
                if outcome.provider == ARTICLE_PROVIDER
                else {
                    "pdf_page_pipeline": PDF_PAGE_TOOL_VERSION,
                    "reconstruction_pipeline": outcome.diagnostics.get(
                        "tool_version", PDF_PAGE_TOOL_VERSION
                    )
                }
            ),
        }
    if outcome.video_acquisition is not None:
        teaching_beats = outcome.video_acquisition.teaching_beats
        artifact_metadata = {
            "transcript_route": outcome.video_acquisition.route,
            "caption_language": outcome.video_acquisition.language,
            "transcript_content_hash": outcome.video_acquisition.content_hash,
            "grouping_version": "timestamp-groups/v1",
            "frame_extractor": outcome.video_acquisition.frame_extractor,
            "frame_count": len(outcome.video_acquisition.frames),
            "speech_evidence": (
                "present" if outcome.video_acquisition.segments else "absent"
            ),
            "visual_analysis": (
                "complete"
                if teaching_beats is not None
                else ("pending" if outcome.video_acquisition.frames else "absent")
            ),
            "visual_interpretation": (
                "video_teaching_beats.v1" if teaching_beats is not None else None
            ),
            "teaching_beat_count": (
                len(teaching_beats.beats) if teaching_beats is not None else 0
            ),
            "source_media_type": "video",
            "pipeline_requires_cleanup": True,
        }
    conn.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, captured_at, content_hash, status, failure_note)"
        " VALUES (%s, %s, now(), %s, 'ok', NULL) ON CONFLICT (id) DO NOTHING",
        (snapshot_id, job["source_id"], content_hash),
    )
    conn.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, tool_version, body, metadata)"
        " VALUES (%s, %s, 'markdown', %s, %s, %s, %s)"
        " ON CONFLICT (id) DO NOTHING",
        (
            artifact_id,
            snapshot_id,
            outcome.tool,
            outcome.tool_version,
            outcome.markdown,
            Jsonb(artifact_metadata),
        ),
    )
    if raw_artifact_id is not None:
        extractor = outcome.diagnostics.get("extractor") or {}
        raw_tool = (
            PDF_TEXT_TOOL
            if extractor.get("document_tool") == PDF_TEXT_TOOL
            else outcome.tool
        )
        raw_tool_version = (
            PDF_TEXT_TOOL_VERSION
            if raw_tool == PDF_TEXT_TOOL
            else outcome.tool_version
        )
        conn.execute(
            "INSERT INTO artifact"
            " (id, snapshot_id, kind, tool, tool_version, body, metadata)"
            " VALUES (%s, %s, 'raw-markdown', %s, %s, %s, %s)"
            " ON CONFLICT (id) DO NOTHING",
            (
                raw_artifact_id,
                snapshot_id,
                raw_tool,
                raw_tool_version,
                outcome.raw_markdown,
                Jsonb({"canonical_artifact_id": artifact_id}),
            ),
        )
        if outcome.provider == ARTICLE_PROVIDER:
            image_candidates = insert_article_image_candidates(
                conn,
                acquisition_job_id=job["id"],
                source_id=job["source_id"],
                snapshot_id=snapshot_id,
                markdown_artifact_id=artifact_id,
                markdown=outcome.raw_markdown,
                firecrawl_urls=outcome.image_urls,
                base_url=(
                    outcome.diagnostics.get("resolved_url")
                    if isinstance(outcome.diagnostics.get("resolved_url"), str)
                    else None
                ),
            )
            has_image_candidates = bool(image_candidates)
    if outcome.video_acquisition is not None:
        if outcome.video_acquisition.frames:
            store = asset_store or asset_store_from_env()
            video_id = str(
                _source(conn, job["source_id"])["identity"]["video_id"]
            ).strip()
            if outcome.video_acquisition.teaching_beats is not None:
                reading_call_id = persist_teaching_beat_reading(
                    conn,
                    markdown_artifact_id=artifact_id,
                    document=outcome.video_acquisition.teaching_beats,
                )
                frame_candidates = insert_teaching_beat_candidates(
                    conn,
                    acquisition_job_id=job["id"],
                    source_id=job["source_id"],
                    snapshot_id=snapshot_id,
                    markdown_artifact_id=artifact_id,
                    markdown=outcome.markdown,
                    video_id=video_id,
                    document=outcome.video_acquisition.teaching_beats,
                    analysis_call_id=reading_call_id,
                    asset_store=store,
                    extractor_ref=(
                        outcome.video_acquisition.frame_extractor
                        or "gemini-teaching-beats/v1"
                    ),
                )
                has_preanalyzed_video_candidates = bool(frame_candidates)
            else:
                frame_candidates = insert_video_frame_candidates(
                    conn,
                    acquisition_job_id=job["id"],
                    source_id=job["source_id"],
                    snapshot_id=snapshot_id,
                    markdown_artifact_id=artifact_id,
                    markdown=outcome.markdown,
                    video_id=video_id,
                    frames=outcome.video_acquisition.frames,
                    asset_store=store,
                    extractor_ref=(
                        outcome.video_acquisition.frame_extractor
                        or "video-frame-extraction/unknown"
                    ),
                )
            has_image_candidates = bool(frame_candidates)
        persist_video_transcript(
            conn,
            job=job,
            snapshot_id=snapshot_id,
            artifact_id=artifact_id,
            acquisition=outcome.video_acquisition,
        )
    requires_cleanup = bool(
        outcome.provider == ARTICLE_PROVIDER
        or outcome.diagnostics.get("pipeline_requires_cleanup")
    )
    updated = conn.execute(
        "UPDATE acquisition_job SET status = 'succeeded', artifact_id = %s,"
        " diagnostics = %s, finished_at = now(), lease_expires_at = NULL,"
        " claim_token = NULL, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (
            artifact_id,
            Jsonb(
                {
                    **outcome.diagnostics,
                    **(
                        {"pipeline_requires_cleanup": True}
                        if requires_cleanup
                        else {}
                    ),
                }
            ),
            job["id"],
            job["claim_token"],
        ),
    )
    if updated.rowcount != 1:
        # Every fact above belongs to this claim.  If its lease was reclaimed,
        # roll the whole transaction back so the stale capture cannot leak into
        # the append-only ledger as an orphan snapshot or artifact.
        conn.rollback()
        result = get_job(conn, job["id"])
        assert result is not None
        return result
    if (
        requires_cleanup
        and not has_image_candidates
        and not outcome.diagnostics.get("visual_incomplete")
    ):
        enqueue_source_cleanup(
            conn,
            acquisition_job_id=job["id"],
            source_artifact_id=artifact_id,
            commit=False,
        )
    conn.commit()
    if has_preanalyzed_video_candidates:
        finalize_article_image_association(conn, artifact_id)
    elif has_image_candidates:
        queue_source_image_analysis_if_ready(conn, artifact_id)
    result = get_job(conn, job["id"])
    assert result is not None
    return result


def _record_failure(
    conn: psycopg.Connection, job: dict, outcome: Outcome
) -> dict:
    failure_code = outcome.failure_code or "fetch_failed"
    # A failure is a fact too.  Job id + lease attempt prevents the old
    # `:snap:failed` collision from swallowing later diagnostics.
    snapshot_id = (
        f"{job['source_id']}:snap:failed:{job['id']}:{job['attempt_count']:02d}"
    )
    conn.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, captured_at, content_hash, status, failure_note)"
        " VALUES (%s, %s, NULL, NULL, 'failed', %s) ON CONFLICT (id) DO NOTHING",
        (snapshot_id, job["source_id"], failure_code),
    )
    updated = conn.execute(
        "UPDATE acquisition_job SET status = 'failed', failure_code = %s,"
        " diagnostics = %s, finished_at = now(), lease_expires_at = NULL,"
        " claim_token = NULL, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (
            failure_code,
            Jsonb(outcome.diagnostics),
            job["id"],
            job["claim_token"],
        ),
    )
    if updated.rowcount != 1:
        conn.rollback()
        result = get_job(conn, job["id"])
        assert result is not None
        return result
    conn.commit()
    result = get_job(conn, job["id"])
    assert result is not None
    return result


def _record_retry(
    conn: psycopg.Connection, job: dict, outcome: Outcome
) -> dict:
    """Release a transient claim while retaining durable partial evidence."""
    updated = conn.execute(
        "UPDATE acquisition_job SET status = 'queued',"
        " available_at = now() + (%s * interval '1 second'),"
        " diagnostics = %s, claimed_at = NULL, lease_expires_at = NULL,"
        " claim_token = NULL, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (
            max(0, int(outcome.retry_after_seconds)),
            Jsonb(
                {
                    **outcome.diagnostics,
                    "retry_scheduled": True,
                    "attempt_count": job["attempt_count"],
                }
            ),
            job["id"],
            job["claim_token"],
        ),
    )
    if updated.rowcount != 1:
        conn.rollback()
    else:
        conn.commit()
    result = get_job(conn, job["id"])
    assert result is not None
    return result


def process_next_job(
    conn: psycopg.Connection,
    *,
    job_id: str | None = None,
    asset_store: AssetStore | None = None,
    book_adapter: BookCaptureAdapter | None = None,
    book_document_parser=None,
    book_image_downloader=None,
    book_figure_locator=None,
    book_pdf_builder=None,
    video_adapter: VideoAdapter | None = None,
) -> dict | None:
    """Claim one acquisition and queue its required downstream Markdown work."""
    job = claim_next_job(conn, job_id=job_id)
    if job is None:
        return None
    try:
        if job["provider"] == MANUAL_PROVIDER:
            outcome = _manual_outcome(conn, job, asset_store=asset_store)
        elif job["provider"] == BOOK_PROVIDER:
            book_kwargs = {}
            if book_document_parser is not None:
                book_kwargs["document_parser"] = book_document_parser
            if book_image_downloader is not None:
                book_kwargs["image_downloader"] = book_image_downloader
            if book_figure_locator is not None:
                book_kwargs["figure_locator"] = book_figure_locator
            if book_pdf_builder is not None:
                book_kwargs["pdf_builder"] = book_pdf_builder
            result = book_capture_outcome(
                conn,
                job,
                adapter=book_adapter,
                asset_store=asset_store,
                **book_kwargs,
            )
            outcome = Outcome(
                result.markdown,
                result.failure_code,
                result.provider,
                result.tool,
                result.diagnostics,
                tool_version=result.tool_version,
                content_hash=result.content_hash,
                raw_markdown=result.raw_markdown,
                retryable=result.retryable,
                retry_after_seconds=result.retry_after_seconds,
            )
        else:
            source = _source(conn, job["source_id"])
            video_preflight = (
                get_preflight(conn, job["video_preflight_id"])
                if job["provider"] == YOUTUBE_PROVIDER
                and job.get("video_preflight_id")
                else None
            )
            # Do not leave a read transaction open during a potentially slow
            # provider request.  The running job was already committed by claim.
            conn.commit()
            if job["provider"] == YOUTUBE_PROVIDER:
                outcome = _fetch(
                    source,
                    video_preflight=video_preflight,
                    video_adapter=video_adapter,
                    video_job=job,
                    conn=conn,
                )
            else:
                outcome = _fetch(source)
    except Exception as exc:
        outcome = Outcome(
            None,
            "fetch_failed",
            job["provider"],
            "none",
            {"category": "worker_error", "exception": type(exc).__name__},
        )
    if outcome.succeeded:
        return _record_success(conn, job, outcome, asset_store=asset_store)
    if outcome.retryable and job["attempt_count"] < 3:
        return _record_retry(conn, job, outcome)
    if outcome.retryable:
        outcome = Outcome(
            outcome.markdown,
            outcome.failure_code,
            outcome.provider,
            outcome.tool,
            {**outcome.diagnostics, "retry_exhausted": True},
            tool_version=outcome.tool_version,
            content_hash=outcome.content_hash,
        )
    return _record_failure(conn, job, outcome)


def _oldest_ready_work_kind(conn: psycopg.Connection) -> str | None:
    """Choose fairly across queues without holding a lock during provider I/O."""
    row = conn.execute(
        "SELECT kind FROM ("
        " SELECT 'acquisition'::text AS kind, available_at, created_at, id"
        " FROM acquisition_job"
        " WHERE available_at <= now() AND (status = 'queued'"
        "   OR (status = 'running' AND lease_expires_at < now()))"
        " UNION ALL"
        " SELECT 'article_image'::text AS kind, available_at, created_at, id"
        " FROM source_image_candidate"
        " WHERE available_at <= now() AND (status = 'queued'"
        "   OR (status = 'running' AND lease_expires_at < now()))"
        " UNION ALL"
        " SELECT 'source_image_analysis'::text AS kind, available_at, created_at, id"
        " FROM source_image_analysis_call"
        " WHERE available_at <= now() AND (status = 'queued'"
        "   OR (status = 'running' AND lease_expires_at < now()))"
        " UNION ALL"
        " SELECT 'source_cleanup'::text AS kind, available_at, created_at, id"
        " FROM source_cleanup_job"
        " WHERE available_at <= now() AND (status = 'queued'"
        "   OR (status = 'running' AND lease_expires_at < now()))"
        ") ready ORDER BY available_at, created_at, id LIMIT 1"
    ).fetchone()
    conn.commit()
    return row[0] if row else None


def process_next_work_item(
    conn: psycopg.Connection,
    *,
    asset_store: AssetStore | None = None,
    video_adapter: VideoAdapter | None = None,
) -> tuple[str, dict] | None:
    """Process the oldest acquisition, visual or canonical-cleanup work item."""
    preferred = _oldest_ready_work_kind(conn)
    if preferred is None:
        return None
    def process_acquisition() -> dict | None:
        kwargs: dict[str, Any] = {"asset_store": asset_store}
        if video_adapter is not None:
            kwargs["video_adapter"] = video_adapter
        return process_next_job(conn, **kwargs)

    processors = {
        "acquisition": process_acquisition,
        "article_image": lambda: process_next_article_image(
            conn, asset_store=asset_store
        ),
        "source_image_analysis": lambda: process_next_source_image_analysis(
            conn, asset_store=asset_store
        ),
        "source_cleanup": lambda: process_next_source_cleanup(conn),
    }
    for kind in (
        preferred,
        *(item for item in processors if item != preferred),
    ):
        payload = processors[kind]()
        if payload is not None:
            return kind, payload
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="universe.acquisition",
        description="Queue or process one explicit source acquisition.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    enqueue = commands.add_parser("enqueue", help="queue exactly one source")
    enqueue.add_argument("source_id", type=_one_source_id)
    enqueue.set_defaults(func=cmd_enqueue)

    work = commands.add_parser("work", help="process queued source jobs")
    work.add_argument("--job", dest="job_id")
    work.add_argument(
        "--forever",
        action="store_true",
        help="keep polling the durable queue (for a local or Railway worker)",
    )
    work.set_defaults(func=cmd_work)
    return parser


def cmd_enqueue(args: argparse.Namespace) -> None:
    with connect() as conn:
        job = enqueue_source(conn, args.source_id)
    suffix = " (already queued)" if job["deduplicated"] else ""
    print(f"queued {job['source_id']} as {job['id']}{suffix}")


def cmd_work(args: argparse.Namespace) -> None:
    while True:
        with connect() as conn:
            job = None
            work_kind = None
            work_payload = None
            if args.job_id is not None:
                # An explicit --job means exactly that parent acquisition.
                job = process_next_job(conn, job_id=args.job_id)
            else:
                work_item = process_next_work_item(conn)
                if work_item is not None:
                    work_kind, work_payload = work_item
                    if work_kind == "acquisition":
                        job = work_payload
                    else:
                        job = None
        if job is not None:
            print(json.dumps({key: job[key] for key in (
                "id", "source_id", "status", "artifact_id", "failure_code"
            )}, default=str), flush=True)
        elif work_payload is not None and work_kind == "article_image":
            print(
                json.dumps(
                    {
                        "kind": work_kind,
                        **{
                            key: work_payload[key]
                            for key in (
                                "id", "source_id", "status", "asset_id", "failure_code"
                            )
                        },
                    },
                    default=str,
                ),
                flush=True,
            )
        elif work_payload is not None and work_kind == "source_image_analysis":
            print(
                json.dumps(
                    {
                        "kind": work_kind,
                        **{
                            key: work_payload[key]
                            for key in (
                                "id", "markdown_artifact_id", "status", "failure_code"
                            )
                        },
                    },
                    default=str,
                ),
                flush=True,
            )
        elif not args.forever:
            print("no acquisition or article image job ready")
        if not args.forever:
            return
        time.sleep(
            0
            if job is not None or work_payload is not None
            else acquisition_poll_seconds()
        )


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
