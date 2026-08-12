"""Durable, non-blocking article-image acquisition jobs.

Text Markdown is committed before this queue is consumed.  Each candidate is
then downloaded, stored and interpreted independently; no image outcome can
move the parent acquisition job away from ``succeeded``.
"""

from __future__ import annotations

import base64
import hashlib
import io
import ipaddress
import json
import re
import socket
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import unquote, urljoin, urlsplit

import httpx
import psycopg
from PIL import Image, ImageOps, UnidentifiedImageError
from psycopg.types.json import Jsonb

from universe.acquisition.article_images import (
    ARTICLE_IMAGE_PROMPT_VERSION,
    ArticleImageAnalysis,
    ArticleImageModelResult,
    ArticleImageReference,
    _model_image_transport,
    analyze_article_image,
    extract_markdown_images,
)
from universe.acquisition.manual_uploads import ManualAsset, validate_manual_assets
from universe.acquisition.job_lease import (
    ConnectionFactory,
    JobLease,
    separate_connection_factory,
)
from universe.acquisition.source_images import (
    SourceImageAnalysis,
    SourceImageBatchResult,
    SourceImageInput,
    analyze_source_images,
    prompt_stamp,
)
from universe.acquisition.video_teaching_beats import TeachingBeatDocument, validate_document
from universe.assets import AssetStore, asset_store_from_env
from universe.model_client import ModelClient, ModelError
from universe.settings import (
    acquisition_lease_minutes,
    article_image_model,
    openrouter_multimodal_provider_routing,
)


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 4
MODEL_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}
CONVERTIBLE_MODEL_IMAGE_MIMES = {"image/avif", "image/gif"}
PRESERVABLE_IMAGE_MIMES = MODEL_IMAGE_MIMES | CONVERTIBLE_MODEL_IMAGE_MIMES | {
    "image/svg+xml"
}
MAX_IMAGE_PIXELS = 40_000_000
MAX_MODEL_IMAGE_EDGE = 2048
MAX_MODEL_IMAGE_BYTES = 1536 * 1024
IMAGE_USER_AGENT = "ConceptUniverseImageAcquisition/1.0"
ARTICLE_IMAGE_ASSOCIATION_VERSION = "article-image-association.v1"


@dataclass(frozen=True)
class DownloadedImage:
    body: bytes
    mime_type: str
    filename: str
    final_url: str
    width: int
    height: int
    sha256: str


class ImageJobError(RuntimeError):
    def __init__(self, code: str, category: str, diagnostics: Mapping[str, Any] | None = None):
        self.code = code
        self.category = category
        self.diagnostics = dict(diagnostics or {})
        super().__init__(code)


IMAGE_JOB_COLUMNS = (
    "id",
    "acquisition_job_id",
    "source_id",
    "snapshot_id",
    "markdown_artifact_id",
    "ordinal",
    "original_url",
    "alt_text",
    "placement",
    "status",
    "filter_reason",
    "failure_code",
    "diagnostics",
    "asset_id",
    "analysis_id",
    "attempt_count",
    "claimed_at",
    "claim_token",
    "finished_at",
    "created_at",
)

SOURCE_IMAGE_CALL_COLUMNS = (
    "id",
    "markdown_artifact_id",
    "prompt_ref",
    "prompt_sha",
    "requested_model",
    "input_manifest_hash",
    "status",
    "attempt_count",
    "claimed_at",
    "claim_token",
    "response_model",
    "provider",
    "usage",
    "duration_ms",
    "failure_code",
    "diagnostics",
    "finished_at",
    "created_at",
)


def prepare_article_image_candidates(
    markdown: str,
    firecrawl_urls: Sequence[str] = (),
    *,
    base_url: str | None = None,
) -> list[dict[str, Any]]:
    """Collect every occurrence and apply only technical URL guards.

    This function performs no network or model call.  Duplicate URLs share one
    candidate and retain all Markdown placements in its metadata. Candidate
    volume, filenames and alt text are never used as relevance decisions.
    """
    references = extract_markdown_images(markdown)
    grouped: dict[str, list[ArticleImageReference]] = {}
    provider_urls: set[str] = set()
    ordered_urls: list[str] = []
    for reference in references:
        url = _candidate_url(reference.source_url, base_url)
        if url not in grouped:
            grouped[url] = []
            ordered_urls.append(url)
        grouped[url].append(reference)
    for raw_url in firecrawl_urls:
        url = _candidate_url(str(raw_url or ""), base_url)
        if not url:
            continue
        provider_urls.add(url)
        if url not in grouped:
            grouped[url] = []
            ordered_urls.append(url)

    candidates: list[dict[str, Any]] = []
    for ordinal, url in enumerate(ordered_urls, start=1):
        occurrences = grouped[url]
        placement = {
            "occurrences": [
                {
                    "ordinal": item.ordinal,
                    "start_char": item.start_char,
                    "end_char": item.end_char,
                    "link_url": item.link_url,
                    "reference_id": item.reference_id,
                    "reference_sha256": item.raw_sha256,
                    "original_markdown": item.original_markdown,
                    "alt_text": item.alt_text,
                }
                for item in occurrences
            ],
            "document_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            "discovered_by": [
                channel
                for channel, present in (
                    ("markdown", bool(occurrences)),
                    ("firecrawl_images", url in provider_urls),
                )
                if present
            ],
        }
        alt_text = next((item.alt_text for item in occurrences if item.alt_text), "")
        status = "queued"
        reason = None
        failure_code = None
        diagnostics: dict[str, Any] = {}
        if not _valid_remote_url_shape(url):
            status = "failed"
            failure_code = "invalid_image_url"
            diagnostics = {"category": "invalid_image_url"}
        candidates.append(
            {
                "ordinal": ordinal,
                "original_url": url,
                "alt_text": alt_text,
                "placement": placement,
                "status": status,
                "filter_reason": reason,
                "failure_code": failure_code,
                "diagnostics": diagnostics,
            }
        )
    return candidates


def insert_article_image_candidates(
    conn: psycopg.Connection,
    *,
    acquisition_job_id: str,
    source_id: str,
    snapshot_id: str,
    markdown_artifact_id: str,
    markdown: str,
    firecrawl_urls: Sequence[str] = (),
    base_url: str | None = None,
) -> list[dict[str, Any]]:
    """Insert every candidate outcome in the parent's success transaction."""
    prepared = prepare_article_image_candidates(
        markdown, firecrawl_urls, base_url=base_url
    )
    inserted: list[dict[str, Any]] = []
    for item in prepared:
        candidate_id = f"{acquisition_job_id}:image:{item['ordinal']:04d}"
        terminal = item["status"] != "queued"
        conn.execute(
            "INSERT INTO source_image_candidate"
            " (id, acquisition_job_id, source_id, snapshot_id, markdown_artifact_id,"
            "  ordinal, original_url, alt_text, placement, status, filter_reason,"
            "  failure_code, diagnostics, finished_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
            "         CASE WHEN %s THEN now() ELSE NULL END)",
            (
                candidate_id,
                acquisition_job_id,
                source_id,
                snapshot_id,
                markdown_artifact_id,
                item["ordinal"],
                item["original_url"],
                item["alt_text"],
                Jsonb(item["placement"]),
                item["status"],
                item["filter_reason"],
                item["failure_code"],
                Jsonb(item["diagnostics"]),
                terminal,
            ),
        )
        inserted.append({"id": candidate_id, **item})
    if inserted:
        prompt_ref, prompt_sha, _template = prompt_stamp()
        call_id = f"{markdown_artifact_id}:source-images:{prompt_sha[:16]}"
        conn.execute(
            "INSERT INTO source_image_analysis_call"
            " (id, markdown_artifact_id, prompt_ref, prompt_sha, requested_model, status)"
            " VALUES (%s, %s, %s, %s, %s, 'waiting')"
            " ON CONFLICT (markdown_artifact_id, prompt_ref) DO NOTHING",
            (
                call_id,
                markdown_artifact_id,
                prompt_ref,
                prompt_sha,
                article_image_model(),
            ),
        )
    return inserted


def insert_video_frame_candidates(
    conn: psycopg.Connection,
    *,
    acquisition_job_id: str,
    source_id: str,
    snapshot_id: str,
    markdown_artifact_id: str,
    markdown: str,
    video_id: str,
    frames: Sequence[Any],
    asset_store: AssetStore,
    extractor_ref: str,
) -> list[dict[str, Any]]:
    return _insert_video_frame_candidates(
        conn,
        acquisition_job_id=acquisition_job_id,
        source_id=source_id,
        snapshot_id=snapshot_id,
        markdown_artifact_id=markdown_artifact_id,
        markdown=markdown,
        video_id=video_id,
        frames=frames,
        asset_store=asset_store,
        extractor_ref=extractor_ref,
        teaching_document=None,
        teaching_beat_call_id=None,
    )


def insert_teaching_beat_candidates(
    conn: psycopg.Connection,
    *,
    acquisition_job_id: str,
    source_id: str,
    snapshot_id: str,
    markdown_artifact_id: str,
    markdown: str,
    video_id: str,
    document: TeachingBeatDocument,
    analysis_call_id: str,
    asset_store: AssetStore,
    extractor_ref: str,
) -> list[dict[str, Any]]:
    """Project one whole-video reading into terminal atomic visual evidence."""
    document = validate_document(document)
    return _insert_video_frame_candidates(
        conn,
        acquisition_job_id=acquisition_job_id,
        source_id=source_id,
        snapshot_id=snapshot_id,
        markdown_artifact_id=markdown_artifact_id,
        markdown=markdown,
        video_id=video_id,
        frames=document.frames,
        asset_store=asset_store,
        extractor_ref=extractor_ref,
        teaching_document=document,
        teaching_beat_call_id=analysis_call_id,
    )


def _insert_video_frame_candidates(
    conn: psycopg.Connection,
    *,
    acquisition_job_id: str,
    source_id: str,
    snapshot_id: str,
    markdown_artifact_id: str,
    markdown: str,
    video_id: str,
    frames: Sequence[Any],
    asset_store: AssetStore,
    extractor_ref: str,
    teaching_document: TeachingBeatDocument | None,
    teaching_beat_call_id: str | None,
) -> list[dict[str, Any]]:
    """Persist locally extracted frames directly into the visual-analysis Seam.

    Frames already have immutable bytes, so they intentionally bypass the
    public-URL download queue. Their ordinary Markdown occurrences let the
    existing association Implementation localize retained frames in place.
    """
    references_by_url: dict[str, list[ArticleImageReference]] = {}
    for reference in extract_markdown_images(markdown):
        references_by_url.setdefault(reference.source_url, []).append(reference)
    document_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    inserted: list[dict[str, Any]] = []
    for ordinal, frame in enumerate(frames, 1):
        timestamp_ms = int(frame.timestamp_ms)
        locator = f"video-frame://{video_id}/{timestamp_ms}"
        occurrences = references_by_url.get(locator, [])
        if len(occurrences) != 1:
            raise ImageJobError(
                "video_frame_reference_invalid",
                "frame_markdown_reference_mismatch",
                {"locator": locator, "occurrence_count": len(occurrences)},
            )
        body = bytes(frame.body)
        if not body or len(body) > MAX_IMAGE_BYTES:
            raise ImageJobError(
                "video_frame_invalid", "invalid_frame_size", {"byte_size": len(body)}
            )
        try:
            with Image.open(io.BytesIO(body)) as decoded:
                width, height = decoded.size
                decoded.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageJobError(
                "video_frame_invalid", "unreadable_frame"
            ) from exc
        if width <= 0 or height <= 0:
            raise ImageJobError("video_frame_invalid", "invalid_frame_dimensions")
        digest = hashlib.sha256(body).hexdigest()
        if digest != str(frame.sha256):
            raise ImageJobError("video_frame_invalid", "frame_hash_mismatch")
        stored = asset_store.put(body, sha256=digest)
        candidate_id = f"{acquisition_job_id}:image:{ordinal:04d}"
        asset_id = f"{candidate_id}:asset"
        filename = Path(str(frame.filename or f"frame-{ordinal:04d}.png")).name
        conn.execute(
            "INSERT INTO source_asset"
            " (id, acquisition_job_id, source_id, ordinal, kind, filename, mime_type,"
            " sha256, byte_size, storage_key, metadata, original_url)"
            " VALUES (%s, %s, %s, %s, 'video_frame', %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (id) DO NOTHING",
            (
                asset_id,
                acquisition_job_id,
                source_id,
                ordinal,
                filename,
                str(frame.mime_type),
                digest,
                len(body),
                stored.key,
                Jsonb(
                    {
                        "timestamp_ms": timestamp_ms,
                        "width": width,
                        "height": height,
                        "extractor_ref": extractor_ref,
                        "video_id": video_id,
                    }
                ),
                locator,
            ),
        )
        reference = occurrences[0]
        placement = {
            "timestamp_ms": timestamp_ms,
            "document_sha256": document_hash,
            "discovered_by": ["video_frame_extraction"],
            "occurrences": [
                {
                    "ordinal": reference.ordinal,
                    "start_char": reference.start_char,
                    "end_char": reference.end_char,
                    "link_url": reference.link_url,
                    "reference_id": reference.reference_id,
                    "reference_sha256": reference.raw_sha256,
                    "original_markdown": reference.original_markdown,
                    "alt_text": reference.alt_text,
                }
            ],
        }
        analysis_id = None
        candidate_status = "downloaded"
        candidate_diagnostics = {
            "category": "downloaded",
            "asset_sha256": digest,
            "source_mime_type": str(frame.mime_type),
            "timestamp_ms": timestamp_ms,
        }
        if teaching_document is not None:
            beat = teaching_document.beats[ordinal - 1]
            if beat.frame_ms != timestamp_ms or teaching_beat_call_id is None:
                raise ImageJobError(
                    "video_teaching_beat_invalid",
                    "teaching_beat_frame_mismatch",
                    {"ordinal": ordinal, "timestamp_ms": timestamp_ms},
                )
            analysis_id = f"{candidate_id}:teaching-beat-analysis"
            description = beat.explanation.strip()
            if beat.visual_description.strip():
                description += (
                    " Visual organization: " + beat.visual_description.strip()
                )
            conn.execute(
                "INSERT INTO source_asset_analysis"
                " (id, source_asset_id, purpose, status, prompt_version,"
                " requested_model, response_model, provider, result, usage,"
                " duration_ms, diagnostics, analysis_call_id)"
                " VALUES (%s, %s, 'video_teaching_beat', 'succeeded', %s, %s,"
                " %s, %s, %s, '{}', NULL, %s, %s) ON CONFLICT (id) DO NOTHING",
                (
                    analysis_id,
                    asset_id,
                    teaching_document.prompt_ref,
                    teaching_document.requested_model,
                    teaching_document.response_model,
                    teaching_document.provider,
                    Jsonb(
                        {
                            "image_id": candidate_id,
                            "retain": True,
                            "reason_code": "teaching_beat",
                            "ocr": beat.visible_text,
                            "description": description,
                            "limitations": beat.limitations,
                        }
                    ),
                    Jsonb(
                        {
                            "analysis_call_id": teaching_beat_call_id,
                            "beat_ordinal": ordinal,
                            "timestamp_ms": timestamp_ms,
                            "asset_sha256": digest,
                            "input_manifest_hash": teaching_document.input_manifest_hash,
                            "result_hash": teaching_document.result_hash,
                        }
                    ),
                    teaching_beat_call_id,
                ),
            )
            candidate_status = "useful"
            candidate_diagnostics = {
                "category": "teaching_beat",
                "asset_sha256": digest,
                "source_mime_type": str(frame.mime_type),
                "timestamp_ms": timestamp_ms,
                "analysis_call_id": teaching_beat_call_id,
                "beat_ordinal": ordinal,
                "result_hash": teaching_document.result_hash,
            }
        conn.execute(
            "INSERT INTO source_image_candidate"
            " (id, acquisition_job_id, source_id, snapshot_id, markdown_artifact_id,"
            " ordinal, original_url, alt_text, placement, status, diagnostics,"
            " asset_id, analysis_id, finished_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())"
            " ON CONFLICT (id) DO NOTHING",
            (
                candidate_id,
                acquisition_job_id,
                source_id,
                snapshot_id,
                markdown_artifact_id,
                ordinal,
                locator,
                reference.alt_text,
                Jsonb(placement),
                candidate_status,
                Jsonb(candidate_diagnostics),
                asset_id,
                analysis_id,
            ),
        )
        inserted.append(
            {
                "id": candidate_id,
                "asset_id": asset_id,
                "ordinal": ordinal,
                "original_url": locator,
                "timestamp_ms": timestamp_ms,
            }
        )
    if inserted and teaching_document is None:
        _ensure_source_image_analysis_call(conn, markdown_artifact_id)
    return inserted


def get_article_image_candidate(
    conn: psycopg.Connection, candidate_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, acquisition_job_id, source_id, snapshot_id, markdown_artifact_id,"
        " ordinal, original_url, alt_text, placement, status, filter_reason,"
        " failure_code, diagnostics, asset_id, analysis_id, attempt_count,"
        " claimed_at, claim_token, finished_at, created_at"
        " FROM source_image_candidate WHERE id = %s",
        (candidate_id,),
    ).fetchone()
    return dict(zip(IMAGE_JOB_COLUMNS, row)) if row else None


def claim_next_article_image(
    conn: psycopg.Connection, *, candidate_id: str | None = None
) -> dict[str, Any] | None:
    token = uuid.uuid4().hex
    row = conn.execute(
        "WITH candidate AS ("
        " SELECT id FROM source_image_candidate"
        " WHERE (%s::text IS NULL OR id = %s)"
        "   AND available_at <= now()"
        "   AND (status = 'queued'"
        "        OR (status = 'running' AND lease_expires_at < now()))"
        " ORDER BY available_at, created_at, id"
        " FOR UPDATE SKIP LOCKED LIMIT 1"
        ")"
        " UPDATE source_image_candidate j SET status = 'running',"
        " attempt_count = j.attempt_count + 1, claimed_at = now(), claim_token = %s,"
        " lease_expires_at = now() + (%s * interval '1 minute'), updated_at = now(),"
        " diagnostics = '{}'::jsonb"
        " FROM candidate WHERE j.id = candidate.id"
        " RETURNING j.id, j.acquisition_job_id, j.source_id, j.snapshot_id,"
        " j.markdown_artifact_id, j.ordinal, j.original_url, j.alt_text, j.placement,"
        " j.status, j.filter_reason, j.failure_code, j.diagnostics, j.asset_id,"
        " j.analysis_id, j.attempt_count, j.claimed_at, j.claim_token,"
        " j.finished_at, j.created_at",
        (candidate_id, candidate_id, token, acquisition_lease_minutes()),
    ).fetchone()
    conn.commit()
    return dict(zip(IMAGE_JOB_COLUMNS, row)) if row else None


def process_next_article_image(
    conn: psycopg.Connection,
    *,
    candidate_id: str | None = None,
    asset_store: AssetStore | None = None,
    downloader: Callable[[str], DownloadedImage] | None = None,
    analyzer: Callable[[str, list[SourceImageInput]], SourceImageBatchResult]
    | None = None,
    lease_connection_factory: ConnectionFactory | None = None,
) -> dict[str, Any] | None:
    """Download and preserve one candidate, without making a semantic call.

    Once every candidate of the source has a technical outcome, one separate
    source-level call is queued.  ``analyzer`` is an injection seam for focused
    tests: when supplied, the newly-ready group is processed immediately.
    Production workers leave it to the durable analysis-call queue.
    """
    heartbeat_connection = (
        lease_connection_factory or separate_connection_factory(conn)
    )
    job = claim_next_article_image(conn, candidate_id=candidate_id)
    if job is None:
        return None
    store = asset_store or asset_store_from_env()
    download = downloader or download_public_image
    asset: dict[str, Any] | None = None
    try:
        with JobLease(
            heartbeat_connection,
            table="source_image_candidate",
            row_id=job["id"],
            claim_token=job["claim_token"],
        ):
            asset = _existing_asset(conn, job)
            if asset is None:
                downloaded = download(job["original_url"])
                try:
                    stored = store.put(downloaded.body, sha256=downloaded.sha256)
                except Exception as exc:
                    raise ImageJobError(
                        "image_asset_storage_failed",
                        "asset_storage_write_failed",
                        {"exception": type(exc).__name__},
                    ) from exc
                asset = _insert_article_asset(conn, job, downloaded, stored.key)
                if asset is None:
                    conn.rollback()
                    return _current_candidate(conn, str(job["id"]))
                conn.commit()

        if not _claim_is_owned(conn, job):
            conn.rollback()
            return _current_candidate(conn, str(job["id"]))
        result = _finish_candidate(
            conn,
            job,
            status="downloaded",
            failure_code=None,
            asset_id=asset["id"],
            diagnostics={
                "category": "downloaded",
                "source_mime_type": asset["mime_type"],
                "asset_sha256": asset["sha256"],
            },
        )
        call = queue_source_image_analysis_if_ready(
            conn, str(job["markdown_artifact_id"])
        )
        if analyzer is not None and call and call["status"] == "queued":
            process_next_source_image_analysis(
                conn,
                call_id=call["id"],
                asset_store=store,
                analyzer=analyzer,
                lease_connection_factory=heartbeat_connection,
            )
            result = _current_candidate(conn, str(job["id"]))
        return result
    except ImageJobError as exc:
        conn.rollback()
        diagnostics = {"category": exc.category, **exc.diagnostics}
        result = _finish_candidate(
            conn,
            job,
            status="failed",
            failure_code=exc.code,
            asset_id=asset["id"] if asset else None,
            diagnostics=diagnostics,
        )
        queue_source_image_analysis_if_ready(
            conn, str(job["markdown_artifact_id"])
        )
        return result
    except Exception as exc:
        conn.rollback()
        result = _finish_candidate(
            conn,
            job,
            status="failed",
            failure_code="image_processing_failed",
            asset_id=asset["id"] if asset else None,
            diagnostics={
                "category": "image_processing_failed",
                "exception": type(exc).__name__,
            },
        )
        queue_source_image_analysis_if_ready(
            conn, str(job["markdown_artifact_id"])
        )
        return result


def get_source_image_analysis_call(
    conn: psycopg.Connection, call_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, markdown_artifact_id, prompt_ref, prompt_sha, requested_model,"
        " input_manifest_hash, status, attempt_count, claimed_at, claim_token,"
        " response_model, provider, usage, duration_ms, failure_code, diagnostics,"
        " finished_at, created_at FROM source_image_analysis_call WHERE id = %s",
        (call_id,),
    ).fetchone()
    return dict(zip(SOURCE_IMAGE_CALL_COLUMNS, row)) if row else None


def _ensure_source_image_analysis_call(
    conn: psycopg.Connection, markdown_artifact_id: str
) -> dict[str, Any] | None:
    count = conn.execute(
        "SELECT count(*) FROM source_image_candidate WHERE markdown_artifact_id = %s",
        (markdown_artifact_id,),
    ).fetchone()[0]
    if not count:
        return None
    prompt_ref, prompt_sha, _template = prompt_stamp()
    call_id = f"{markdown_artifact_id}:source-images:{prompt_sha[:16]}"
    conn.execute(
        "INSERT INTO source_image_analysis_call"
        " (id, markdown_artifact_id, prompt_ref, prompt_sha, requested_model, status)"
        " VALUES (%s, %s, %s, %s, %s, 'waiting')"
        " ON CONFLICT (markdown_artifact_id, prompt_ref) DO NOTHING",
        (call_id, markdown_artifact_id, prompt_ref, prompt_sha, article_image_model()),
    )
    row = conn.execute(
        "SELECT id FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s AND prompt_ref = %s",
        (markdown_artifact_id, prompt_ref),
    ).fetchone()
    return get_source_image_analysis_call(conn, row[0]) if row else None


def queue_source_image_analysis_if_ready(
    conn: psycopg.Connection, markdown_artifact_id: str
) -> dict[str, Any] | None:
    """Queue exactly one source call after all technical image work is terminal."""
    call = _ensure_source_image_analysis_call(conn, markdown_artifact_id)
    if call is None:
        conn.rollback()
        return None
    if call["status"] in {"running", "succeeded", "failed", "skipped"}:
        conn.commit()
        return call
    counts = conn.execute(
        "SELECT count(*) FILTER (WHERE status IN ('queued', 'running')),"
        " count(*) FILTER (WHERE status = 'downloaded')"
        " FROM source_image_candidate WHERE markdown_artifact_id = %s",
        (markdown_artifact_id,),
    ).fetchone()
    active, downloaded = counts or (0, 0)
    if active:
        conn.commit()
        return call
    if downloaded:
        conn.execute(
            "UPDATE source_image_analysis_call SET status = 'queued',"
            " available_at = now(), updated_at = now()"
            " WHERE id = %s AND status = 'waiting'",
            (call["id"],),
        )
        conn.commit()
        return get_source_image_analysis_call(conn, call["id"])

    conn.execute(
        "UPDATE source_image_analysis_call SET status = 'skipped',"
        " diagnostics = %s, finished_at = now(), updated_at = now()"
        " WHERE id = %s AND status IN ('waiting', 'queued')",
        (Jsonb({"category": "no_model_compatible_images"}), call["id"]),
    )
    conn.commit()
    _finalize_article_images_safely(conn, markdown_artifact_id)
    return get_source_image_analysis_call(conn, call["id"])


def claim_next_source_image_analysis(
    conn: psycopg.Connection, *, call_id: str | None = None
) -> dict[str, Any] | None:
    token = uuid.uuid4().hex
    row = conn.execute(
        "WITH candidate AS ("
        " SELECT id FROM source_image_analysis_call"
        " WHERE (%s::text IS NULL OR id = %s) AND available_at <= now()"
        "   AND (status = 'queued'"
        "        OR (status = 'running' AND lease_expires_at < now()))"
        " ORDER BY available_at, created_at, id"
        " FOR UPDATE SKIP LOCKED LIMIT 1"
        ") UPDATE source_image_analysis_call c SET status = 'running',"
        " attempt_count = c.attempt_count + 1, claimed_at = now(), claim_token = %s,"
        " lease_expires_at = now() + (%s * interval '1 minute'),"
        " diagnostics = '{}'::jsonb, updated_at = now()"
        " FROM candidate WHERE c.id = candidate.id"
        " RETURNING c.id, c.markdown_artifact_id, c.prompt_ref, c.prompt_sha,"
        " c.requested_model, c.input_manifest_hash, c.status, c.attempt_count,"
        " c.claimed_at, c.claim_token, c.response_model, c.provider, c.usage,"
        " c.duration_ms, c.failure_code, c.diagnostics, c.finished_at, c.created_at",
        (call_id, call_id, token, acquisition_lease_minutes()),
    ).fetchone()
    conn.commit()
    return dict(zip(SOURCE_IMAGE_CALL_COLUMNS, row)) if row else None


def _source_analysis_candidates(
    conn: psycopg.Connection, markdown_artifact_id: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT c.id, c.alt_text, c.original_url, c.placement, c.status,"
        " c.asset_id, a.mime_type, a.sha256, a.storage_key"
        " FROM source_image_candidate c"
        " JOIN source_asset a ON a.id = c.asset_id"
        " WHERE c.markdown_artifact_id = %s AND c.status = 'downloaded'"
        " ORDER BY c.ordinal, c.id",
        (markdown_artifact_id,),
    ).fetchall()
    keys = (
        "id", "alt_text", "original_url", "placement", "status", "asset_id",
        "mime_type", "sha256", "storage_key",
    )
    return [dict(zip(keys, row)) for row in rows]


def default_source_image_analyzer(
    markdown: str, images: list[SourceImageInput]
) -> SourceImageBatchResult:
    client = ModelClient(
        article_image_model(),
        temperature=0,
        # A high ceiling does not spend tokens by itself. It prevents a large
        # source's required result array or OCR from being truncated.
        max_tokens=65_536,
        extra={"provider": openrouter_multimodal_provider_routing()},
    )
    return analyze_source_images(markdown, images, client=client)


def process_next_source_image_analysis(
    conn: psycopg.Connection,
    *,
    call_id: str | None = None,
    asset_store: AssetStore | None = None,
    analyzer: Callable[[str, list[SourceImageInput]], SourceImageBatchResult]
    | None = None,
    lease_connection_factory: ConnectionFactory | None = None,
) -> dict[str, Any] | None:
    """Run one grouped multimodal call and reconcile every image fail-open."""
    heartbeat_connection = (
        lease_connection_factory or separate_connection_factory(conn)
    )
    call = claim_next_source_image_analysis(conn, call_id=call_id)
    if call is None:
        return None
    markdown = ""
    candidates: list[dict[str, Any]] = []
    prepared: list[SourceImageInput] = []
    input_diagnostics: dict[str, dict[str, Any]] = {}
    batch: SourceImageBatchResult | None = None
    try:
        with JobLease(
            heartbeat_connection,
            table="source_image_analysis_call",
            row_id=call["id"],
            claim_token=call["claim_token"],
        ):
            store = asset_store or asset_store_from_env()
            artifact = conn.execute(
                "SELECT body FROM artifact WHERE id = %s",
                (call["markdown_artifact_id"],),
            ).fetchone()
            markdown = (
                artifact[0]
                if artifact and isinstance(artifact[0], str)
                else ""
            )
            candidates = _source_analysis_candidates(
                conn, call["markdown_artifact_id"]
            )
            conn.commit()

            for candidate in candidates:
                try:
                    body = store.get(candidate["storage_key"])
                    model_body, model_mime, diagnostics = _prepare_model_image(
                        body, candidate["mime_type"]
                    )
                    if model_body is None or model_mime is None:
                        raise ImageJobError(
                            "image_analysis_unsupported_type",
                            "unsupported_model_image_type",
                            {"mime_type": candidate["mime_type"]},
                        )
                except ImageJobError as exc:
                    _mark_downloaded_candidate_unresolved(
                        conn,
                        candidate["id"],
                        failure_code=exc.code,
                        diagnostics={
                            "category": exc.category,
                            **exc.diagnostics,
                        },
                    )
                    continue
                except Exception as exc:
                    _mark_downloaded_candidate_unresolved(
                        conn,
                        candidate["id"],
                        failure_code="image_asset_unavailable",
                        diagnostics={
                            "category": "asset_storage_read_failed",
                            "exception": type(exc).__name__,
                        },
                    )
                    continue
                model_hash = hashlib.sha256(model_body).hexdigest()
                input_diagnostics[candidate["id"]] = {
                    **diagnostics,
                    "model_input_sha256": model_hash,
                }
                prepared.append(
                    SourceImageInput(
                        image_id=candidate["id"],
                        alt_text=str(candidate.get("alt_text") or ""),
                        source_url=str(candidate["original_url"]),
                        model_image_url=(
                            f"data:{model_mime};base64,"
                            f"{base64.b64encode(model_body).decode('ascii')}"
                        ),
                        asset_sha256=str(candidate["sha256"]),
                        model_input_sha256=model_hash,
                    )
                )
            conn.commit()

            if prepared:
                batch = (analyzer or default_source_image_analyzer)(
                    markdown, prepared
                )
                if not isinstance(batch, SourceImageBatchResult):
                    raise ModelError(
                        "source image analyzer returned an invalid batch"
                    )
    except Exception as exc:
        diagnostics = _source_analysis_failure_diagnostics(exc)
        if _source_image_call_is_owned(conn, call):
            for image in prepared:
                _mark_downloaded_candidate_unresolved(
                    conn,
                    image.image_id,
                    failure_code="image_analysis_failed",
                    diagnostics={
                        **diagnostics,
                        "analysis_call_id": call["id"],
                        "asset_sha256": image.asset_sha256,
                    },
                    commit=False,
                )
            _finish_source_image_call(
                conn,
                call,
                status="failed",
                failure_code="source_image_analysis_failed",
                diagnostics=diagnostics,
                commit=False,
            )
            conn.commit()
            _finalize_article_images_safely(conn, call["markdown_artifact_id"])
        else:
            conn.rollback()
        result = get_source_image_analysis_call(conn, call["id"])
        assert result is not None
        return result

    if not prepared:
        _finish_source_image_call(
            conn,
            call,
            status="skipped",
            failure_code=None,
            diagnostics={"category": "no_model_compatible_images"},
        )
        _finalize_article_images_safely(conn, call["markdown_artifact_id"])
        result = get_source_image_analysis_call(conn, call["id"])
        assert result is not None
        return result

    assert batch is not None

    if not _source_image_call_is_owned(conn, call):
        conn.rollback()
        result = get_source_image_analysis_call(conn, call["id"])
        assert result is not None
        return result
    candidates_by_id = {item["id"]: item for item in candidates}
    analysis_ids: dict[str, str] = {}
    for image in prepared:
        analysis = batch.analyses.get(image.image_id)
        if analysis is None:
            _mark_downloaded_candidate_unresolved(
                conn,
                image.image_id,
                failure_code="image_analysis_unavailable",
                diagnostics={
                    "category": "image_analysis_unavailable",
                    "reason": batch.unresolved.get(image.image_id, "missing_result"),
                    "analysis_call_id": call["id"],
                    **input_diagnostics[image.image_id],
                },
                commit=False,
            )
            continue
        candidate = candidates_by_id[image.image_id]
        analysis_id = _insert_source_image_analysis(
            conn,
            call,
            candidate,
            analysis,
            batch,
            input_diagnostics[image.image_id],
        )
        status = "useful" if analysis.retain else "not_important"
        conn.execute(
            "UPDATE source_image_candidate SET status = %s, failure_code = NULL,"
            " analysis_id = %s, diagnostics = %s, finished_at = now(), updated_at = now()"
            " WHERE id = %s AND status = 'downloaded'",
            (
                status,
                analysis_id,
                Jsonb(
                    {
                        "category": "success",
                        "analysis_call_id": call["id"],
                        "reason_code": analysis.reason_code,
                        **input_diagnostics[image.image_id],
                    }
                ),
                image.image_id,
            ),
        )
        analysis_ids[image.image_id] = analysis_id

    _finish_source_image_call(
        conn,
        call,
        status="succeeded",
        failure_code=None,
        diagnostics={
            "category": "success",
            "image_count": len(prepared),
            "resolved_count": len(batch.analyses),
            "unresolved": dict(batch.unresolved),
            "analysis_ids": analysis_ids,
        },
        batch=batch,
        commit=False,
    )
    conn.commit()
    _finalize_article_images_safely(conn, call["markdown_artifact_id"])
    result = get_source_image_analysis_call(conn, call["id"])
    assert result is not None
    return result


def _source_image_call_is_owned(
    conn: psycopg.Connection, call: Mapping[str, Any]
) -> bool:
    return conn.execute(
        "SELECT 1 FROM source_image_analysis_call"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (call["id"], call["claim_token"]),
    ).fetchone() is not None


def _mark_downloaded_candidate_unresolved(
    conn: psycopg.Connection,
    candidate_id: str,
    *,
    failure_code: str,
    diagnostics: Mapping[str, Any],
    commit: bool = True,
) -> None:
    conn.execute(
        "UPDATE source_image_candidate SET status = 'failed', failure_code = %s,"
        " diagnostics = %s, finished_at = now(), updated_at = now()"
        " WHERE id = %s AND status = 'downloaded'",
        (failure_code, Jsonb(dict(diagnostics)), candidate_id),
    )
    if commit:
        conn.commit()


def _insert_source_image_analysis(
    conn: psycopg.Connection,
    call: Mapping[str, Any],
    candidate: Mapping[str, Any],
    analysis: SourceImageAnalysis,
    batch: SourceImageBatchResult,
    input_diagnostics: Mapping[str, Any],
) -> str:
    identity = hashlib.sha256(
        f"{call['id']}:{candidate['asset_id']}".encode()
    ).hexdigest()[:32]
    analysis_id = f"analysis-source-image-{identity}"
    conn.execute(
        "INSERT INTO source_asset_analysis"
        " (id, source_asset_id, purpose, status, prompt_version, requested_model,"
        " response_model, provider, result, usage, duration_ms, diagnostics,"
        " analysis_call_id)"
        " VALUES (%s, %s, 'source_image_analysis', 'succeeded', %s, %s, %s, %s,"
        " %s, '{}', NULL, %s, %s) ON CONFLICT (id) DO NOTHING",
        (
            analysis_id,
            candidate["asset_id"],
            batch.prompt_ref,
            batch.requested_model,
            batch.response_model,
            batch.provider,
            Jsonb(asdict(analysis)),
            Jsonb(
                {
                    "analysis_call_id": call["id"],
                    "input_manifest_hash": batch.input_manifest_hash,
                    "asset_sha256": candidate["sha256"],
                    **dict(input_diagnostics),
                }
            ),
            call["id"],
        ),
    )
    return analysis_id


def _finish_source_image_call(
    conn: psycopg.Connection,
    call: Mapping[str, Any],
    *,
    status: str,
    failure_code: str | None,
    diagnostics: Mapping[str, Any],
    batch: SourceImageBatchResult | None = None,
    commit: bool = True,
) -> None:
    updated = conn.execute(
        "UPDATE source_image_analysis_call SET status = %s, failure_code = %s,"
        " input_manifest_hash = COALESCE(%s, input_manifest_hash),"
        " response_model = COALESCE(%s, response_model),"
        " provider = COALESCE(%s, provider), usage = %s, duration_ms = %s,"
        " diagnostics = %s, finished_at = now(), lease_expires_at = NULL,"
        " claim_token = NULL, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (
            status,
            failure_code,
            batch.input_manifest_hash if batch else None,
            batch.response_model if batch else None,
            batch.provider if batch else None,
            Jsonb(dict(batch.usage) if batch else {}),
            batch.duration_ms if batch else None,
            Jsonb(dict(diagnostics)),
            call["id"],
            call["claim_token"],
        ),
    )
    if updated.rowcount != 1:
        conn.rollback()
    elif commit:
        conn.commit()


def _source_analysis_failure_diagnostics(exc: Exception) -> dict[str, Any]:
    message = str(exc)
    diagnostics: dict[str, Any] = {
        "category": "image_analysis_failed",
        "exception": type(exc).__name__,
    }
    if message:
        safe = re.sub(
            r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[image redacted]", message
        )
        safe = re.sub(r"sk-[A-Za-z0-9_-]+", "[key redacted]", safe)
        diagnostics["detail"] = safe[:300]
    return diagnostics


def _finalize_article_images_safely(
    conn: psycopg.Connection, markdown_artifact_id: str
) -> str | None:
    try:
        return finalize_article_image_association(conn, markdown_artifact_id)
    except Exception as exc:
        conn.rollback()
        conn.execute(
            "UPDATE source_image_candidate SET diagnostics = diagnostics || %s,"
            " updated_at = now() WHERE markdown_artifact_id = %s",
            (
                Jsonb(
                    {
                        "association_attention": {
                            "code": "article_image_association_failed",
                            "exception": type(exc).__name__,
                        }
                    }
                ),
                markdown_artifact_id,
            ),
        )
        conn.commit()
        return None


def default_article_image_analyzer(
    reference: ArticleImageReference,
    body: bytes,
    mime_type: str,
    context: str,
    asset_sha256: str,
) -> ArticleImageModelResult:
    encoded = base64.b64encode(body).decode("ascii")
    client = ModelClient(
        article_image_model(),
        temperature=0,
        max_tokens=1800,
        extra={"provider": openrouter_multimodal_provider_routing()},
    )
    return analyze_article_image(
        reference,
        client=client,
        image_url=f"data:{mime_type};base64,{encoded}",
        context=context,
        asset_sha256=asset_sha256,
    )


def _prepare_model_image(
    body: bytes, mime_type: str
) -> tuple[bytes | None, str | None, dict[str, Any]]:
    """Normalize a bounded model representation; never replace source bytes."""
    if mime_type not in MODEL_IMAGE_MIMES | CONVERTIBLE_MODEL_IMAGE_MIMES:
        return None, None, {}
    try:
        with Image.open(io.BytesIO(body)) as source:
            source.seek(0)
            source.load()
            image = ImageOps.exif_transpose(source)
            image.thumbnail(
                (MAX_MODEL_IMAGE_EDGE, MAX_MODEL_IMAGE_EDGE),
                Image.Resampling.LANCZOS,
            )
            has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
            if has_alpha:
                normalized = image.convert("RGBA")
                output = io.BytesIO()
                normalized.save(output, format="PNG", optimize=True)
                converted = output.getvalue()
                model_mime = "image/png"
            else:
                normalized = image.convert("RGB")
                converted = b""
                model_mime = "image/jpeg"
                for quality in (92, 82, 70, 58):
                    output = io.BytesIO()
                    normalized.save(
                        output,
                        format="JPEG",
                        quality=quality,
                        optimize=True,
                        progressive=True,
                    )
                    converted = output.getvalue()
                    if len(converted) <= MAX_MODEL_IMAGE_BYTES:
                        break
            if len(converted) > MAX_MODEL_IMAGE_BYTES and has_alpha:
                background = Image.new("RGB", normalized.size, "white")
                background.paste(normalized, mask=normalized.getchannel("A"))
                for quality in (88, 76, 64, 52):
                    output = io.BytesIO()
                    background.save(
                        output,
                        format="JPEG",
                        quality=quality,
                        optimize=True,
                        progressive=True,
                    )
                    converted = output.getvalue()
                    model_mime = "image/jpeg"
                    if len(converted) <= MAX_MODEL_IMAGE_BYTES:
                        break
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageJobError(
            "image_analysis_conversion_failed",
            "image_analysis_conversion_failed",
            {"mime_type": mime_type, "exception": type(exc).__name__},
        ) from exc
    if not converted or len(converted) > MAX_MODEL_IMAGE_BYTES:
        raise ImageJobError(
            "image_analysis_conversion_failed",
            "image_analysis_conversion_failed",
            {"mime_type": mime_type, "reason": "converted_image_size_invalid"},
        )
    return converted, model_mime, {
        "source_mime_type": mime_type,
        "model_input_mime_type": model_mime,
        "model_input_converted": True,
        "model_input_sha256": hashlib.sha256(converted).hexdigest(),
    }


def _analysis_failure_diagnostics(
    exc: Exception,
    *,
    reference_id: str,
    asset_sha256: str,
) -> dict[str, Any]:
    """Classify provider failures without persisting prompts, media, or keys."""
    category = "image_analysis_failed"
    provider_status: int | None = None
    message = str(exc)
    if isinstance(exc, ModelError):
        status_match = re.search(r"\bHTTP (\d{3})\b", message)
        provider_status = int(status_match.group(1)) if status_match else None
        lowered = message.lower()
        if "no endpoints found that can handle the requested parameters" in lowered:
            category = "model_routing_unavailable"
        elif provider_status in {401, 403}:
            category = "model_authentication"
        elif provider_status == 402:
            category = "model_credits"
        elif provider_status == 429:
            category = "model_rate_limited"
        elif provider_status is not None and provider_status >= 500:
            category = "model_unavailable"

    diagnostics: dict[str, Any] = {
        "category": category,
        "exception": type(exc).__name__,
        "reference_id": reference_id,
        "asset_sha256": asset_sha256,
    }
    if provider_status is not None:
        diagnostics["provider_http_status"] = provider_status
    if message:
        safe_detail = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[image redacted]", message)
        safe_detail = re.sub(r"sk-[A-Za-z0-9_-]+", "[key redacted]", safe_detail)
        diagnostics["detail"] = safe_detail[:300]
    return diagnostics


def download_public_image(url: str) -> DownloadedImage:
    """Download one public raster through validated redirects and hard limits."""
    current = url
    with httpx.Client(follow_redirects=False, timeout=30.0) as client:
        for redirect_count in range(MAX_REDIRECTS + 1):
            _validate_public_url(current)
            try:
                with client.stream(
                    "GET",
                    current,
                    headers={"User-Agent": IMAGE_USER_AGENT, "Accept": "image/*"},
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise ImageJobError(
                                "image_redirect_invalid", "invalid_redirect"
                            )
                        if redirect_count >= MAX_REDIRECTS:
                            raise ImageJobError(
                                "image_redirect_limit", "redirect_limit"
                            )
                        current = urljoin(current, location)
                        continue
                    if response.status_code == 404:
                        raise ImageJobError(
                            "image_not_found", "not_found", {"http_status": 404}
                        )
                    if response.status_code in {401, 403}:
                        raise ImageJobError(
                            "image_access_denied",
                            "access_denied",
                            {"http_status": response.status_code},
                        )
                    if response.status_code == 429:
                        raise ImageJobError(
                            "image_rate_limited",
                            "rate_limited",
                            {"http_status": 429},
                        )
                    if response.status_code >= 400:
                        raise ImageJobError(
                            "image_download_failed",
                            "http_error",
                            {"http_status": response.status_code},
                        )
                    declared = response.headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > MAX_IMAGE_BYTES:
                        raise ImageJobError("image_too_large", "payload_too_large")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_IMAGE_BYTES:
                            raise ImageJobError("image_too_large", "payload_too_large")
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    return _validated_download(
                        body,
                        response.headers.get("content-type"),
                        current,
                    )
            except ImageJobError:
                raise
            except httpx.TimeoutException as exc:
                raise ImageJobError("image_download_timeout", "request_timeout") from exc
            except httpx.TransportError as exc:
                raise ImageJobError(
                    "image_download_failed",
                    "transport_error",
                    {"exception": type(exc).__name__},
                ) from exc
    raise ImageJobError("image_redirect_limit", "redirect_limit")


def _validated_download(
    body: bytes, content_type: str | None, final_url: str
) -> DownloadedImage:
    if not body:
        raise ImageJobError("image_empty", "empty_content")
    mime_type = _sniff_image_mime(body)
    declared = str(content_type or "").split(";", 1)[0].strip().lower()
    if declared == "image/jpg":
        declared = "image/jpeg"
    if mime_type is None or (declared.startswith("image/") and declared != mime_type):
        raise ImageJobError("image_type_invalid", "invalid_image_type")
    if mime_type not in PRESERVABLE_IMAGE_MIMES:
        raise ImageJobError("image_type_invalid", "invalid_image_type")
    filename = _filename_for_url(final_url, mime_type)
    if mime_type in {"image/avif", "image/svg+xml"}:
        return DownloadedImage(
            body=body,
            mime_type=mime_type,
            filename=filename,
            final_url=final_url,
            width=0,
            height=0,
            sha256=hashlib.sha256(body).hexdigest(),
        )
    if mime_type == "image/gif":
        width, height = _validated_gif_dimensions(body)
        sha256 = hashlib.sha256(body).hexdigest()
        validated_filename = filename
    else:
        try:
            validated = validate_manual_assets(
                [ManualAsset(filename, mime_type, body, "image")],
                max_total_bytes=MAX_IMAGE_BYTES,
            )[0]
        except ValueError as exc:
            raise ImageJobError(
                "image_validation_failed",
                "invalid_image",
                {"reason": str(exc)[:300]},
            ) from exc
        width = int(validated.metadata["width"])
        height = int(validated.metadata["height"])
        assert validated.sha256 is not None
        sha256 = validated.sha256
        validated_filename = validated.filename
    return DownloadedImage(
        body=body,
        mime_type=mime_type,
        filename=validated_filename,
        final_url=final_url,
        width=width,
        height=height,
        sha256=sha256,
    )


def _validated_gif_dimensions(body: bytes) -> tuple[int, int]:
    """Validate one bounded article GIF without admitting GIF manual uploads."""
    if len(body) < 13 or body[:6] not in {b"GIF87a", b"GIF89a"}:
        raise ImageJobError("image_validation_failed", "invalid_image")
    width = int.from_bytes(body[6:8], "little")
    height = int.from_bytes(body[8:10], "little")
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise ImageJobError(
            "image_validation_failed",
            "invalid_image",
            {"reason": "image dimensions exceed the pixel limit"},
        )
    try:
        with Image.open(io.BytesIO(body)) as image:
            if image.format != "GIF" or image.size != (width, height):
                raise ValueError("GIF header does not match decoded image")
            image.seek(0)
            image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageJobError(
            "image_validation_failed",
            "invalid_image",
            {"reason": "GIF first frame is not decodable"},
        ) from exc
    return width, height


def _sniff_image_mime(body: bytes) -> str | None:
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp"
    if body.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(body) >= 16 and body[4:8] == b"ftyp" and body[8:12] in {b"avif", b"avis"}:
        return "image/avif"
    head = body[:4096].lstrip(b"\xef\xbb\xbf\x00\t\r\n ").lower()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head):
        return "image/svg+xml"
    return None


def _filename_for_url(url: str, mime_type: str) -> str:
    raw = unquote(Path(urlsplit(url).path).name).strip()
    raw = re.sub(r"[\x00-\x1f\x7f]", "", raw).replace("/", "-")[:220]
    suffix = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/avif": ".avif",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
    }[mime_type]
    if not raw or raw in {".", ".."}:
        return f"article-image{suffix}"
    return raw if Path(raw).suffix else raw + suffix


def _candidate_url(value: str, base_url: str | None) -> str:
    raw = str(value or "").strip()
    if _valid_remote_url_shape(raw):
        return raw
    if not raw or not base_url or not _valid_remote_url_shape(base_url):
        return raw
    try:
        resolved = urljoin(base_url, raw)
    except ValueError:
        return raw
    return resolved if _valid_remote_url_shape(resolved) else raw


def _valid_remote_url_shape(url: str) -> bool:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    hostname = parsed.hostname.casefold().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return _is_public_address(address)


def _validate_public_url(url: str) -> None:
    if not _valid_remote_url_shape(url):
        raise ImageJobError("invalid_image_url", "invalid_image_url")
    hostname = urlsplit(url).hostname
    assert hostname is not None
    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        }
    except (socket.gaierror, ValueError) as exc:
        raise ImageJobError("image_dns_failure", "dns_failure") from exc
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise ImageJobError("invalid_image_url", "private_network_target")


def _is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _existing_asset(conn: psycopg.Connection, job: Mapping[str, Any]) -> dict | None:
    row = conn.execute(
        "SELECT id, mime_type, sha256, byte_size, storage_key, metadata"
        " FROM source_asset WHERE acquisition_job_id = %s AND ordinal = %s"
        " AND kind = 'article_image'",
        (job["acquisition_job_id"], job["ordinal"]),
    ).fetchone()
    if row is None:
        return None
    return dict(zip(("id", "mime_type", "sha256", "byte_size", "storage_key", "metadata"), row))


def _claim_is_owned(conn: psycopg.Connection, job: Mapping[str, Any]) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM source_image_candidate"
            " WHERE id = %s AND status = 'running' AND claim_token = %s",
            (job["id"], job["claim_token"]),
        ).fetchone()
        is not None
    )


def _current_candidate(
    conn: psycopg.Connection, candidate_id: str
) -> dict[str, Any]:
    current = get_article_image_candidate(conn, candidate_id)
    assert current is not None
    return current


def _validate_analysis_binding(
    reference: ArticleImageReference,
    asset: Mapping[str, Any],
    result: ArticleImageModelResult,
) -> None:
    if result.reference_id != reference.reference_id:
        raise ValueError("article image analysis references another Markdown image")
    if result.source_url != reference.source_url:
        raise ValueError("article image analysis references another source URL")
    if result.asset_sha256 != asset["sha256"]:
        raise ValueError("article image analysis references another binary asset")


def _insert_article_asset(
    conn: psycopg.Connection,
    job: Mapping[str, Any],
    image: DownloadedImage,
    storage_key: str,
) -> dict | None:
    asset_id = f"{job['id']}:asset"
    metadata = {
        "candidate_id": job["id"],
        "final_url": image.final_url,
        "width": image.width,
        "height": image.height,
    }
    row = conn.execute(
        "INSERT INTO source_asset"
        " (id, acquisition_job_id, source_id, ordinal, kind, filename, mime_type,"
        "  sha256, byte_size, storage_key, metadata, original_url)"
        " SELECT %s, %s, %s, %s, 'article_image', %s, %s, %s, %s, %s, %s, %s"
        " FROM source_image_candidate c"
        " WHERE c.id = %s AND c.status = 'running' AND c.claim_token = %s"
        " ON CONFLICT (id) DO NOTHING"
        " RETURNING id, mime_type, sha256, byte_size, storage_key, metadata",
        (
            asset_id,
            job["acquisition_job_id"],
            job["source_id"],
            job["ordinal"],
            image.filename,
            image.mime_type,
            image.sha256,
            len(image.body),
            storage_key,
            Jsonb(metadata),
            job["original_url"],
            job["id"],
            job["claim_token"],
        ),
    ).fetchone()
    if row:
        return dict(zip(("id", "mime_type", "sha256", "byte_size", "storage_key", "metadata"), row))
    return _existing_asset(conn, job)


def _cached_analysis(
    conn: psycopg.Connection, asset_id: str, reference_id: str
) -> dict | None:
    model = article_image_model()
    row = conn.execute(
        "SELECT id, requested_model, response_model, provider, result, prompt_version"
        " FROM source_asset_analysis WHERE source_asset_id = %s"
        " AND purpose = 'article_image_relevance' AND status = 'succeeded'"
        " AND prompt_version = %s AND requested_model = %s"
        " AND diagnostics->>'reference_id' = %s"
        " ORDER BY created_at DESC, id DESC LIMIT 1",
        (asset_id, ARTICLE_IMAGE_PROMPT_VERSION, model, reference_id),
    ).fetchone()
    if row is None:
        return None
    from universe.acquisition.article_images import ArticleImageAnalysis

    result = row[4] or {}
    try:
        analysis = ArticleImageAnalysis(
            pedagogical_importance=result["pedagogical_importance"],
            description=result["description"],
            visible_text=result["visible_text"],
            reason=result["reason"],
            confidence=result["confidence"],
        )
    except (KeyError, TypeError):
        return None
    return {
        "id": row[0],
        "requested_model": row[1],
        "response_model": row[2],
        "provider": row[3],
        "analysis": analysis,
        "prompt_version": row[5],
    }


def _insert_analysis_success(
    conn: psycopg.Connection,
    job: Mapping[str, Any],
    asset: Mapping[str, Any],
    result: ArticleImageModelResult,
) -> str | None:
    analysis_id = f"analysis-{uuid.uuid4().hex}"
    row = conn.execute(
        "INSERT INTO source_asset_analysis"
        " (id, source_asset_id, purpose, status, prompt_version, requested_model,"
        "  response_model, provider, result, usage, duration_ms, diagnostics)"
        " SELECT %s, %s, 'article_image_relevance', 'succeeded', %s, %s, %s, %s,"
        "        %s, %s, %s, %s FROM source_image_candidate c"
        " WHERE c.id = %s AND c.status = 'running' AND c.claim_token = %s"
        " RETURNING id",
        (
            analysis_id,
            asset["id"],
            result.prompt_version,
            result.requested_model,
            result.response_model,
            result.provider,
            Jsonb(asdict(result.analysis)),
            Jsonb(dict(result.usage)),
            result.duration_ms,
            Jsonb(
                {
                    "reference_id": result.reference_id,
                    "source_url": result.source_url,
                    "model_image_transport": _model_image_transport(
                        result.model_image_url
                    ),
                    "input_sha256": result.input_sha256,
                    "asset_sha256": result.asset_sha256,
                }
            ),
            job["id"],
            job["claim_token"],
        ),
    ).fetchone()
    return row[0] if row else None


def _insert_analysis_failure(
    conn: psycopg.Connection,
    job: Mapping[str, Any],
    asset: Mapping[str, Any],
    *,
    failure_code: str,
    diagnostics: Mapping[str, Any],
) -> str | None:
    analysis_id = f"analysis-{uuid.uuid4().hex}"
    row = conn.execute(
        "INSERT INTO source_asset_analysis"
        " (id, source_asset_id, purpose, status, prompt_version, requested_model,"
        "  failure_code, diagnostics)"
        " SELECT %s, %s, 'article_image_relevance', 'failed', %s, %s, %s, %s"
        " FROM source_image_candidate c"
        " WHERE c.id = %s AND c.status = 'running' AND c.claim_token = %s"
        " RETURNING id",
        (
            analysis_id,
            asset["id"],
            ARTICLE_IMAGE_PROMPT_VERSION,
            article_image_model(),
            failure_code,
            Jsonb(dict(diagnostics)),
            job["id"],
            job["claim_token"],
        ),
    ).fetchone()
    return row[0] if row else None


def _reference_and_context(
    conn: psycopg.Connection, job: Mapping[str, Any]
) -> tuple[ArticleImageReference, str]:
    row = conn.execute(
        "SELECT body FROM artifact WHERE id = %s",
        (job["markdown_artifact_id"],),
    ).fetchone()
    markdown = row[0] if row and isinstance(row[0], str) else ""
    reference = _reference_for_job(job, markdown)
    occurrences = (job.get("placement") or {}).get("occurrences") or []
    starts = [item.get("start_char") for item in occurrences if isinstance(item, dict)]
    starts = [value for value in starts if isinstance(value, int) and value >= 0]
    if not starts:
        return reference, markdown[:6000]
    position = starts[0]
    return reference, markdown[max(0, position - 3000) : position + 3000]


def _reference_for_job(
    job: Mapping[str, Any], markdown: str
) -> ArticleImageReference:
    occurrences = (job.get("placement") or {}).get("occurrences") or []
    first = occurrences[0] if occurrences and isinstance(occurrences[0], dict) else {}
    occurrence_ordinal = first.get("ordinal")
    if isinstance(occurrence_ordinal, int):
        references = extract_markdown_images(markdown)
        for reference in references:
            if reference.ordinal == occurrence_ordinal:
                expected_id = first.get("reference_id")
                expected_hash = first.get("reference_sha256")
                if expected_id and expected_id != reference.reference_id:
                    raise ImageJobError(
                        "image_reference_changed", "markdown_reference_mismatch"
                    )
                if expected_hash and expected_hash != reference.raw_sha256:
                    raise ImageJobError(
                        "image_reference_changed", "markdown_reference_mismatch"
                    )
                return reference

    original_markdown = f"![{job.get('alt_text') or ''}]({job['original_url']})"
    document_sha256 = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return ArticleImageReference(
        ordinal=int(job["ordinal"]),
        alt_text=str(job.get("alt_text") or ""),
        source_url=str(job["original_url"]),
        original_markdown=original_markdown,
        start_char=0,
        end_char=len(original_markdown),
        document_sha256=document_sha256,
        link_url=None,
    )


def _finish_candidate(
    conn: psycopg.Connection,
    job: Mapping[str, Any],
    *,
    status: str,
    failure_code: str | None,
    diagnostics: Mapping[str, Any],
    asset_id: str | None = None,
    analysis_id: str | None = None,
) -> dict[str, Any]:
    updated = conn.execute(
        "UPDATE source_image_candidate SET status = %s, failure_code = %s,"
        " diagnostics = %s, asset_id = COALESCE(%s, asset_id),"
        " analysis_id = COALESCE(%s, analysis_id), finished_at = now(),"
        " lease_expires_at = NULL, claim_token = NULL, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (
            status,
            failure_code,
            Jsonb(dict(diagnostics)),
            asset_id,
            analysis_id,
            job["id"],
            job["claim_token"],
        ),
    )
    if updated.rowcount != 1:
        conn.rollback()
    else:
        conn.commit()
    return _current_candidate(conn, str(job["id"]))


def finalize_article_image_association(
    conn: psycopg.Connection, markdown_artifact_id: str
) -> str | None:
    """Create one immutable enriched Markdown fact after every image is terminal.

    The initial textual Markdown remains available throughout.  This optional
    artifact is append-only and can be absent without changing the acquisition
    job's succeeded state.
    """
    counts = conn.execute(
        "SELECT count(*), count(*) FILTER"
        " (WHERE status IN ('queued', 'running', 'downloaded'))"
        " FROM source_image_candidate WHERE markdown_artifact_id = %s",
        (markdown_artifact_id,),
    ).fetchone()
    if counts is None or counts[0] == 0 or counts[1] != 0:
        conn.rollback()
        return None
    active_call = conn.execute(
        "SELECT 1 FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s"
        " AND status IN ('waiting', 'queued', 'running') LIMIT 1",
        (markdown_artifact_id,),
    ).fetchone()
    if active_call:
        conn.rollback()
        return None
    artifact_row = conn.execute(
        "SELECT snapshot_id, body, metadata FROM artifact WHERE id = %s",
        (markdown_artifact_id,),
    ).fetchone()
    if artifact_row is None:
        raise ValueError("article image candidate references missing Markdown")
    snapshot_id, raw_markdown, source_metadata = artifact_row
    source_metadata = dict(source_metadata or {})
    is_video = source_metadata.get("source_media_type") == "video"
    candidates = _association_candidates(conn, markdown_artifact_id)
    analyses: dict[int, ArticleImageAnalysis] = {}
    local_assets: dict[int, str] = {}
    additional: list[dict[str, Any]] = []
    for candidate in candidates:
        occurrences = (candidate.get("placement") or {}).get("occurrences") or []
        analysis = _analysis_from_json(candidate.get("analysis"))
        if (
            is_video
            and candidate["status"] == "failed"
            and candidate.get("asset_id")
        ):
            # A stored video frame is primary source evidence. If interpretation
            # fails, preserve the frame visibly instead of classifying the
            # unknown pixels as irrelevant article chrome.
            analysis = ArticleImageAnalysis(
                pedagogical_importance="unavailable",
                description="",
                visible_text="",
                reason=str(candidate.get("failure_code") or "analysis unavailable"),
                confidence="low",
            )
        elif candidate["status"] in {"failed", "filtered"}:
            # An incidental article image that could not be resolved remains a
            # durable candidate/asset outcome, but is not source evidence.  Its
            # Markdown reference must disappear without shielding neighboring
            # text from passage cleanup.
            analysis = ArticleImageAnalysis(
                pedagogical_importance="not_important",
                description="",
                visible_text="",
                reason=str(candidate.get("failure_code") or "analysis unavailable"),
                confidence="high",
            )
        if candidate["status"] in {"useful", "not_important"} and analysis:
            for occurrence in occurrences:
                if isinstance(occurrence, dict) and isinstance(
                    occurrence.get("ordinal"), int
                ):
                    analyses[occurrence["ordinal"]] = analysis
        elif candidate["status"] in {"failed", "filtered"} and analysis:
            for occurrence in occurrences:
                if isinstance(occurrence, dict) and isinstance(
                    occurrence.get("ordinal"), int
                ):
                    analyses[occurrence["ordinal"]] = analysis
        if candidate.get("asset_id"):
            for occurrence in occurrences:
                if isinstance(occurrence, dict) and isinstance(
                    occurrence.get("ordinal"), int
                ):
                    local_assets[occurrence["ordinal"]] = candidate["asset_id"]
        if (
            candidate["status"] == "useful"
            and analysis is not None
            and not occurrences
            and candidate.get("asset_id")
        ):
            additional.append({**candidate, "parsed_analysis": analysis})

    from universe.acquisition.article_images import associate_article_images

    association = associate_article_images(
        raw_markdown,
        analyses=analyses,
        local_url_for=lambda reference: (
            f"/api/source-assets/{local_assets[reference.ordinal]}"
            if reference.ordinal in local_assets
            else None
        ),
    )
    canonical_markdown = association.canonical_markdown.rstrip()
    if additional:
        sections = [canonical_markdown, "", "## Additional source images"]
        for candidate in additional:
            analysis = candidate["parsed_analysis"]
            label = candidate.get("alt_text") or f"Source image {candidate['ordinal']}"
            atom = [
                f"![{_markdown_alt(label)}](/api/source-assets/{candidate['asset_id']})"
            ]
            if analysis.pedagogical_importance == "important":
                if analysis.description:
                    atom.append(f"Image description: {analysis.description}")
                if analysis.visible_text:
                    atom.append(f"OCR: {analysis.visible_text}")
                if analysis.limitations:
                    atom.append(f"Image limitations: {analysis.limitations}")
            else:
                atom.append("Image analysis: unresolved")
            sections.extend(["", "\n".join(atom)])
        canonical_markdown = "\n".join(sections).rstrip()
    canonical_markdown += "\n"
    base_enriched_id = f"{markdown_artifact_id}:images"
    manifest = {
        **dict(association.manifest),
        "schema_version": ARTICLE_IMAGE_ASSOCIATION_VERSION,
        "source_markdown_artifact_id": markdown_artifact_id,
        "additional_image_candidate_ids": [item["id"] for item in additional],
        "candidate_outcomes": [
            {
                "id": item["id"],
                "status": item["status"],
                "failure_code": item["failure_code"],
                "asset_id": item["asset_id"],
                "analysis_id": item["analysis_id"],
            }
            for item in candidates
        ],
    }
    if is_video:
        manifest.update(
            {
                "schema_version": "video-frame-association.v1",
                "source_media_type": "video",
                "frame_extractor": source_metadata.get("frame_extractor"),
                "frame_count": source_metadata.get("frame_count", len(candidates)),
                "speech_evidence": source_metadata.get("speech_evidence", "absent"),
                "visual_analysis": (
                    "attention"
                    if any(item["status"] == "failed" for item in candidates)
                    else "complete"
                ),
                "pipeline_requires_cleanup": True,
            }
        )
    existing = conn.execute(
        "SELECT body, metadata FROM artifact WHERE id = %s",
        (base_enriched_id,),
    ).fetchone()
    if existing is None or (
        existing[0] == canonical_markdown and dict(existing[1] or {}) == manifest
    ):
        enriched_id = base_enriched_id
    else:
        revision_payload = canonical_markdown + "\n" + json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        revision = hashlib.sha256(revision_payload.encode("utf-8")).hexdigest()[:16]
        enriched_id = f"{base_enriched_id}:{revision}"

    association_tool = "video-frame-association" if is_video else "article-image-association"
    association_version = (
        "video-frame-association.v1" if is_video else ARTICLE_IMAGE_ASSOCIATION_VERSION
    )
    conn.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, tool_version, body, metadata)"
        " VALUES (%s, %s, 'markdown', %s, %s, %s, %s)"
        " ON CONFLICT (id) DO NOTHING",
        (
            enriched_id,
            snapshot_id,
            association_tool,
            association_version,
            canonical_markdown,
            Jsonb(manifest),
        ),
    )
    acquisition = conn.execute(
        "SELECT id FROM acquisition_job"
        " WHERE artifact_id = %s AND status = 'succeeded'"
        " ORDER BY created_at DESC, id DESC LIMIT 1",
        (markdown_artifact_id,),
    ).fetchone()
    if acquisition is None:
        raise ValueError("enriched article Markdown has no acquisition job")
    # Import locally to keep the image data model independent from the worker
    # dispatcher while publishing both facts in the same transaction.
    from universe.acquisition.source_cleanup_jobs import enqueue_source_cleanup

    enqueue_source_cleanup(
        conn,
        acquisition_job_id=acquisition[0],
        source_artifact_id=enriched_id,
        commit=False,
    )
    conn.commit()
    return enriched_id


def _association_candidates(
    conn: psycopg.Connection, markdown_artifact_id: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT c.id, c.ordinal, c.original_url, c.alt_text, c.placement, c.status,"
        " c.failure_code, c.diagnostics, c.asset_id, c.analysis_id, sa.result"
        " FROM source_image_candidate c"
        " LEFT JOIN source_asset_analysis sa ON sa.id = c.analysis_id"
        " WHERE c.markdown_artifact_id = %s ORDER BY c.ordinal, c.id",
        (markdown_artifact_id,),
    ).fetchall()
    keys = (
        "id",
        "ordinal",
        "original_url",
        "alt_text",
        "placement",
        "status",
        "failure_code",
        "diagnostics",
        "asset_id",
        "analysis_id",
        "analysis",
    )
    return [dict(zip(keys, row)) for row in rows]


def _analysis_from_json(value: Any) -> ArticleImageAnalysis | None:
    if not isinstance(value, Mapping):
        return None
    if {"retain", "reason_code", "ocr", "description", "limitations"} <= set(value):
        retain = value.get("retain")
        if not isinstance(retain, bool):
            return None
        # The immutable analysis ledger keeps the provider's complete payload.
        # Association only needs the retain decision for discarded images; do
        # not let unsolicited derived fields turn a valid drop into a failure.
        description = str(value.get("description") or "") if retain else ""
        visible_text = str(value.get("ocr") or "") if retain else ""
        limitations = str(value.get("limitations") or "") if retain else ""
        return ArticleImageAnalysis(
            pedagogical_importance="important" if retain else "not_important",
            description=description,
            visible_text=visible_text,
            reason=str(value.get("reason_code") or "source image decision"),
            confidence="high",
            limitations=limitations,
        )
    try:
        return ArticleImageAnalysis(
            pedagogical_importance=str(value["pedagogical_importance"]),
            description=str(value["description"]),
            visible_text=str(value["visible_text"]),
            reason=str(value["reason"]),
            confidence=str(value["confidence"]),
            limitations=str(value.get("limitations") or ""),
        )
    except KeyError:
        return None


def _markdown_alt(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def list_article_images_for_artifact(
    conn: psycopg.Connection, artifact_id: str
) -> list[dict[str, Any]]:
    """Return safe sidecar state for UI and later tutor retrieval."""
    rows = conn.execute(
        "WITH RECURSIVE lineage(id) AS ("
        " SELECT %s::text"
        " UNION"
        " SELECT a.metadata->>'source_markdown_artifact_id'"
        " FROM artifact a JOIN lineage l ON a.id = l.id"
        " WHERE a.metadata ? 'source_markdown_artifact_id'"
        ")"
        "SELECT c.id, c.ordinal, c.original_url, c.alt_text, c.status,"
        " c.failure_code, c.diagnostics, c.asset_id, a.kind, a.mime_type, a.filename,"
        " a.metadata,"
        " sa.result, sa.provider, sa.requested_model, sa.response_model,"
        " sa.diagnostics"
        " FROM source_image_candidate c"
        " LEFT JOIN source_asset a ON a.id = c.asset_id"
        " LEFT JOIN source_asset_analysis sa ON sa.id = c.analysis_id"
        " WHERE c.markdown_artifact_id IN (SELECT id FROM lineage)"
        " ORDER BY c.ordinal, c.id",
        (artifact_id,),
    ).fetchall()
    keys = (
        "id", "ordinal", "original_url", "alt_text", "status", "failure_code",
        "diagnostics", "asset_id", "asset_kind", "mime_type", "filename",
        "asset_metadata", "analysis",
        "provider", "requested_model", "response_model", "analysis_diagnostics",
    )
    result = [dict(zip(keys, row)) for row in rows]
    for item in result:
        item["asset_url"] = (
            f"/api/source-assets/{item['asset_id']}" if item["asset_id"] else None
        )
    return result
