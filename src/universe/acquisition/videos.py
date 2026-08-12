"""YouTube preflight and deterministic speech/visual evidence materialization.

Only publisher-uploaded tracks from yt-dlp's ``subtitles`` catalog are
eligible as transcript evidence. An original automatic-caption track may be
read transiently only to decide whether useful speech exists; its text and URL
are never persisted or published. Candidate frames are extracted locally by
Summarize and interpreted by the same grouped visual Module used for article
images.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ContextManager, Mapping, Protocol

import httpx
import psycopg
from psycopg.types.json import Jsonb

from universe.acquisition.job_lease import (
    ConnectionFactory,
    JobLease,
    JobLeaseLost,
    separate_connection_factory,
)
from universe.settings import (
    acquisition_lease_minutes,
    openrouter_api_key,
    openrouter_video_provider_routing,
    video_caption_languages,
    video_teaching_beat_model,
    video_stt_chunk_seconds,
    video_stt_fallback_model,
    video_stt_model,
    video_stt_timeout_seconds,
    video_stt_workers,
)
from universe.acquisition.video_teaching_beats import (
    OpenRouterGeminiTeachingBeatAdapter,
    TeachingBeatAdapter,
    TeachingBeatDocument,
    YtDlpTeachingBeatFrameMaterializer,
    validate_document as validate_teaching_beat_document,
)
from universe.model_client import ModelClient
from universe.syllabus import youtube_video_id as normalize_youtube_video_id


YOUTUBE_PROVIDER = "youtube/v1"
PREFLIGHT_VERSION = "youtube-preflight/v2"
GROUPING_VERSION = "timestamp-groups/v1"
AUTOMATIC_STT_MAX_SECONDS = 120 * 60
STT_OPERATION_VERSION = "openrouter-stt/v1"
FRAME_EXTRACTION_VERSION = "summarize-slides/v1"
SPEECH_PROBE_VERSION = "youtube-original-auto-caption-presence/v1"


@dataclass(frozen=True)
class VideoMetadata:
    title: str
    channel: str | None
    duration_seconds: float | None
    uploaded_caption_languages: tuple[str, ...]
    language: str | None = None
    speech_evidence: str = "unknown"
    speech_probe: dict[str, Any] | None = None


@dataclass(frozen=True)
class CaptionDownload:
    language: str
    vtt: str
    raw_bytes: bytes | None = None


@dataclass(frozen=True)
class AudioChunk:
    ordinal: int
    start_ms: int
    end_ms: int
    sha256: str
    path: Path


@dataclass(frozen=True)
class PreparedAudio:
    audio_sha256: str
    duration_ms: int
    chunks: tuple[AudioChunk, ...]


@dataclass(frozen=True)
class SttSegment:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class SttResponse:
    text: str
    language: str | None
    segments: tuple[SttSegment, ...]
    response_model: str | None
    provider: str | None
    usage: dict[str, Any]
    duration_ms: int
    generation_id: str | None = None


class SttError(RuntimeError):
    def __init__(
        self,
        failure_code: str,
        *,
        fallback_allowed: bool,
        diagnostics: dict[str, Any] | None = None,
        usage: dict[str, Any] | None = None,
        duration_ms: int = 0,
    ) -> None:
        super().__init__(failure_code)
        self.failure_code = failure_code
        self.fallback_allowed = fallback_allowed
        self.diagnostics = diagnostics or {}
        self.usage = usage or {}
        self.duration_ms = max(0, duration_ms)


@dataclass(frozen=True)
class TranscriptSegment:
    start_ms: int
    end_ms: int
    text: str
    source_ref: str


@dataclass(frozen=True)
class VideoFrame:
    """One timestamped frame whose bytes exist only until durable storage."""

    timestamp_ms: int
    body: bytes
    mime_type: str
    filename: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


@dataclass(frozen=True)
class VideoAcquisition:
    route: str
    language: str | None
    segments: tuple[TranscriptSegment, ...]
    markdown: str
    content_hash: str
    preflight_id: str
    source_url: str
    raw_vtt: str | None = None
    raw_vtt_bytes: bytes | None = None
    frames: tuple[VideoFrame, ...] = ()
    frame_extractor: str | None = None
    teaching_beats: TeachingBeatDocument | None = None


class VideoAdapter(Protocol):
    def probe(self, source_url: str) -> VideoMetadata: ...

    def download_uploaded_caption(
        self, source_url: str, *, language: str
    ) -> CaptionDownload: ...

    def prepare_audio(
        self, source_url: str, *, chunk_seconds: int
    ) -> ContextManager[PreparedAudio]: ...

    def transcribe_chunk(
        self, chunk: AudioChunk, *, model: str, language: str | None
    ) -> SttResponse: ...

    def extract_frames(self, source_url: str) -> tuple[VideoFrame, ...]: ...

    def acquire_visual_teaching_beats(
        self, source_url: str, *, duration_seconds: float | None
    ) -> TeachingBeatDocument: ...


class VideoAdapterError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        category: str | None = None,
        retriable: bool = False,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.category = category or code
        self.retriable = retriable
        self.diagnostics = diagnostics or {}


PREFLIGHT_COLUMNS = (
    "id", "source_id", "probe_version", "input_fingerprint", "status",
    "title", "channel", "duration_seconds", "uploaded_caption_languages",
    "selected_caption_language", "route", "failure_code", "diagnostics",
    "created_at",
)


def _preflight(row: tuple | None) -> dict[str, Any] | None:
    return dict(zip(PREFLIGHT_COLUMNS, row)) if row else None


def _identity_video_id(identity: object) -> str:
    if not isinstance(identity, dict):
        raise ValueError("video Source has no stable identity")
    if identity.get("kind") != "video" or identity.get("provider") != "youtube":
        raise ValueError("YouTube Adapter requires a YouTube Source identity")
    raw_video_id = identity.get("video_id")
    if not isinstance(raw_video_id, str) or not raw_video_id.strip():
        raise ValueError("YouTube Source identity has no video id")
    normalized = normalize_youtube_video_id(raw_video_id)
    if normalized:
        return normalized
    # Historical test/dev ledgers used short synthetic ids. Preserve those plain
    # tokens, but never forward whitespace or query-like content to a provider.
    legacy = raw_video_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]+", legacy):
        return legacy
    raise ValueError("YouTube Source identity has an invalid video id")


def youtube_url(identity: object) -> str:
    return f"https://www.youtube.com/watch?v={_identity_video_id(identity)}"


def _source(conn: psycopg.Connection, source_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT id, identity, title, media_type FROM source WHERE id = %s",
        (source_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown source {source_id}")
    source = dict(zip(("id", "identity", "title", "media_type"), row))
    if source["media_type"] != "video":
        raise ValueError("video preflight requires a video Source")
    youtube_url(source["identity"])
    return source


def _input_fingerprint(source: dict[str, Any]) -> str:
    material = json.dumps(
        {
            "source_id": source["id"],
            "identity": source["identity"],
            "probe_version": PREFLIGHT_VERSION,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()


def latest_preflight(
    conn: psycopg.Connection, source_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, source_id, probe_version, input_fingerprint, status, title,"
        " channel, duration_seconds, uploaded_caption_languages,"
        " selected_caption_language, route, failure_code, diagnostics, created_at"
        " FROM video_preflight WHERE source_id = %s"
        " ORDER BY created_at DESC, id DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    return _preflight(row)


def get_preflight(
    conn: psycopg.Connection, preflight_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, source_id, probe_version, input_fingerprint, status, title,"
        " channel, duration_seconds, uploaded_caption_languages,"
        " selected_caption_language, route, failure_code, diagnostics, created_at"
        " FROM video_preflight WHERE id = %s",
        (preflight_id,),
    ).fetchone()
    return _preflight(row)


def _caption_order(
    available: tuple[str, ...], preferred: tuple[str, ...] | None = None
) -> tuple[str, ...]:
    preferred = preferred or video_caption_languages()
    unique = tuple(dict.fromkeys(item for item in available if item))
    ordered: list[str] = []
    for wanted in preferred:
        for language in unique:
            if language == wanted and language not in ordered:
                ordered.append(language)
        wanted_base = wanted.lower().split("-", 1)[0]
        for language in unique:
            if (
                language.lower().split("-", 1)[0] == wanted_base
                and language not in ordered
            ):
                ordered.append(language)
    ordered.extend(language for language in sorted(unique) if language not in ordered)
    return tuple(ordered)


def _route(metadata: VideoMetadata) -> tuple[str, str | None]:
    languages = _caption_order(metadata.uploaded_caption_languages)
    if languages:
        return "uploaded_caption", languages[0]
    if metadata.speech_evidence == "absent":
        return "visual_only", None
    duration = metadata.duration_seconds
    if duration is not None and duration <= AUTOMATIC_STT_MAX_SECONDS:
        return "automatic_stt", None
    return "approval_required", None


def refresh_preflight(
    conn: psycopg.Connection,
    source_id: str,
    *,
    adapter: VideoAdapter | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Record or reuse one provider-free readiness result for a YouTube Source."""
    source = _source(conn, source_id)
    fingerprint = _input_fingerprint(source)
    if not force:
        existing = conn.execute(
            "SELECT id, source_id, probe_version, input_fingerprint, status, title,"
            " channel, duration_seconds, uploaded_caption_languages,"
            " selected_caption_language, route, failure_code, diagnostics, created_at"
            " FROM video_preflight WHERE source_id = %s AND input_fingerprint = %s"
            " ORDER BY created_at DESC, id DESC LIMIT 1",
            (source_id, fingerprint),
        ).fetchone()
        if existing is not None:
            result = _preflight(existing)
            assert result is not None
            result["deduplicated"] = True
            return result

    adapter = adapter or YtDlpYouTubeAdapter()
    preflight_id = f"vpf-{uuid.uuid4().hex}"
    try:
        metadata = adapter.probe(youtube_url(source["identity"]))
        route, selected = _route(metadata)
        languages = list(_caption_order(metadata.uploaded_caption_languages))
        conn.execute(
            "INSERT INTO video_preflight"
            " (id, source_id, probe_version, input_fingerprint, status, title,"
            " channel, duration_seconds, uploaded_caption_languages,"
            " selected_caption_language, route, diagnostics)"
            " VALUES (%s, %s, %s, %s, 'succeeded', %s, %s, %s, %s, %s, %s, %s)",
            (
                preflight_id, source_id, PREFLIGHT_VERSION, fingerprint,
                metadata.title or source.get("title"), metadata.channel,
                metadata.duration_seconds, Jsonb(languages), selected, route,
                Jsonb({
                    "category": "success",
                    "automatic_captions_used": False,
                    "detected_language": metadata.language,
                    "speech_evidence": metadata.speech_evidence,
                    "speech_probe": metadata.speech_probe or {
                        "version": SPEECH_PROBE_VERSION,
                        "status": "unknown",
                        "reason": "adapter_did_not_probe",
                    },
                }),
            ),
        )
    except VideoAdapterError as exc:
        conn.execute(
            "INSERT INTO video_preflight"
            " (id, source_id, probe_version, input_fingerprint, status,"
            " failure_code, diagnostics)"
            " VALUES (%s, %s, %s, %s, 'failed', %s, %s)",
            (
                preflight_id, source_id, PREFLIGHT_VERSION, fingerprint, exc.code,
                Jsonb({"category": exc.category, "retriable": exc.retriable}),
            ),
        )
    conn.commit()
    result = latest_preflight(conn, source_id)
    assert result is not None and result["id"] == preflight_id
    result["deduplicated"] = False
    return result


def acquisition_input(
    conn: psycopg.Connection,
    source_id: str,
    *,
    authorize_paid_transcription: bool = False,
) -> tuple[dict[str, Any], str, str]:
    preflight = latest_preflight(conn, source_id)
    if preflight is None or preflight["status"] != "succeeded":
        raise ValueError("YouTube metadata preflight is required before queueing")
    route = preflight["route"]
    if route == "approval_required" and not authorize_paid_transcription:
        raise PermissionError("video transcription requires explicit authorization")
    effective_route = "automatic_stt" if route == "approval_required" else route
    request_input = {
        "video_preflight_id": preflight["id"],
        "transcript_route": effective_route,
        "video_processing_authorized": bool(authorize_paid_transcription),
        "policy_version": "video-speech-policy/v2",
        "grouping_version": GROUPING_VERSION,
        "visual_route": FRAME_EXTRACTION_VERSION,
    }
    if effective_route == "automatic_stt":
        request_input.update(
            {
                "stt_model": video_stt_model(),
                "stt_fallback_model": video_stt_fallback_model(),
                "stt_chunk_seconds": video_stt_chunk_seconds(),
                "stt_operation_version": STT_OPERATION_VERSION,
            }
        )
    material = json.dumps(request_input, sort_keys=True, separators=(",", ":"))
    return request_input, hashlib.sha256(material.encode()).hexdigest(), preflight["id"]


def parse_vtt(vtt: str) -> tuple[TranscriptSegment, ...]:
    segments: list[TranscriptSegment] = []
    cue_lines: list[str] = []
    start_ms: int | None = None
    end_ms: int | None = None

    def flush() -> None:
        nonlocal cue_lines, start_ms, end_ms
        if cue_lines and start_ms is not None and end_ms is not None:
            text = " ".join(" ".join(cue_lines).split())
            if text:
                segments.append(
                    TranscriptSegment(start_ms, end_ms, text, f"cue:{len(segments) + 1}")
                )
        cue_lines = []
        start_ms = None
        end_ms = None

    timing = re.compile(
        r"^(?P<start>\d{1,2}:\d{2}(?::\d{2})?\.\d{1,3})\s+-->\s+"
        r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?\.\d{1,3})"
    )
    for raw in vtt.splitlines() + [""]:
        line = raw.strip()
        matched = timing.match(line)
        if matched:
            flush()
            start_ms = _timestamp_ms(matched.group("start"))
            end_ms = _timestamp_ms(matched.group("end"))
            continue
        if not line:
            flush()
            continue
        if line == "WEBVTT" or line.startswith(("NOTE", "STYLE", "Kind:", "Language:")):
            continue
        if start_ms is not None:
            cleaned = html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
            if cleaned:
                cue_lines.append(cleaned)
    return tuple(segments)


def _timestamp_ms(value: str) -> int:
    parts = value.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError("invalid caption timestamp")
    return int(round((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000))


def _groups(
    segments: tuple[TranscriptSegment, ...],
    *,
    max_span_ms: int = 45_000,
    max_chars: int = 700,
    max_gap_ms: int = 4_000,
) -> list[list[TranscriptSegment]]:
    grouped: list[list[TranscriptSegment]] = []
    current: list[TranscriptSegment] = []
    for segment in segments:
        if current:
            gap = segment.start_ms - current[-1].end_ms
            span = segment.end_ms - current[0].start_ms
            chars = sum(len(item.text) for item in current) + len(segment.text) + len(current)
            if gap > max_gap_ms or span > max_span_ms or chars > max_chars:
                grouped.append(current)
                current = []
        current.append(segment)
    if current:
        grouped.append(current)
    return grouped


def _clock(milliseconds: int, *, ceil: bool = False) -> str:
    seconds = math.ceil(milliseconds / 1000) if ceil else milliseconds // 1000
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return (
        f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        if hours
        else f"{minutes:02d}:{seconds:02d}"
    )


def render_transcript_markdown(segments: tuple[TranscriptSegment, ...]) -> str:
    if not segments:
        raise VideoAdapterError(
            "video_transcript_assembly_failed", category="empty_transcript"
        )
    sections = []
    for group in _groups(segments):
        label = f"[{_clock(group[0].start_ms)}–{_clock(group[-1].end_ms, ceil=True)}]"
        sections.append(f"## {label}\n\n{' '.join(item.text for item in group)}")
    return "\n\n".join(sections).rstrip() + "\n"


def _dedupe_frames(frames: tuple[VideoFrame, ...]) -> tuple[VideoFrame, ...]:
    """Drop byte-identical frames while preserving the first timestamp."""
    unique: list[VideoFrame] = []
    seen: set[str] = set()
    for frame in sorted(frames, key=lambda item: (item.timestamp_ms, item.filename)):
        if frame.timestamp_ms < 0 or not frame.body:
            raise VideoAdapterError(
                "video_frame_extraction_failed", category="invalid_frame"
            )
        if frame.mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise VideoAdapterError(
                "video_frame_extraction_failed", category="unsupported_frame_type"
            )
        digest = frame.sha256
        if digest in seen:
            continue
        seen.add(digest)
        unique.append(frame)
    return tuple(unique)


def _frame_markdown(video_id: str, frame: VideoFrame) -> str:
    label = f"Video frame at {_clock(frame.timestamp_ms)}"
    locator = f"video-frame://{video_id}/{frame.timestamp_ms}"
    seconds = max(0, frame.timestamp_ms // 1000)
    target = f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"
    return f"[![{label}]({locator})]({target})"


def render_video_markdown(
    segments: tuple[TranscriptSegment, ...],
    frames: tuple[VideoFrame, ...],
    *,
    video_id: str,
) -> str:
    """Interleave exact timed speech groups and timestamp-linked frame atoms."""
    frames = _dedupe_frames(frames)
    groups = _groups(segments) if segments else []
    used_frames: set[int] = set()
    sections: list[tuple[int, str]] = []
    for group in groups:
        start_ms = group[0].start_ms
        end_ms = group[-1].end_ms
        label = f"[{_clock(start_ms)}–{_clock(end_ms, ceil=True)}]"
        parts = [f"## {label}", " ".join(item.text for item in group)]
        for index, frame in enumerate(frames):
            if start_ms <= frame.timestamp_ms <= end_ms:
                parts.append(_frame_markdown(video_id, frame))
                used_frames.add(index)
        sections.append((start_ms, "\n\n".join(parts)))
    for index, frame in enumerate(frames):
        if index in used_frames:
            continue
        sections.append(
            (
                frame.timestamp_ms,
                f"## [{_clock(frame.timestamp_ms)}]\n\n"
                f"{_frame_markdown(video_id, frame)}",
            )
        )
    if not sections:
        raise VideoAdapterError(
            "video_evidence_empty", category="no_speech_or_frames", retriable=True
        )
    sections.sort(key=lambda item: (item[0], item[1]))
    return "\n\n".join(section for _, section in sections).rstrip() + "\n"


def render_visual_teaching_beats(
    document: TeachingBeatDocument, *, video_id: str
) -> str:
    """Project beat headings and frame locators without duplicating interpretation.

    The persisted Teaching Beats reading later enriches each locator with an
    atomic Image description/OCR/limitations payload. Keeping the explanation
    there prevents passage refinement from detaching a claim from its evidence.
    """
    document = validate_teaching_beat_document(document)
    sections = []
    for beat, frame in zip(document.beats, document.frames):
        label = f"[{_clock(beat.start_ms)}–{_clock(beat.end_ms, ceil=True)}]"
        sections.append(
            "\n\n".join(
                (
                    f"## {label} {beat.heading.strip()}",
                    _frame_markdown(video_id, frame),
                )
            )
        )
    return "\n\n".join(sections).rstrip() + "\n"


STT_CHUNK_COLUMNS = (
    "id", "status", "window_start_ms", "window_end_ms", "text", "segments",
    "response_language", "response_model", "provider", "usage", "duration_ms",
    "failure_code", "diagnostics", "claim_token",
)


def _stt_chunk(row: tuple | None) -> dict[str, Any] | None:
    return dict(zip(STT_CHUNK_COLUMNS, row)) if row else None


def _model_route_hash(
    language: str | None,
    *,
    primary_model: str,
    fallback_model: str | None,
    operation_version: str,
) -> str:
    material = json.dumps(
        {
            "primary": primary_model,
            "fallback": fallback_model,
            "language": language,
            "operation_version": operation_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _chunk_id(
    source_id: str,
    prepared: PreparedAudio,
    chunk: AudioChunk,
    language: str | None,
    *,
    primary_model: str,
    fallback_model: str | None,
    operation_version: str,
) -> str:
    material = json.dumps(
        {
            "source_id": source_id,
            "audio_sha256": prepared.audio_sha256,
            "chunk_sha256": chunk.sha256,
            "window_start_ms": chunk.start_ms,
            "window_end_ms": chunk.end_ms,
            "model_route_hash": _model_route_hash(
                language,
                primary_model=primary_model,
                fallback_model=fallback_model,
                operation_version=operation_version,
            ),
            "operation_version": operation_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"vsc-{hashlib.sha256(material.encode()).hexdigest()}"


def _materialize_stt_chunks(
    conn: psycopg.Connection,
    *,
    job: dict[str, Any],
    prepared: PreparedAudio,
    language: str | None,
    primary_model: str,
    fallback_model: str | None,
    operation_version: str,
) -> list[tuple[AudioChunk, str]]:
    if not prepared.chunks:
        raise VideoAdapterError(
            "video_ffmpeg_failed",
            category="audio_chunks_missing",
            retriable=True,
        )
    materialized = []
    route_hash = _model_route_hash(
        language,
        primary_model=primary_model,
        fallback_model=fallback_model,
        operation_version=operation_version,
    )
    for chunk in prepared.chunks:
        chunk_id = _chunk_id(
            job["source_id"],
            prepared,
            chunk,
            language,
            primary_model=primary_model,
            fallback_model=fallback_model,
            operation_version=operation_version,
        )
        conn.execute(
            "INSERT INTO video_stt_chunk"
            " (id, source_id, audio_sha256, chunk_sha256, window_start_ms,"
            " window_end_ms, requested_model, fallback_model, language,"
            " operation_version, model_route_hash)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT DO NOTHING",
            (
                chunk_id, job["source_id"], prepared.audio_sha256, chunk.sha256,
                chunk.start_ms, chunk.end_ms, primary_model,
                fallback_model, language, operation_version, route_hash,
            ),
        )
        conn.execute(
            "INSERT INTO video_stt_job_chunk (acquisition_job_id, chunk_id, ordinal)"
            " VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (job["id"], chunk_id, chunk.ordinal),
        )
        materialized.append((chunk, chunk_id))
    conn.commit()
    return materialized


def _get_stt_chunk(conn: psycopg.Connection, chunk_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT id, status, window_start_ms, window_end_ms, text, segments,"
        " response_language, response_model, provider, usage, duration_ms,"
        " failure_code, diagnostics, claim_token"
        " FROM video_stt_chunk WHERE id = %s",
        (chunk_id,),
    ).fetchone()
    result = _stt_chunk(row)
    if result is None:
        raise RuntimeError("materialized STT chunk is missing")
    return result


def _claim_stt_chunk(
    conn: psycopg.Connection, chunk_id: str
) -> dict[str, Any] | None:
    token = uuid.uuid4().hex
    row = conn.execute(
        "UPDATE video_stt_chunk SET status = 'running',"
        " attempt_count = attempt_count + 1, claimed_at = now(), claim_token = %s,"
        " lease_expires_at = now() + (%s * interval '1 minute'),"
        " failure_code = NULL, diagnostics = '{}'::jsonb, finished_at = NULL,"
        " updated_at = now() WHERE id = %s AND (status IN ('queued', 'failed')"
        " OR (status = 'running' AND lease_expires_at < now()))"
        " RETURNING id, status, window_start_ms, window_end_ms, text, segments,"
        " response_language, response_model, provider, usage, duration_ms,"
        " failure_code, diagnostics, claim_token",
        (token, acquisition_lease_minutes(), chunk_id),
    ).fetchone()
    conn.commit()
    return _stt_chunk(row)


def _next_attempt_no(conn: psycopg.Connection, chunk_id: str) -> int:
    return conn.execute(
        "SELECT coalesce(max(attempt_no), 0) + 1 FROM video_stt_attempt"
        " WHERE chunk_id = %s",
        (chunk_id,),
    ).fetchone()[0]


def _record_stt_attempt(
    conn: psycopg.Connection,
    *,
    chunk_id: str,
    requested_model: str,
    operation_version: str,
    status: str,
    response: SttResponse | None = None,
    error: SttError | None = None,
) -> None:
    attempt_no = _next_attempt_no(conn, chunk_id)
    conn.execute(
        "INSERT INTO video_stt_attempt"
        " (id, chunk_id, attempt_no, requested_model, operation_version, status,"
        " response_model, provider, generation_id, language, usage, duration_ms,"
        " failure_code, diagnostics)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            f"vsa-{uuid.uuid4().hex}", chunk_id, attempt_no, requested_model,
            operation_version, status,
            response.response_model if response else None,
            response.provider if response else None,
            response.generation_id if response else None,
            response.language if response else None,
            Jsonb(response.usage if response else (error.usage if error else {})),
            response.duration_ms if response else (error.duration_ms if error else 0),
            error.failure_code if error else None,
            Jsonb(error.diagnostics if error else {}),
        ),
    )


def _base_language(value: str | None) -> str | None:
    clean = (value or "").strip().lower().replace("_", "-")
    return clean.split("-", 1)[0] if clean else None


def _validated_stt_response(
    response: object, *, expected_language: str | None
) -> SttResponse:
    if not isinstance(response, SttResponse):
        raise SttError(
            "video_stt_provider_failure",
            fallback_allowed=True,
            diagnostics={"category": "non_stt_response"},
        )
    if not response.text.strip():
        raise SttError(
            "video_stt_empty_transcript",
            fallback_allowed=True,
            diagnostics={"category": "empty_transcript"},
            usage=response.usage,
            duration_ms=response.duration_ms,
        )
    expected = _base_language(expected_language)
    observed = _base_language(response.language)
    if expected and observed and expected != observed:
        raise SttError(
            "video_stt_language_mismatch",
            fallback_allowed=True,
            diagnostics={"expected_language": expected, "observed_language": observed},
            usage=response.usage,
            duration_ms=response.duration_ms,
        )
    return response


def _call_stt(
    adapter: VideoAdapter,
    chunk: AudioChunk,
    *,
    model: str,
    language: str | None,
) -> SttResponse:
    try:
        response = adapter.transcribe_chunk(chunk, model=model, language=language)
    except SttError:
        raise
    except Exception as exc:
        raise SttError(
            "video_stt_provider_failure",
            fallback_allowed=True,
            diagnostics={"category": type(exc).__name__},
        ) from exc
    return _validated_stt_response(response, expected_language=language)


def _finish_stt_success(
    conn: psycopg.Connection,
    claimed: dict[str, Any],
    response: SttResponse,
) -> None:
    segments = [
        {"start_ms": item.start_ms, "end_ms": item.end_ms, "text": item.text}
        for item in response.segments
    ]
    updated = conn.execute(
        "UPDATE video_stt_chunk SET status = 'succeeded', text = %s, segments = %s,"
        " response_language = %s, response_model = %s, provider = %s, usage = %s,"
        " duration_ms = %s, generation_id = %s, failure_code = NULL,"
        " diagnostics = %s, finished_at = now(), lease_expires_at = NULL,"
        " claim_token = NULL, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (
            response.text.strip(), Jsonb(segments), response.language,
            response.response_model, response.provider, Jsonb(response.usage),
            response.duration_ms, response.generation_id,
            Jsonb({"category": "success"}), claimed["id"], claimed["claim_token"],
        ),
    )
    if updated.rowcount != 1:
        conn.rollback()
        raise VideoAdapterError(
            "video_stt_chunk_failed", category="claim_lost", retriable=True
        )
    conn.commit()


def _finish_stt_failure(
    conn: psycopg.Connection,
    claimed: dict[str, Any],
    error: SttError,
) -> None:
    updated = conn.execute(
        "UPDATE video_stt_chunk SET status = 'failed', failure_code = %s,"
        " diagnostics = %s, finished_at = now(), lease_expires_at = NULL,"
        " claim_token = NULL, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (
            error.failure_code, Jsonb(error.diagnostics), claimed["id"],
            claimed["claim_token"],
        ),
    )
    if updated.rowcount != 1:
        conn.rollback()
        raise VideoAdapterError(
            "video_stt_chunk_failed", category="claim_lost", retriable=True
        )
    conn.commit()


def _process_stt_chunk(
    conn: psycopg.Connection,
    *,
    adapter: VideoAdapter,
    audio_chunk: AudioChunk,
    chunk_id: str,
    language: str | None,
    primary_model: str,
    fallback_model: str | None,
    operation_version: str,
    db_lock: threading.Lock | None = None,
    lease_connection_factory: ConnectionFactory | None = None,
) -> dict[str, Any]:
    def locked():
        return db_lock if db_lock is not None else nullcontext()

    with locked():
        existing = _get_stt_chunk(conn, chunk_id)
        if existing["status"] == "succeeded":
            return existing
        heartbeat_connection = (
            lease_connection_factory or separate_connection_factory(conn)
        )
        claimed = _claim_stt_chunk(conn, chunk_id)
    if claimed is None:
        raise VideoAdapterError(
            "video_stt_chunk_failed",
            category="chunk_claim_unavailable",
            retriable=True,
            diagnostics={"chunk_id": chunk_id},
        )

    last_error: SttError | None = None
    models = tuple(item for item in (primary_model, fallback_model) if item)
    for model in models:
        try:
            with JobLease(
                heartbeat_connection,
                table="video_stt_chunk",
                row_id=claimed["id"],
                claim_token=claimed["claim_token"],
            ):
                response = _call_stt(
                    adapter, audio_chunk, model=model, language=language
                )
        except JobLeaseLost as exc:
            raise VideoAdapterError(
                "video_stt_chunk_failed",
                category="claim_lost",
                retriable=True,
                diagnostics={"chunk_id": chunk_id},
            ) from exc
        except SttError as exc:
            last_error = exc
            with locked():
                _record_stt_attempt(
                    conn,
                    chunk_id=chunk_id,
                    requested_model=model,
                    operation_version=operation_version,
                    status="failed",
                    error=exc,
                )
                conn.commit()
            if model == primary_model and fallback_model and exc.fallback_allowed:
                continue
            with locked():
                _finish_stt_failure(conn, claimed, exc)
                return _get_stt_chunk(conn, chunk_id)
        except Exception as exc:
            lease_error = SttError(
                "video_stt_chunk_failed",
                fallback_allowed=False,
                diagnostics={
                    "category": "lease_heartbeat_unavailable",
                    "exception": type(exc).__name__,
                },
            )
            with locked():
                _finish_stt_failure(conn, claimed, lease_error)
                return _get_stt_chunk(conn, chunk_id)
        with locked():
            _record_stt_attempt(
                conn,
                chunk_id=chunk_id,
                requested_model=model,
                operation_version=operation_version,
                status="succeeded",
                response=response,
            )
            _finish_stt_success(conn, claimed, response)
            return _get_stt_chunk(conn, chunk_id)

    assert last_error is not None
    with locked():
        _finish_stt_failure(conn, claimed, last_error)
        return _get_stt_chunk(conn, chunk_id)


def _segments_from_stt_chunks(
    conn: psycopg.Connection, acquisition_job_id: str
) -> tuple[TranscriptSegment, ...]:
    rows = conn.execute(
        "SELECT jc.ordinal, c.id, c.window_start_ms, c.window_end_ms, c.text,"
        " c.segments FROM video_stt_job_chunk jc"
        " JOIN video_stt_chunk c ON c.id = jc.chunk_id"
        " WHERE jc.acquisition_job_id = %s AND c.status = 'succeeded'"
        " ORDER BY jc.ordinal",
        (acquisition_job_id,),
    ).fetchall()
    segments: list[TranscriptSegment] = []
    for _ordinal, chunk_id, start_ms, end_ms, text, provider_segments in rows:
        valid = []
        if isinstance(provider_segments, list):
            for index, item in enumerate(provider_segments, 1):
                if not isinstance(item, dict) or not str(item.get("text") or "").strip():
                    continue
                relative_start = int(item.get("start_ms") or 0)
                relative_end = int(item.get("end_ms") or (end_ms - start_ms))
                if relative_start < 0 or relative_end < relative_start:
                    continue
                valid.append(
                    TranscriptSegment(
                        start_ms + relative_start,
                        min(end_ms, start_ms + relative_end),
                        str(item["text"]).strip(),
                        f"{chunk_id}:segment:{index}",
                    )
                )
        if valid:
            segments.extend(valid)
        else:
            segments.append(
                TranscriptSegment(start_ms, end_ms, str(text).strip(), chunk_id)
            )
    return tuple(segments)


def _acquire_stt(
    conn: psycopg.Connection,
    *,
    job: dict[str, Any],
    source: dict[str, Any],
    preflight: dict[str, Any],
    adapter: VideoAdapter,
    lease_connection_factory: ConnectionFactory | None = None,
) -> VideoAcquisition:
    source_url = youtube_url(source["identity"])
    video_id = _identity_video_id(source["identity"])
    detected = (preflight.get("diagnostics") or {}).get("detected_language")
    language = _base_language(detected if isinstance(detected, str) else None)
    request_input = job.get("request_input") or {}
    primary_model = str(request_input.get("stt_model") or video_stt_model())
    fallback_model = str(
        request_input.get("stt_fallback_model") or video_stt_fallback_model()
    ) or None
    operation_version = str(
        request_input.get("stt_operation_version") or STT_OPERATION_VERSION
    )
    chunk_seconds = int(
        request_input.get("stt_chunk_seconds") or video_stt_chunk_seconds()
    )
    failures = []
    try:
        preparation = adapter.prepare_audio(
            source_url, chunk_seconds=chunk_seconds
        )
        with preparation as prepared:
            chunks = _materialize_stt_chunks(
                conn,
                job=job,
                prepared=prepared,
                language=language,
                primary_model=primary_model,
                fallback_model=fallback_model,
                operation_version=operation_version,
            )
            workers = min(
                len(chunks),
                max(1, int(getattr(adapter, "stt_workers", 1))),
            )
            db_lock = threading.Lock() if workers > 1 else None

            def process(pair):
                audio_chunk, chunk_id = pair
                return chunk_id, _process_stt_chunk(
                    conn,
                    adapter=adapter,
                    audio_chunk=audio_chunk,
                    chunk_id=chunk_id,
                    language=language,
                    primary_model=primary_model,
                    fallback_model=fallback_model,
                    operation_version=operation_version,
                    db_lock=db_lock,
                    lease_connection_factory=lease_connection_factory,
                )

            if workers == 1:
                results = [process(pair) for pair in chunks]
            else:
                results = []
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    pending = {executor.submit(process, pair): pair for pair in chunks}
                    for future in as_completed(pending):
                        results.append(future.result())
            for chunk_id, result in results:
                if result["status"] != "succeeded":
                    failures.append({
                        "chunk_id": chunk_id,
                        "failure_code": result["failure_code"],
                    })
    except VideoAdapterError:
        raise
    except Exception as exc:
        raise VideoAdapterError(
            "video_ffmpeg_failed",
            category=type(exc).__name__,
            retriable=True,
        ) from exc
    if failures:
        raise VideoAdapterError(
            "video_stt_chunk_failed",
            category="stt_chunk_failed",
            retriable=True,
            diagnostics={"failed_chunks": failures},
        )
    observed_languages = sorted({
        normalized
        for (value,) in conn.execute(
            "SELECT c.response_language FROM video_stt_job_chunk jc"
            " JOIN video_stt_chunk c ON c.id = jc.chunk_id"
            " WHERE jc.acquisition_job_id = %s AND c.status = 'succeeded'"
            " AND c.response_language IS NOT NULL",
            (job["id"],),
        ).fetchall()
        if (normalized := _base_language(value))
    })
    if len(observed_languages) > 1:
        raise VideoAdapterError(
            "video_stt_language_mismatch",
            category="inconsistent_chunk_languages",
            retriable=False,
            diagnostics={"observed_languages": observed_languages},
        )
    segments = _segments_from_stt_chunks(conn, job["id"])
    if not segments:
        raise VideoAdapterError(
            "video_stt_empty_transcript", category="empty_transcript", retriable=True
        )
    if language is None:
        observed = conn.execute(
            "SELECT c.response_language FROM video_stt_job_chunk jc"
            " JOIN video_stt_chunk c ON c.id = jc.chunk_id"
            " WHERE jc.acquisition_job_id = %s AND c.response_language IS NOT NULL"
            " ORDER BY jc.ordinal LIMIT 1",
            (job["id"],),
        ).fetchone()
        language = _base_language(observed[0]) if observed else None
    frames = _adapter_frames(adapter, source_url, required=True)
    markdown = render_video_markdown(segments, frames, video_id=video_id)
    return VideoAcquisition(
        route="openrouter_stt",
        language=language,
        segments=segments,
        markdown=markdown,
        content_hash=_video_evidence_hash(segments, frames),
        preflight_id=preflight["id"],
        source_url=source_url,
        frames=frames,
        frame_extractor=FRAME_EXTRACTION_VERSION,
    )


def _adapter_frames(
    adapter: VideoAdapter,
    source_url: str,
    *,
    required: bool,
) -> tuple[VideoFrame, ...]:
    extract = getattr(adapter, "extract_frames", None)
    if not callable(extract):
        if required:
            raise VideoAdapterError(
                "video_frame_extraction_unavailable",
                category="frame_adapter_missing",
                retriable=False,
            )
        return ()
    try:
        frames = _dedupe_frames(tuple(extract(source_url)))
    except VideoAdapterError:
        raise
    except Exception as exc:
        raise VideoAdapterError(
            "video_frame_extraction_failed",
            category=type(exc).__name__,
            retriable=True,
        ) from exc
    if required and not frames:
        raise VideoAdapterError(
            "video_frame_extraction_empty",
            category="no_frames_extracted",
            retriable=True,
        )
    return frames


def _video_evidence_hash(
    segments: tuple[TranscriptSegment, ...], frames: tuple[VideoFrame, ...]
) -> str:
    material = {
        "segments": [
            {"start_ms": item.start_ms, "end_ms": item.end_ms, "text": item.text}
            for item in segments
        ],
        "frames": [
            {"timestamp_ms": item.timestamp_ms, "sha256": item.sha256}
            for item in frames
        ],
    }
    return hashlib.sha256(
        json.dumps(
            material,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _teaching_beat_evidence_hash(document: TeachingBeatDocument) -> str:
    material = {
        "input_manifest_hash": document.input_manifest_hash,
        "result_hash": document.result_hash,
        "frames": [
            {
                "timestamp_ms": int(frame.timestamp_ms),
                "sha256": str(frame.sha256),
            }
            for frame in document.frames
        ],
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def acquire_video(
    source: dict[str, Any],
    preflight: dict[str, Any],
    *,
    adapter: VideoAdapter | None = None,
    conn: psycopg.Connection | None = None,
    job: dict[str, Any] | None = None,
    lease_connection_factory: ConnectionFactory | None = None,
) -> VideoAcquisition:
    adapter = adapter or YtDlpYouTubeAdapter()
    route = preflight.get("route")
    requested_route = (job or {}).get("request_input", {}).get("transcript_route")
    source_url = youtube_url(source["identity"])
    video_id = _identity_video_id(source["identity"])
    if route == "visual_only" or requested_route == "visual_only":
        acquire_beats = getattr(adapter, "acquire_visual_teaching_beats", None)
        if not callable(acquire_beats):
            raise VideoAdapterError(
                "video_teaching_beat_analysis_unavailable",
                category="teaching_beat_adapter_missing",
                retriable=False,
            )
        try:
            teaching_beats = validate_teaching_beat_document(
                acquire_beats(
                    source_url,
                    duration_seconds=preflight.get("duration_seconds"),
                )
            )
        except VideoAdapterError:
            raise
        except Exception as exc:
            raise VideoAdapterError(
                "video_teaching_beat_analysis_failed",
                category=type(exc).__name__,
                retriable=True,
            ) from exc
        frames = tuple(teaching_beats.frames)
        return VideoAcquisition(
            route="visual_only",
            language=None,
            segments=(),
            markdown=render_visual_teaching_beats(teaching_beats, video_id=video_id),
            content_hash=_teaching_beat_evidence_hash(teaching_beats),
            preflight_id=preflight["id"],
            source_url=source_url,
            frames=frames,
            frame_extractor="gemini-teaching-beats/v1",
            teaching_beats=teaching_beats,
        )
    if route in {"automatic_stt", "approval_required"} or requested_route == "automatic_stt":
        if conn is None or job is None:
            raise ValueError("STT acquisition requires its durable job and connection")
        return _acquire_stt(
            conn,
            job=job,
            source=source,
            preflight=preflight,
            adapter=adapter,
            lease_connection_factory=lease_connection_factory,
        )
    if route != "uploaded_caption":
        raise VideoAdapterError(
            "video_transcript_assembly_failed", category="invalid_preflight_route"
        )
    language = preflight.get("selected_caption_language")
    if not isinstance(language, str) or not language:
        raise VideoAdapterError(
            "video_caption_parse_failed", category="caption_metadata_invalid"
        )
    try:
        caption = adapter.download_uploaded_caption(source_url, language=language)
    except VideoAdapterError:
        raise
    except Exception as exc:
        raise VideoAdapterError(
            "video_caption_download_failed",
            category=type(exc).__name__,
            retriable=True,
        ) from exc
    segments = parse_vtt(caption.vtt)
    if not segments:
        raise VideoAdapterError(
            "video_caption_parse_failed", category="empty_caption_track", retriable=True
        )
    frames = _adapter_frames(adapter, source_url, required=True)
    markdown = render_video_markdown(segments, frames, video_id=video_id)
    return VideoAcquisition(
        route="uploaded_caption",
        language=caption.language,
        segments=segments,
        markdown=markdown,
        content_hash=_video_evidence_hash(segments, frames),
        preflight_id=preflight["id"],
        source_url=source_url,
        raw_vtt=caption.vtt,
        raw_vtt_bytes=caption.raw_bytes or caption.vtt.encode("utf-8"),
        frames=frames,
        frame_extractor=FRAME_EXTRACTION_VERSION if frames else None,
    )


def persist_video_transcript(
    conn: psycopg.Connection,
    *,
    job: dict[str, Any],
    snapshot_id: str,
    artifact_id: str,
    acquisition: VideoAcquisition,
) -> str | None:
    if not acquisition.segments:
        return None
    transcript_id = f"vt-{job['id']}"
    if acquisition.raw_vtt is not None:
        conn.execute(
            "INSERT INTO video_caption_evidence"
            " (id, acquisition_job_id, source_id, snapshot_id, preflight_id,"
            " language, source_url, vtt_sha256, vtt_body, vtt_bytes)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (acquisition_job_id) DO NOTHING",
            (
                f"vce-{job['id']}", job["id"], job["source_id"], snapshot_id,
                acquisition.preflight_id, acquisition.language,
                acquisition.source_url,
                hashlib.sha256(
                    acquisition.raw_vtt_bytes or acquisition.raw_vtt.encode("utf-8")
                ).hexdigest(),
                acquisition.raw_vtt,
                acquisition.raw_vtt_bytes or acquisition.raw_vtt.encode("utf-8"),
            ),
        )
    conn.execute(
        "INSERT INTO video_transcript"
        " (id, acquisition_job_id, source_id, snapshot_id, route, language,"
        " grouping_version, segment_count, content_hash, markdown_artifact_id,"
        " visual_analysis, metadata)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (acquisition_job_id) DO NOTHING",
        (
            transcript_id, job["id"], job["source_id"], snapshot_id,
            acquisition.route, acquisition.language, GROUPING_VERSION,
            len(acquisition.segments), acquisition.content_hash, artifact_id,
            "pending" if acquisition.frames else "deferred",
            Jsonb({"source_url": acquisition.source_url}),
        ),
    )
    for seq, segment in enumerate(acquisition.segments, 1):
        conn.execute(
            "INSERT INTO video_transcript_segment"
            " (transcript_id, seq, start_ms, end_ms, text, source_kind, source_ref)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (transcript_id, seq) DO NOTHING",
            (
                transcript_id, seq, segment.start_ms, segment.end_ms,
                segment.text,
                "caption_cue" if acquisition.route == "uploaded_caption" else "stt_chunk",
                segment.source_ref,
            ),
        )
    return transcript_id


class SummarizeYouTubeAdapter:
    """Hermetic Summarize CLI Adapter for timestamped candidate frames."""

    def __init__(
        self,
        executable: str | None = None,
        *,
        runner=None,
        temporary_root: str | Path | None = None,
        slides_max: int = 20,
        runtime_tools: Mapping[str, str] | None = None,
    ) -> None:
        local_executable = (
            Path(__file__).resolve().parents[3]
            / "node_modules"
            / ".bin"
            / "summarize"
        )
        self.executable = (
            executable
            or (str(local_executable) if local_executable.is_file() else None)
            or shutil.which("summarize")
        )
        self.runner = runner or subprocess.run
        self.temporary_root = Path(temporary_root) if temporary_root else None
        self.slides_max = min(20, max(1, int(slides_max)))
        self.runtime_tools = (
            dict(runtime_tools) if runtime_tools is not None else None
        )

    def _require(self) -> str:
        if not self.executable:
            raise VideoAdapterError(
                "video_frame_extraction_unavailable",
                category="summarize_unavailable",
                retriable=False,
            )
        return self.executable

    def _hermetic_runtime_path(self, temporary_home: Path) -> str:
        required = ("node", "yt-dlp", "ffmpeg", "ffprobe")
        resolved = (
            self.runtime_tools
            if self.runtime_tools is not None
            else {name: path for name in required if (path := shutil.which(name))}
        )
        missing = [name for name in required if not resolved.get(name)]
        if missing:
            raise VideoAdapterError(
                "video_frame_extraction_unavailable",
                category="summarize_runtime_dependency_missing",
                retriable=False,
                diagnostics={"missing": missing},
            )
        runtime_bin = temporary_home / "runtime-bin"
        runtime_bin.mkdir(mode=0o700)
        for name in required:
            target = Path(str(resolved[name])).resolve()
            if not target.is_file() or not os.access(target, os.X_OK):
                raise VideoAdapterError(
                    "video_frame_extraction_unavailable",
                    category="summarize_runtime_dependency_missing",
                    retriable=False,
                    diagnostics={"missing": [name]},
                )
            (runtime_bin / name).symlink_to(target)
        return str(runtime_bin)

    @staticmethod
    def _hermetic_environment(
        temporary_home: Path, *, runtime_path: str
    ) -> dict[str, str]:
        # The dedicated `slides` command never enters transcript selection.
        # A blank home, stripped credentials and a four-tool PATH additionally
        # keep cloud, ONNX and whisper.cpp transcription undiscoverable.
        allowed = {
            "TMPDIR",
            "LANG",
            "LC_ALL",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "NODE_EXTRA_CA_CERTS",
        }
        environment = {
            key: value for key, value in os.environ.items() if key in allowed
        }
        environment.update(
            {
                "HOME": str(temporary_home),
                "XDG_CONFIG_HOME": str(temporary_home / "config"),
                "XDG_CACHE_HOME": str(temporary_home / "cache"),
                "PATH": runtime_path,
                "NO_COLOR": "1",
                "SUMMARIZE_WHISPER_CPP_BINARY": str(
                    temporary_home / "transcription-disabled"
                ),
            }
        )
        return environment

    def extract_frames(self, source_url: str) -> tuple[VideoFrame, ...]:
        with tempfile.TemporaryDirectory(
            prefix="concept-universe-video-frames-",
            dir=str(self.temporary_root) if self.temporary_root else None,
        ) as directory:
            slides_dir = Path(directory).resolve()
            runtime_path = self._hermetic_runtime_path(slides_dir)
            command = [
                self._require(),
                "slides",
                source_url,
                "--slides-max",
                str(self.slides_max),
                "--no-cache",
                "--slides-dir",
                str(slides_dir),
                "--timeout",
                "10m",
                "--render",
                "none",
                "--json",
            ]
            try:
                result = self.runner(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=660,
                    env=self._hermetic_environment(
                        slides_dir, runtime_path=runtime_path
                    ),
                    cwd=slides_dir,
                )
                payload = json.loads(result.stdout)
            except VideoAdapterError:
                raise
            except subprocess.TimeoutExpired as exc:
                raise VideoAdapterError(
                    "video_frame_extraction_failed",
                    category="summarize_timeout",
                    retriable=True,
                ) from exc
            except subprocess.CalledProcessError as exc:
                raise VideoAdapterError(
                    "video_frame_extraction_failed",
                    category="summarize_failed",
                    retriable=True,
                    diagnostics={"returncode": exc.returncode},
                ) from exc
            except OSError as exc:
                raise VideoAdapterError(
                    "video_frame_extraction_unavailable",
                    category="summarize_spawn_failed",
                    retriable=False,
                ) from exc
            except (json.JSONDecodeError, TypeError, AttributeError) as exc:
                raise VideoAdapterError(
                    "video_frame_extraction_failed",
                    category="summarize_invalid_json",
                    retriable=True,
                ) from exc

            if not isinstance(payload, dict) or payload.get("ok") is not True:
                raise VideoAdapterError(
                    "video_frame_extraction_failed",
                    category="summarize_invalid_json",
                    retriable=True,
                )
            slide_payload = payload.get("slides")
            if not isinstance(slide_payload, dict):
                raise VideoAdapterError(
                    "video_frame_extraction_failed",
                    category="summarize_invalid_json",
                    retriable=True,
                )
            raw_slides = slide_payload.get("slides")
            expected_video_id_match = re.search(
                r"(?:[?&]v=|youtu\.be/)([A-Za-z0-9_-]+)", source_url
            )
            expected_video_id = (
                expected_video_id_match.group(1) if expected_video_id_match else None
            )
            observed_source_id = str(slide_payload.get("sourceId") or "")
            if (
                not expected_video_id
                or not observed_source_id
                or observed_source_id
                not in {expected_video_id, f"youtube-{expected_video_id}"}
            ):
                raise VideoAdapterError(
                    "video_frame_extraction_failed",
                    category="summarize_source_mismatch",
                    retriable=False,
                )
            if not isinstance(raw_slides, list):
                raise VideoAdapterError(
                    "video_frame_extraction_failed",
                    category="summarize_invalid_json",
                    retriable=True,
                )
            frames: list[VideoFrame] = []
            seen_indices: set[int] = set()
            for item in raw_slides:
                if not isinstance(item, dict):
                    raise VideoAdapterError(
                        "video_frame_extraction_failed",
                        category="summarize_invalid_slide",
                        retriable=True,
                    )
                try:
                    index = int(item["index"])
                    timestamp = float(item["timestamp"])
                    candidate = Path(str(item["imagePath"]))
                except (KeyError, TypeError, ValueError):
                    raise VideoAdapterError(
                        "video_frame_extraction_failed",
                        category="summarize_invalid_slide",
                        retriable=True,
                    )
                if (
                    index <= 0
                    or index in seen_indices
                    or not math.isfinite(timestamp)
                    or timestamp < 0
                ):
                    raise VideoAdapterError(
                        "video_frame_extraction_failed",
                        category="summarize_invalid_slide",
                        retriable=True,
                    )
                seen_indices.add(index)
                path = (
                    candidate.resolve()
                    if candidate.is_absolute()
                    else (slides_dir / candidate).resolve()
                )
                if not path.is_relative_to(slides_dir) or not path.is_file():
                    raise VideoAdapterError(
                        "video_frame_extraction_failed",
                        category="summarize_frame_path_invalid",
                        retriable=False,
                    )
                if path.suffix.lower() != ".png":
                    raise VideoAdapterError(
                        "video_frame_extraction_failed",
                        category="summarize_frame_type_invalid",
                        retriable=True,
                    )
                mime_type = "image/png"
                body = path.read_bytes()
                if not body:
                    raise VideoAdapterError(
                        "video_frame_extraction_failed",
                        category="summarize_frame_empty",
                        retriable=True,
                    )
                frames.append(
                    VideoFrame(
                        timestamp_ms=int(round(timestamp * 1000)),
                        body=body,
                        mime_type=mime_type,
                        filename=path.name,
                    )
                )
            frames = list(_dedupe_frames(tuple(frames)))
            if not frames:
                raise VideoAdapterError(
                    "video_frame_extraction_empty",
                    category="summarize_returned_no_frames",
                    retriable=True,
                )
            return tuple(frames)


class YtDlpYouTubeAdapter:
    """Live YouTube Adapter composed from yt-dlp and Summarize."""

    def __init__(
        self,
        executable: str | None = None,
        *,
        ffmpeg_path: str | None = None,
        ffprobe_path: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        stt_transport=None,
        stt_timeout_seconds: int | None = None,
        stt_workers: int | None = None,
        frame_adapter: SummarizeYouTubeAdapter | None = None,
        caption_probe_transport=None,
        teaching_beat_adapter: TeachingBeatAdapter | None = None,
    ) -> None:
        self.executable = executable or shutil.which("yt-dlp")
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        self.ffprobe_path = ffprobe_path or shutil.which("ffprobe")
        self.api_key = api_key or openrouter_api_key()
        self.base_url = (
            base_url
            or os.environ.get("MODEL_API_BASE", "").strip()
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.stt_transport = stt_transport or self._post_stt
        self.stt_timeout_seconds = max(
            1, stt_timeout_seconds or video_stt_timeout_seconds()
        )
        self.stt_workers = max(1, stt_workers or video_stt_workers())
        self.frame_adapter = frame_adapter
        self.caption_probe_transport = (
            caption_probe_transport or self._fetch_caption_probe
        )
        self.teaching_beat_adapter = teaching_beat_adapter

    def _require(self) -> str:
        if not self.executable:
            raise VideoAdapterError(
                "video_metadata_unavailable",
                category="yt_dlp_unavailable",
                retriable=False,
            )
        return self.executable

    def extract_frames(self, source_url: str) -> tuple[VideoFrame, ...]:
        adapter = self.frame_adapter or SummarizeYouTubeAdapter()
        return adapter.extract_frames(source_url)

    def acquire_visual_teaching_beats(
        self, source_url: str, *, duration_seconds: float | None
    ) -> TeachingBeatDocument:
        adapter = self.teaching_beat_adapter
        if adapter is None:
            adapter = OpenRouterGeminiTeachingBeatAdapter(
                client=ModelClient(
                    video_teaching_beat_model(),
                    api_base=self.base_url,
                    api_key=self.api_key,
                    temperature=0,
                    max_tokens=65_536,
                    extra={
                        "provider": openrouter_video_provider_routing()
                    },
                ),
                frame_materializer=YtDlpTeachingBeatFrameMaterializer(
                    executable=self.executable,
                    ffmpeg_path=self.ffmpeg_path,
                ),
            )
        return adapter.acquire_visual_teaching_beats(
            source_url, duration_seconds=duration_seconds
        )

    @staticmethod
    def _fetch_caption_probe(url: str) -> bytes:
        parsed = httpx.URL(url)
        host = (parsed.host or "").lower()
        if parsed.scheme != "https" or not (
            host == "youtube.com" or host.endswith(".youtube.com")
        ):
            raise ValueError("speech probe URL is not a YouTube HTTPS URL")
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        if len(response.content) > 2 * 1024 * 1024:
            raise ValueError("speech probe response is too large")
        return response.content

    def _speech_probe(self, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        base = {"version": SPEECH_PROBE_VERSION}
        formats = payload.get("formats")
        if isinstance(formats, list) and formats and not any(
            isinstance(item, dict)
            and item.get("acodec") not in {None, "none"}
            for item in formats
        ):
            return "absent", {
                **base,
                "status": "absent",
                "reason": "no_audio_stream",
                "cue_count": 0,
            }
        catalog = payload.get("automatic_captions")
        if not isinstance(catalog, dict):
            return "unknown", {
                **base,
                "status": "unknown",
                "reason": "original_auto_caption_unavailable",
            }
        original_languages = sorted(
            key
            for key in catalog
            if isinstance(key, str) and key.endswith("-orig")
        )
        if len(original_languages) != 1:
            return "unknown", {
                **base,
                "status": "unknown",
                "reason": "original_auto_caption_unavailable",
            }
        language = original_languages[0]
        tracks = catalog.get(language)
        vtt_url = next(
            (
                str(item.get("url"))
                for item in tracks
                if isinstance(item, dict)
                and item.get("ext") == "vtt"
                and isinstance(item.get("url"), str)
            ),
            None,
        ) if isinstance(tracks, list) else None
        if not vtt_url:
            return "unknown", {
                **base,
                "status": "unknown",
                "reason": "original_auto_caption_unavailable",
                "language": language,
            }
        try:
            raw = self.caption_probe_transport(vtt_url)
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            if not isinstance(raw, bytes) or len(raw) > 2 * 1024 * 1024:
                raise ValueError("invalid speech probe body")
            cues = parse_vtt(raw.decode("utf-8", errors="replace"))
        except Exception as exc:
            return "unknown", {
                **base,
                "status": "unknown",
                "reason": "original_auto_caption_probe_failed",
                "language": language,
                "category": type(exc).__name__,
            }
        status = "present" if cues else "absent"
        return status, {
            **base,
            "status": status,
            "reason": "original_auto_caption",
            "language": language,
            "cue_count": len(cues),
        }

    def probe(self, source_url: str) -> VideoMetadata:
        try:
            result = subprocess.run(
                [
                    self._require(), "--dump-single-json", "--skip-download",
                    "--no-warnings", "--no-playlist", source_url,
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            payload = json.loads(result.stdout)
        except VideoAdapterError:
            raise
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
            raise VideoAdapterError(
                "video_metadata_unavailable",
                category=type(exc).__name__,
                retriable=True,
            ) from exc
        if not isinstance(payload, dict):
            raise VideoAdapterError(
                "video_metadata_unavailable", category="invalid_metadata", retriable=True
            )
        subtitles = payload.get("subtitles")
        languages = (
            tuple(str(key) for key in subtitles if isinstance(key, str))
            if isinstance(subtitles, dict)
            else ()
        )
        duration = payload.get("duration")
        if languages:
            speech_evidence = "present"
            speech_probe = {
                "version": SPEECH_PROBE_VERSION,
                "status": "present",
                "reason": "uploaded_caption",
            }
        else:
            speech_evidence, speech_probe = self._speech_probe(payload)
        return VideoMetadata(
            title=str(payload.get("title") or ""),
            channel=str(payload.get("channel") or payload.get("uploader") or "") or None,
            duration_seconds=float(duration) if isinstance(duration, (int, float)) else None,
            uploaded_caption_languages=languages,
            language=str(payload.get("language") or "") or None,
            speech_evidence=speech_evidence,
            speech_probe=speech_probe,
        )

    def download_uploaded_caption(
        self, source_url: str, *, language: str
    ) -> CaptionDownload:
        with tempfile.TemporaryDirectory(prefix="universe-youtube-caption-") as directory:
            output = Path(directory) / "caption"
            try:
                subprocess.run(
                    [
                        self._require(), "--skip-download", "--no-warnings",
                        "--no-playlist", "--write-subs", "--sub-langs", language,
                        "--sub-format", "vtt", "-o", str(output), source_url,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                )
            except VideoAdapterError:
                raise
            except (subprocess.SubprocessError, OSError) as exc:
                raise VideoAdapterError(
                    "video_caption_download_failed",
                    category=type(exc).__name__,
                    retriable=True,
                ) from exc
            candidates = sorted(Path(directory).glob("caption*.vtt"))
            if not candidates:
                raise VideoAdapterError(
                    "video_caption_download_failed",
                    category="caption_file_missing",
                    retriable=True,
                )
            raw_bytes = candidates[0].read_bytes()
            return CaptionDownload(
                language=language,
                vtt=raw_bytes.decode("utf-8", errors="replace"),
                raw_bytes=raw_bytes,
            )

    @contextmanager
    def prepare_audio(
        self, source_url: str, *, chunk_seconds: int
    ):
        """Yield deterministic bounded MP3 chunks and always remove them."""
        if not self.ffmpeg_path or not self.ffprobe_path:
            raise VideoAdapterError(
                "video_ffmpeg_unavailable",
                category="ffmpeg_or_ffprobe_unavailable",
                retriable=False,
            )
        with tempfile.TemporaryDirectory(prefix="universe-youtube-audio-") as directory:
            root = Path(directory)
            template = root / "input.%(ext)s"
            try:
                subprocess.run(
                    [
                        self._require(),
                        "--no-playlist",
                        "--no-warnings",
                        "-f",
                        "bestaudio/best",
                        "-o",
                        str(template),
                        source_url,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=900,
                )
            except VideoAdapterError:
                raise
            except subprocess.TimeoutExpired as exc:
                raise VideoAdapterError(
                    "video_audio_download_failed",
                    category="yt_dlp_timeout",
                    retriable=True,
                ) from exc
            except (subprocess.CalledProcessError, OSError) as exc:
                raise VideoAdapterError(
                    "video_audio_download_failed",
                    category=type(exc).__name__,
                    retriable=True,
                ) from exc
            source_paths = sorted(
                path
                for path in root.glob("input.*")
                if path.is_file() and not path.name.endswith((".part", ".ytdl"))
            )
            if not source_paths:
                raise VideoAdapterError(
                    "video_audio_download_failed",
                    category="audio_file_missing",
                    retriable=True,
                )
            chunks_dir = root / "chunks"
            chunks_dir.mkdir()
            pattern = chunks_dir / "chunk-%05d.mp3"
            try:
                subprocess.run(
                    [
                        self.ffmpeg_path,
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-i",
                        str(source_paths[0]),
                        "-map",
                        "0:a:0",
                        "-f",
                        "segment",
                        "-segment_time",
                        str(max(1, chunk_seconds)),
                        "-reset_timestamps",
                        "1",
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        "-c:a",
                        "libmp3lame",
                        "-b:a",
                        "64k",
                        "-map_metadata",
                        "-1",
                        str(pattern),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=900,
                )
            except subprocess.TimeoutExpired as exc:
                raise VideoAdapterError(
                    "video_ffmpeg_failed",
                    category="ffmpeg_timeout",
                    retriable=True,
                ) from exc
            except (subprocess.CalledProcessError, OSError) as exc:
                raise VideoAdapterError(
                    "video_ffmpeg_failed",
                    category=type(exc).__name__,
                    retriable=True,
                ) from exc
            paths = sorted(chunks_dir.glob("chunk-*.mp3"))
            if not paths:
                raise VideoAdapterError(
                    "video_ffmpeg_failed",
                    category="audio_chunks_missing",
                    retriable=True,
                )
            chunks = []
            offset_ms = 0
            hashes = []
            for ordinal, path in enumerate(paths, 1):
                try:
                    probe = subprocess.run(
                        [
                            self.ffprobe_path,
                            "-v",
                            "error",
                            "-show_entries",
                            "format=duration",
                            "-of",
                            "default=noprint_wrappers=1:nokey=1",
                            str(path),
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=60,
                    )
                    duration_ms = round(float(probe.stdout.strip()) * 1000)
                except (subprocess.SubprocessError, OSError, ValueError) as exc:
                    raise VideoAdapterError(
                        "video_ffmpeg_failed",
                        category="ffprobe_failed",
                        retriable=True,
                    ) from exc
                if duration_ms <= 0:
                    raise VideoAdapterError(
                        "video_ffmpeg_failed",
                        category="empty_audio_chunk",
                        retriable=True,
                    )
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                hashes.append(digest)
                chunks.append(
                    AudioChunk(
                        ordinal,
                        offset_ms,
                        offset_ms + duration_ms,
                        digest,
                        path,
                    )
                )
                offset_ms += duration_ms
            audio_sha256 = hashlib.sha256("".join(hashes).encode()).hexdigest()
            yield PreparedAudio(audio_sha256, offset_ms, tuple(chunks))

    @staticmethod
    def _post_stt(url, headers, payload, timeout):
        return httpx.post(url, headers=headers, json=payload, timeout=timeout)

    def transcribe_chunk(
        self, chunk: AudioChunk, *, model: str, language: str | None
    ) -> SttResponse:
        if not self.api_key:
            raise SttError(
                "video_stt_authentication_failed",
                fallback_allowed=False,
                diagnostics={"category": "missing_credentials"},
            )
        started = time.monotonic()
        try:
            audio = chunk.path.read_bytes()
        except OSError as exc:
            raise SttError(
                "video_ffmpeg_failed",
                fallback_allowed=False,
                diagnostics={"category": type(exc).__name__},
            ) from exc
        payload: dict[str, Any] = {
            "model": model,
            "input_audio": {
                "data": base64.b64encode(audio).decode("ascii"),
                "format": "mp3",
            },
            "temperature": 0,
            "response_format": "verbose_json",
            "timestamp_granularities": ["segment"],
        }
        if language:
            payload["language"] = language
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            raw = self.stt_transport(
                f"{self.base_url}/audio/transcriptions",
                headers,
                payload,
                self.stt_timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.TransportError, OSError) as exc:
            raise SttError(
                "video_stt_provider_failure",
                fallback_allowed=True,
                diagnostics={"category": type(exc).__name__},
                duration_ms=round((time.monotonic() - started) * 1000),
            ) from exc

        if isinstance(raw, httpx.Response):
            if raw.status_code >= 400:
                status = raw.status_code
                if status in {401, 403}:
                    code = "video_stt_authentication_failed"
                    fallback_allowed = False
                elif status == 429:
                    code = "video_stt_rate_limited"
                    fallback_allowed = True
                elif status in {404, 408, 425, 500, 502, 503, 504, 529}:
                    code = "video_stt_provider_failure"
                    fallback_allowed = True
                else:
                    code = "video_stt_provider_failure"
                    fallback_allowed = False
                raise SttError(
                    code,
                    fallback_allowed=fallback_allowed,
                    diagnostics={"category": "http_error", "http_status": status},
                    duration_ms=round((time.monotonic() - started) * 1000),
                )
            try:
                decoded = raw.json()
            except ValueError as exc:
                raise SttError(
                    "video_stt_provider_failure",
                    fallback_allowed=True,
                    diagnostics={"category": "invalid_json"},
                    duration_ms=round((time.monotonic() - started) * 1000),
                ) from exc
        else:
            decoded = raw
        if not isinstance(decoded, dict):
            raise SttError(
                "video_stt_provider_failure",
                fallback_allowed=True,
                diagnostics={"category": "non_object_response"},
                duration_ms=round((time.monotonic() - started) * 1000),
            )
        segments = []
        raw_segments = decoded.get("segments")
        if isinstance(raw_segments, list):
            for item in raw_segments:
                if not isinstance(item, dict) or not str(item.get("text") or "").strip():
                    continue
                start = item.get("start")
                end = item.get("end")
                if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
                    continue
                if start < 0 or end < start:
                    continue
                segments.append(
                    SttSegment(
                        round(float(start) * 1000),
                        round(float(end) * 1000),
                        " ".join(str(item["text"]).split()),
                    )
                )
        usage = decoded.get("usage")
        return SttResponse(
            text=" ".join(str(decoded.get("text") or "").split()),
            language=str(decoded.get("language") or "") or None,
            segments=tuple(segments),
            response_model=str(decoded.get("model") or "") or None,
            provider=str(decoded.get("provider") or "openrouter"),
            usage=usage if isinstance(usage, dict) else {},
            duration_ms=round((time.monotonic() - started) * 1000),
            generation_id=str(decoded.get("id") or "") or None,
        )
