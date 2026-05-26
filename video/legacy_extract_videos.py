#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
from typing import Any, Protocol
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv


DEFAULT_VIDEO_WORKER_COUNT = 6
DEFAULT_STT_WORKER_COUNT = 2
DEFAULT_FRAME_INTERVAL_SECONDS = 2.0
DEFAULT_MAX_OCR_FRAMES = 240


def _load_pipeline_env() -> None:
    script_path = Path(__file__).resolve()
    load_dotenv(script_path.parents[1] / ".env")
    load_dotenv(script_path.parents[2] / ".env")


class VideoExtractionFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retriable: bool = False,
        terminal: bool = False,
        unavailable: bool = False,
    ) -> None:
        super().__init__(message)
        self.retriable = retriable
        self.terminal = terminal
        self.unavailable = unavailable


@dataclass(frozen=True)
class VideoRef:
    id: str
    title: str
    url: str


@dataclass(frozen=True)
class VideoTranscriptSegment:
    text: str
    start_seconds: float | None = None
    duration_seconds: float | None = None


@dataclass(frozen=True)
class VideoTranscriptResponse:
    final_url: str
    title: str
    transcript_source: str
    caption_language: str = ""
    duration_seconds: float | None = None
    segments: list[VideoTranscriptSegment] = field(default_factory=list)
    raw_captions: str = ""
    stt_model: str = ""
    audio_manifest: dict[str, Any] | None = None
    video_ocr_manifest: dict[str, Any] | None = None


@dataclass(frozen=True)
class AppleVisionOcrResult:
    text: str
    average_confidence: float | None = None
    line_count: int = 0


@dataclass
class Result:
    video_id: str
    title: str
    url: str
    status: str
    output_path: str | None = None
    manifest_path: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    transcript_source: str = ""
    segment_count: int = 0
    word_count: int = 0


class VideoCaptionFetcher(Protocol):
    def fetch(
        self,
        url: str,
        *,
        preferred_languages: list[str],
    ) -> VideoTranscriptResponse:
        raise NotImplementedError


class VideoSttRunner(Protocol):
    def transcribe(
        self,
        url: str,
        *,
        artifact_dir: Path,
        preferred_languages: list[str],
    ) -> VideoTranscriptResponse:
        raise NotImplementedError


class VideoOcrRunner(Protocol):
    def extract(
        self,
        url: str,
        *,
        artifact_dir: Path,
        preferred_languages: list[str],
    ) -> VideoTranscriptResponse:
        raise NotImplementedError


class YtDlpCaptionFetcher:
    def fetch(
        self,
        url: str,
        *,
        preferred_languages: list[str],
    ) -> VideoTranscriptResponse:
        info = _extract_ytdlp_info(url)
        manual_caption = _select_caption_track(
            info.get("subtitles", {}),
            preferred_languages,
        )
        if manual_caption is None:
            raise VideoExtractionFailure(
                "No manual YouTube captions available",
                unavailable=True,
            )

        raw_captions = _download_text(_caption_url_as_vtt(manual_caption["url"]))
        segments = _segments_from_caption_payload(raw_captions)
        if not segments:
            segments = _segments_from_plain_text(_plain_text_from_captions(raw_captions))
        return VideoTranscriptResponse(
            final_url=str(info.get("webpage_url") or info.get("original_url") or url),
            title=str(info.get("title") or ""),
            transcript_source="manual_captions",
            caption_language=str(manual_caption.get("language") or ""),
            duration_seconds=_optional_float(info.get("duration")),
            segments=segments,
            raw_captions=raw_captions,
        )


class LocalWhisperRunner:
    def __init__(
        self,
        *,
        binary_path: str | None = None,
        model_path: str | None = None,
    ) -> None:
        _load_pipeline_env()
        self.binary_path = (
            binary_path
            or os.environ.get("CG_PIPELINE_WHISPER_CPP_BINARY", "").strip()
            or _first_existing_path(["~/.local/bin/whisper-cli"])
            or _first_existing_command(["whisper-cli", "whisper-cpp", "main"])
        )
        self.model_path = (
            model_path
            or os.environ.get("CG_PIPELINE_WHISPER_MODEL", "").strip()
            or _first_existing_path(
                [
                    "~/.local/share/whisper.cpp/models/ggml-large-v3-turbo-q5_0.bin",
                    "~/.local/share/whisper.cpp/models/ggml-large-v3-q5_0.bin",
                    "~/Models/whisper/ggml-large-v3-turbo-q5_0.bin",
                    "~/.cache/whisper.cpp/ggml-large-v3-turbo-q5_0.bin",
                    "./models/ggml-large-v3-turbo-q5_0.bin",
                ]
            )
        )
        self.extra_args = shlex.split(
            os.environ.get("CG_PIPELINE_WHISPER_CPP_EXTRA_ARGS", "").strip()
        )

    def transcribe(
        self,
        url: str,
        *,
        artifact_dir: Path,
        preferred_languages: list[str],
    ) -> VideoTranscriptResponse:
        return self._transcribe(
            url,
            artifact_dir=artifact_dir,
            preferred_languages=preferred_languages,
            stt_semaphore=None,
        )

    def transcribe_with_semaphore(
        self,
        url: str,
        *,
        artifact_dir: Path,
        preferred_languages: list[str],
        stt_semaphore: threading.Semaphore | None,
    ) -> VideoTranscriptResponse:
        return self._transcribe(
            url,
            artifact_dir=artifact_dir,
            preferred_languages=preferred_languages,
            stt_semaphore=stt_semaphore,
        )

    def _transcribe(
        self,
        url: str,
        *,
        artifact_dir: Path,
        preferred_languages: list[str],
        stt_semaphore: threading.Semaphore | None,
    ) -> VideoTranscriptResponse:
        del preferred_languages
        if not self.binary_path:
            raise VideoExtractionFailure(
                "Local Whisper unavailable: whisper.cpp binary not found",
                unavailable=True,
            )
        if not self.model_path:
            raise VideoExtractionFailure(
                "Local Whisper unavailable: model file not found",
                unavailable=True,
            )
        yt_dlp_command = _yt_dlp_command()
        if not yt_dlp_command:
            raise VideoExtractionFailure(
                "Local Whisper unavailable: yt-dlp command not found",
                unavailable=True,
            )

        artifact_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="video_audio_", dir=artifact_dir) as temp:
            temp_dir = Path(temp)
            audio_template = temp_dir / "audio.%(ext)s"
            try:
                subprocess.run(
                    [
                        *yt_dlp_command,
                        "--no-playlist",
                        "-x",
                        "--audio-format",
                        "wav",
                        "-o",
                        str(audio_template),
                        url,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=900,
                )
            except subprocess.TimeoutExpired as exc:
                raise VideoExtractionFailure(
                    "Timed out extracting YouTube audio for local Whisper",
                    retriable=True,
                ) from exc
            except subprocess.CalledProcessError as exc:
                raise _video_failure_from_message(
                    "yt-dlp audio extraction failed",
                    f"{exc.stderr}\n{exc.stdout}",
                ) from exc

            audio_paths = sorted(temp_dir.glob("audio.*"))
            if not audio_paths:
                raise VideoExtractionFailure(
                    "yt-dlp did not produce audio for local Whisper",
                    unavailable=True,
                )
            output_base = temp_dir / "whisper_transcript"
            whisper_command = [
                self.binary_path,
                *self.extra_args,
                "-m",
                self.model_path,
                "-f",
                str(audio_paths[0]),
                "-l",
                "auto",
                "-otxt",
                "-of",
                str(output_base),
            ]
            try:
                completed = _run_whisper_command(
                    whisper_command,
                    stt_semaphore=stt_semaphore,
                )
            except subprocess.TimeoutExpired as exc:
                raise VideoExtractionFailure(
                    "Timed out running local Whisper transcription",
                    retriable=True,
                ) from exc
            except subprocess.CalledProcessError as exc:
                if _should_retry_whisper_without_gpu(exc) and "--no-gpu" not in whisper_command:
                    retry_command = [whisper_command[0], "--no-gpu", *whisper_command[1:]]
                    try:
                        completed = _run_whisper_command(
                            retry_command,
                            stt_semaphore=stt_semaphore,
                        )
                    except subprocess.TimeoutExpired as retry_exc:
                        raise VideoExtractionFailure(
                            "Timed out running local Whisper transcription",
                            retriable=True,
                        ) from retry_exc
                    except subprocess.CalledProcessError as retry_exc:
                        raise VideoExtractionFailure(
                            "Local Whisper transcription failed after CPU retry: "
                            f"{retry_exc.stderr or retry_exc.stdout}",
                            retriable=True,
                        ) from retry_exc
                else:
                    raise VideoExtractionFailure(
                        f"Local Whisper transcription failed: {exc.stderr or exc.stdout}",
                        retriable=True,
                    ) from exc

            transcript_path = output_base.with_suffix(".txt")
            if transcript_path.exists():
                transcript_text = transcript_path.read_text(encoding="utf-8").strip()
            else:
                transcript_text = completed.stdout.strip()
            if not transcript_text:
                raise VideoExtractionFailure(
                    "Local Whisper returned an empty transcript",
                    retriable=True,
                )
            return VideoTranscriptResponse(
                final_url=url,
                title="",
                transcript_source="local_whisper",
                segments=_segments_from_plain_text(transcript_text),
                stt_model=Path(self.model_path).name,
                audio_manifest={
                    "cached_audio": False,
                    "audio_retained": False,
                    "audio_policy": (
                        "Audio is extracted as an intermediate and deleted after "
                        "transcription; replay uses the cached transcript bundle."
                    ),
                    "extraction_tool": "yt-dlp",
                    "stt_tool": self.binary_path,
                    "stt_extra_args": self.extra_args,
                    "stt_model": Path(self.model_path).name,
                },
            )


def _run_whisper_command(
    whisper_command: list[str],
    *,
    stt_semaphore: threading.Semaphore | None,
) -> subprocess.CompletedProcess[str]:
    if stt_semaphore is None:
        return subprocess.run(
            whisper_command,
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
        )
    with stt_semaphore:
        return subprocess.run(
            whisper_command,
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
        )


def _should_retry_whisper_without_gpu(exc: subprocess.CalledProcessError) -> bool:
    output = f"{exc.stderr or ''}\n{exc.stdout or ''}".lower()
    return (
        "ggml_metal_buffer_init" in output
        or "failed to allocate buffer" in output
        or "whisper_backend_init_gpu: no gpu found" in output
    )


class LocalVideoOcrRunner:
    def __init__(
        self,
        *,
        ffmpeg_path: str | None = None,
        frame_interval_seconds: float | None = None,
        recognition_languages: list[str] | None = None,
        max_frames: int | None = None,
    ) -> None:
        _load_pipeline_env()
        self.ffmpeg_path = (
            ffmpeg_path
            or os.environ.get("CG_PIPELINE_FFMPEG_BINARY", "").strip()
            or _first_existing_command(["ffmpeg"])
        )
        env_frame_interval = _optional_float(
            os.environ.get("CG_PIPELINE_VIDEO_OCR_FRAME_INTERVAL")
        )
        self.frame_interval_seconds = max(
            0.5,
            frame_interval_seconds
            if frame_interval_seconds is not None
            else env_frame_interval or DEFAULT_FRAME_INTERVAL_SECONDS,
        )
        self.recognition_languages = (
            recognition_languages or _configured_apple_vision_languages()
        )
        self.recognition_level = (
            os.environ.get("CG_PIPELINE_APPLE_VISION_RECOGNITION_LEVEL", "").strip()
            or "accurate"
        )
        self.max_frames = (
            max(1, max_frames)
            if max_frames is not None
            else _optional_int(
                os.environ.get("CG_PIPELINE_VIDEO_OCR_MAX_FRAMES"),
                default=DEFAULT_MAX_OCR_FRAMES,
            )
        )

    def extract(
        self,
        url: str,
        *,
        artifact_dir: Path,
        preferred_languages: list[str],
    ) -> VideoTranscriptResponse:
        if not self.ffmpeg_path:
            raise VideoExtractionFailure(
                "Local video OCR unavailable: ffmpeg command not found",
                unavailable=True,
            )
        yt_dlp_command = _yt_dlp_command()
        if not yt_dlp_command:
            raise VideoExtractionFailure(
                "Local video OCR unavailable: yt-dlp command not found",
                unavailable=True,
            )
        ocrmac_module = _load_ocrmac()
        recognition_languages = (
            self.recognition_languages
            or _apple_vision_languages_from_preferred(preferred_languages)
        )

        artifact_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="video_ocr_", dir=artifact_dir) as temp:
            temp_dir = Path(temp)
            video_template = temp_dir / "video.%(ext)s"
            try:
                subprocess.run(
                    [
                        *yt_dlp_command,
                        "--no-playlist",
                        "-f",
                        "best[height<=720]/best",
                        "-o",
                        str(video_template),
                        url,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=900,
                )
            except subprocess.TimeoutExpired as exc:
                raise VideoExtractionFailure(
                    "Timed out downloading video for local OCR",
                    retriable=True,
                ) from exc
            except subprocess.CalledProcessError as exc:
                raise _video_failure_from_message(
                    "yt-dlp video download failed",
                    f"{exc.stderr}\n{exc.stdout}",
                ) from exc

            video_paths = sorted(
                path
                for path in temp_dir.glob("video.*")
                if path.is_file() and not path.name.endswith(".part")
            )
            if not video_paths:
                raise VideoExtractionFailure(
                    "yt-dlp did not produce a video file for local OCR",
                    retriable=True,
                )

            frame_pattern = temp_dir / "frame_%05d.png"
            try:
                subprocess.run(
                    [
                        self.ffmpeg_path,
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        str(video_paths[0]),
                        "-vf",
                        f"fps=1/{self.frame_interval_seconds}",
                        "-frames:v",
                        str(self.max_frames),
                        str(frame_pattern),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=900,
                )
            except subprocess.TimeoutExpired as exc:
                raise VideoExtractionFailure(
                    "Timed out sampling video frames for local OCR",
                    retriable=True,
                ) from exc
            except subprocess.CalledProcessError as exc:
                raise VideoExtractionFailure(
                    f"ffmpeg frame sampling failed: {exc.stderr or exc.stdout}",
                    retriable=True,
                ) from exc

            frames = sorted(temp_dir.glob("frame_*.png"))
            if not frames:
                raise VideoExtractionFailure(
                    "ffmpeg did not produce frames for local OCR",
                    retriable=True,
                )

            segments: list[VideoTranscriptSegment] = []
            seen_frame_hashes: set[str] = set()
            accepted_texts: list[str] = []
            rejected_frame_count = 0
            duplicate_frame_count = 0
            duplicate_text_count = 0
            empty_text_count = 0
            for index, frame_path in enumerate(frames):
                frame_hash = sha256(frame_path.read_bytes()).hexdigest()
                if frame_hash in seen_frame_hashes:
                    duplicate_frame_count += 1
                    rejected_frame_count += 1
                    continue
                seen_frame_hashes.add(frame_hash)
                ocr_result = _run_apple_vision_ocr(
                    ocrmac_module,
                    frame_path,
                    recognition_languages=recognition_languages,
                    recognition_level=self.recognition_level,
                )
                normalized = _normalize_ocr_text(ocr_result.text)
                if not normalized:
                    empty_text_count += 1
                    rejected_frame_count += 1
                    continue
                if any(
                    _near_duplicate_ocr_text(normalized, existing)
                    for existing in accepted_texts
                ):
                    duplicate_text_count += 1
                    rejected_frame_count += 1
                    continue
                accepted_texts.append(normalized)
                segments.append(
                    VideoTranscriptSegment(
                        text=normalized,
                        start_seconds=round(index * self.frame_interval_seconds, 3),
                        duration_seconds=self.frame_interval_seconds,
                    )
                )

        if not segments:
            raise VideoExtractionFailure(
                "Local video OCR produced no usable on-screen text",
                unavailable=True,
            )

        return VideoTranscriptResponse(
            final_url=url,
            title="",
            transcript_source="video_ocr",
            segments=segments,
            video_ocr_manifest={
                "extraction_tool": "yt-dlp",
                "frame_sampling_tool": self.ffmpeg_path,
                "ocr_tool": "apple_vision_ocrmac",
                "ocr_languages_requested": recognition_languages,
                "ocr_languages_used": recognition_languages,
                "ocr_language_selection": (
                    "configured"
                    if self.recognition_languages
                    else f"preferred_languages:{','.join(preferred_languages)}"
                ),
                "recognition_level": self.recognition_level,
                "frame_interval_seconds": self.frame_interval_seconds,
                "sampled_frame_count": len(frames),
                "accepted_frame_count": len(segments),
                "rejected_frame_count": rejected_frame_count,
                "duplicate_frame_count": duplicate_frame_count,
                "duplicate_text_count": duplicate_text_count,
                "empty_text_count": empty_text_count,
                "max_frames": self.max_frames,
                "policy": (
                    "Sample frames locally, skip exact duplicate frame files, OCR with "
                    "Apple Vision, and dedupe near-identical OCR text before writing "
                    "the normal transcript bundle."
                ),
            },
        )


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slugify(value: str, max_length: int = 90) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug[:max_length].rstrip("-") or "video")


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def yaml_frontmatter(data: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {yaml_scalar(item)}")
            else:
                lines.append(f"{key}: []")
        elif isinstance(value, dict):
            if value:
                lines.append(f"{key}:")
                for child_key, child_value in value.items():
                    lines.append(f"  {child_key}: {yaml_scalar(child_value)}")
            else:
                lines.append(f"{key}: {{}}")
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def parse_only_ids(value: str | None) -> set[str] | None:
    if not value:
        return None
    ids = {part.strip() for part in value.split(",") if part.strip()}
    if not ids:
        raise ValueError("--only must include at least one id")
    return ids


def load_videos(input_path: Path, only_ids: set[str] | None) -> tuple[list[VideoRef], set[str]]:
    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {input_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Input file is not valid JSON: {input_path}: {exc}") from exc

    if not isinstance(raw, list):
        raise SystemExit(f"Input JSON must be a list of objects: {input_path}")

    videos: list[VideoRef] = []
    seen_ids: set[str] = set()
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Input item #{idx} is not an object")
        missing = [key for key in ("id", "title", "url") if key not in item]
        if missing:
            raise SystemExit(f"Input item #{idx} is missing keys: {', '.join(missing)}")

        video_id = str(item["id"]).strip()
        title = str(item["title"]).strip()
        url = str(item["url"]).strip()
        if not video_id or not title or not url:
            raise SystemExit(f"Input item #{idx} has blank id, title, or url")
        if not _is_youtube_url(url):
            raise SystemExit(f"Input item #{idx} is not a YouTube URL: {url}")
        seen_ids.add(video_id)
        if only_ids is None or video_id in only_ids:
            videos.append(VideoRef(id=video_id, title=title, url=url))

    missing_requested = set()
    if only_ids is not None:
        missing_requested = only_ids - seen_ids
    return videos, missing_requested


def extract_video(
    video: VideoRef,
    *,
    output_root: Path,
    force: bool,
    caption_fetcher: VideoCaptionFetcher,
    stt_runner: VideoSttRunner,
    ocr_runner: VideoOcrRunner,
    stt_semaphore: threading.Semaphore | None = None,
) -> Result:
    video_dir = output_root / video.id
    manifest_path = video_dir / "source_manifest.json"
    if manifest_path.exists() and not force:
        try:
            manifest = _read_json(manifest_path)
        except (OSError, json.JSONDecodeError):
            manifest = {}
        return _result_from_manifest(
            video,
            manifest,
            status="skipped",
            output_dir=video_dir,
        )

    preferred_languages = _preferred_video_languages(video)
    failures: list[VideoExtractionFailure] = []
    fallback_warnings: list[str] = []

    for source_name, acquire in (
        (
            "captions",
            lambda: caption_fetcher.fetch(
                video.url,
                preferred_languages=preferred_languages,
            ),
        ),
        (
            "local_whisper",
            lambda: _transcribe_with_semaphore(
                stt_runner,
                video.url,
                artifact_dir=video_dir,
                preferred_languages=preferred_languages,
                stt_semaphore=stt_semaphore,
            ),
        ),
        (
            "video_ocr",
            lambda: ocr_runner.extract(
                video.url,
                artifact_dir=video_dir,
                preferred_languages=preferred_languages,
            ),
        ),
    ):
        try:
            response = acquire()
        except VideoExtractionFailure as exc:
            if source_name == "video_ocr" and exc.unavailable:
                fallback_warnings.append("video_ocr_unavailable")
            failures.append(
                VideoExtractionFailure(
                    f"{source_name}: {exc}",
                    retriable=exc.retriable,
                    terminal=exc.terminal,
                    unavailable=exc.unavailable,
                )
            )
            continue

        if not _transcript_text(response).strip():
            failures.append(
                VideoExtractionFailure(
                    f"{source_name}: transcript was empty",
                    unavailable=True,
                )
            )
            if source_name == "local_whisper":
                fallback_warnings.append("local_whisper_unusable")
            continue

        if source_name == "local_whisper":
            unusable_reasons = _local_whisper_unusable_reasons(response, video)
            if unusable_reasons:
                failures.append(
                    VideoExtractionFailure(
                        (
                            "local_whisper: unusable transcript "
                            f"({', '.join(unusable_reasons)})"
                        ),
                        unavailable=True,
                    )
                )
                fallback_warnings.append("local_whisper_unusable")
                continue

        manifest = _write_video_bundle(
            video,
            response,
            output_dir=video_dir,
            extra_warnings=fallback_warnings,
        )
        return _result_from_manifest(
            video,
            manifest,
            status="saved_with_warnings" if manifest.get("warnings") else "saved",
            output_dir=video_dir,
        )

    blocking_errors = [str(failure) for failure in failures]
    if any(failure.terminal for failure in failures):
        status = "failed_terminal"
    elif any(failure.retriable for failure in failures):
        status = "failed_retriable"
    else:
        status = "needs_manual"
    return Result(
        video_id=video.id,
        title=video.title,
        url=video.url,
        status=status,
        warnings=_dedupe_preserving_order(fallback_warnings),
        error="; ".join(blocking_errors) or "Video transcript acquisition unavailable",
    )


def _transcribe_with_semaphore(
    stt_runner: VideoSttRunner,
    url: str,
    *,
    artifact_dir: Path,
    preferred_languages: list[str],
    stt_semaphore: threading.Semaphore | None,
) -> VideoTranscriptResponse:
    transcribe_with_semaphore = getattr(stt_runner, "transcribe_with_semaphore", None)
    if callable(transcribe_with_semaphore):
        return transcribe_with_semaphore(
            url,
            artifact_dir=artifact_dir,
            preferred_languages=preferred_languages,
            stt_semaphore=stt_semaphore,
        )
    if stt_semaphore is None:
        return stt_runner.transcribe(
            url,
            artifact_dir=artifact_dir,
            preferred_languages=preferred_languages,
        )
    with stt_semaphore:
        return stt_runner.transcribe(
            url,
            artifact_dir=artifact_dir,
            preferred_languages=preferred_languages,
        )


def _write_video_bundle(
    video: VideoRef,
    response: VideoTranscriptResponse,
    *,
    output_dir: Path,
    extra_warnings: list[str] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    captured_at = iso_utc_now()
    transcript_text = _transcript_text(response)
    word_count = _word_count(transcript_text)
    title = response.title.strip() or video.title
    final_url = response.final_url.strip() or video.url
    warnings = _dedupe_preserving_order(
        [*(extra_warnings or []), *_video_warnings(response)]
    )

    markdown_path = output_dir / f"{video.id}-{slugify(video.title)}.md"
    metadata_path = output_dir / "metadata.json"
    transcript_json_path = output_dir / "transcript.json"
    manifest_path = output_dir / "source_manifest.json"

    metadata = {
        "id": video.id,
        "title": title,
        "source_url": video.url,
        "final_url": final_url,
        "transcript_source": response.transcript_source,
        "caption_language": response.caption_language,
        "duration_seconds": response.duration_seconds,
        "transcript_segment_count": len(response.segments),
        "stt_model": response.stt_model,
        "word_count": word_count,
        "warnings": warnings,
        "captured_at": captured_at,
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    metadata_path.write_text(metadata_json, encoding="utf-8")

    transcript_payload = {
        "schema_version": "1.0",
        "transcript_source": response.transcript_source,
        "caption_language": response.caption_language,
        "segments": [_segment_as_dict(segment) for segment in response.segments],
        "text": transcript_text,
    }
    transcript_json = json.dumps(transcript_payload, ensure_ascii=False, indent=2) + "\n"
    transcript_json_path.write_text(transcript_json, encoding="utf-8")

    frontmatter = {
        "id": video.id,
        "title": video.title,
        "source_url": video.url,
        "final_url": final_url,
        "resolved_title": title,
        "fetched_at": captured_at,
        "transcript_source": response.transcript_source,
        "caption_language": response.caption_language,
        "duration_seconds": response.duration_seconds,
        "segment_count": len(response.segments),
        "word_count": word_count,
        "content_sha256": sha256(transcript_text.encode("utf-8")).hexdigest(),
        "warnings": warnings,
    }
    markdown = f"{yaml_frontmatter(frontmatter)}\n\n# {title}\n\n{transcript_text.rstrip()}\n"
    markdown_path.write_text(markdown, encoding="utf-8")

    artifacts = {
        "markdown": markdown_path.name,
        "metadata": metadata_path.name,
        "transcript_json": transcript_json_path.name,
    }
    if response.raw_captions:
        captions_path = output_dir / "captions.vtt"
        captions_path.write_text(response.raw_captions, encoding="utf-8")
        artifacts["captions_vtt"] = captions_path.name
    if response.audio_manifest:
        audio_manifest_path = output_dir / "audio_manifest.json"
        audio_manifest_path.write_text(
            json.dumps(response.audio_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        artifacts["audio_manifest"] = audio_manifest_path.name
    if response.video_ocr_manifest:
        video_ocr_manifest_path = output_dir / "video_ocr_manifest.json"
        video_ocr_manifest_path.write_text(
            json.dumps(response.video_ocr_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        artifacts["video_ocr_manifest"] = video_ocr_manifest_path.name

    manifest = {
        "schema_version": "1.0",
        "id": video.id,
        "resource_kind": "video",
        "original_url": video.url,
        "final_url": final_url,
        "source_identity": {
            "title": title,
            "url": final_url,
        },
        "transcript_source": response.transcript_source,
        "caption_language": response.caption_language,
        "duration_seconds": response.duration_seconds,
        "transcript_segment_count": len(response.segments),
        "stt_model": response.stt_model,
        "word_count": word_count,
        "artifacts": artifacts,
        "warnings": warnings,
        "transcript_sha256": sha256(transcript_text.encode("utf-8")).hexdigest(),
        "metadata_sha256": sha256(metadata_json.encode("utf-8")).hexdigest(),
        "captured_at": captured_at,
        "credential_fields_redacted": True,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _result_from_manifest(
    video: VideoRef,
    manifest: dict[str, Any],
    *,
    status: str,
    output_dir: Path | None = None,
) -> Result:
    artifacts = manifest.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
    output_path = None
    if artifacts.get("markdown"):
        artifact_path = Path(str(artifacts["markdown"]))
        output_path = output_dir / artifact_path if output_dir else artifact_path
    manifest_output_path = output_dir / "source_manifest.json" if output_dir and manifest else None
    raw_warnings = manifest.get("warnings", [])
    warnings = (
        [str(warning) for warning in raw_warnings]
        if isinstance(raw_warnings, list)
        else []
    )
    return Result(
        video_id=video.id,
        title=video.title,
        url=video.url,
        status=status,
        output_path=str(output_path) if output_path else None,
        manifest_path=str(manifest_output_path) if manifest_output_path else None,
        warnings=warnings,
        transcript_source=str(manifest.get("transcript_source", "")),
        segment_count=int(manifest.get("transcript_segment_count", 0) or 0),
        word_count=_word_count_from_manifest(manifest),
    )


def result_event(result: Result) -> dict[str, Any]:
    return {
        "timestamp": iso_utc_now(),
        "id": result.video_id,
        "title": result.title,
        "url": result.url,
        "status": result.status,
        "output_path": result.output_path,
        "manifest_path": result.manifest_path,
        "warnings": result.warnings,
        "error": result.error,
        "transcript_source": result.transcript_source,
        "segment_count": result.segment_count,
        "word_count": result.word_count,
    }


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def run_batch(
    args: argparse.Namespace,
    videos: list[VideoRef],
    *,
    caption_fetcher: VideoCaptionFetcher | None = None,
    stt_runner: VideoSttRunner | None = None,
    ocr_runner: VideoOcrRunner | None = None,
) -> list[Result]:
    if not videos:
        return []

    output_root = args.output
    output_root.mkdir(parents=True, exist_ok=True)
    log_path = output_root / "run_log.jsonl"
    log_path.write_text("", encoding="utf-8")

    caption_fetcher = caption_fetcher or YtDlpCaptionFetcher()
    stt_runner = stt_runner or LocalWhisperRunner()
    if ocr_runner is None:
        ocr_kwargs: dict[str, Any] = {}
        if args.frame_interval is not None:
            ocr_kwargs["frame_interval_seconds"] = args.frame_interval
        if args.max_ocr_frames is not None:
            ocr_kwargs["max_frames"] = args.max_ocr_frames
        ocr_runner = LocalVideoOcrRunner(**ocr_kwargs)

    total = len(videos)
    worker_count = min(args.concurrency, total)
    stt_semaphore = threading.Semaphore(args.stt_workers)
    results_by_index: dict[int, Result] = {}
    print_lock = threading.Lock()

    def process(index: int, video: VideoRef) -> Result:
        with print_lock:
            print(f"[{index}/{total}] id={video.id} extract {video.url}", flush=True)
        try:
            return extract_video(
                video,
                output_root=output_root,
                force=args.force,
                caption_fetcher=caption_fetcher,
                stt_runner=stt_runner,
                ocr_runner=ocr_runner,
                stt_semaphore=stt_semaphore,
            )
        except Exception as exc:
            return Result(
                video_id=video.id,
                title=video.title,
                url=video.url,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
            )

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(process, index, video): index - 1
            for index, video in enumerate(videos, start=1)
        }
        for future in as_completed(futures):
            result = future.result()
            results_by_index[futures[future]] = result
            append_jsonl(log_path, result_event(result))
            with print_lock:
                if result.status in {"failed", "failed_retriable", "failed_terminal", "needs_manual"}:
                    print(f"[fail] id={result.video_id} status={result.status} {result.error}", flush=True)
                elif result.status == "skipped":
                    print(f"[skip] id={result.video_id} existing={result.output_path}", flush=True)
                else:
                    warning_text = ",".join(result.warnings) or "none"
                    print(
                        f"[done] id={result.video_id} status={result.status} "
                        f"source={result.transcript_source} words={result.word_count} "
                        f"warnings={warning_text}",
                        flush=True,
                    )

    return [results_by_index[index] for index in range(total)]


def build_summary(results: list[Result], selected_count: int, output_root: Path) -> dict[str, Any]:
    counts: dict[str, int] = {}
    warning_counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
        for warning in result.warnings:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
    return {
        "timestamp": iso_utc_now(),
        "selected": selected_count,
        "counts": dict(sorted(counts.items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "failed_ids": [
            result.video_id
            for result in results
            if result.status in {"failed", "failed_retriable", "failed_terminal", "needs_manual"}
        ],
        "output_root": str(output_root),
        "results": [result_event(result) for result in results],
    }


def print_summary(summary: dict[str, Any]) -> None:
    print("\nSummary")
    print(f"  selected: {summary['selected']}")
    for status, count in summary["counts"].items():
        print(f"  {status}: {count}")
    print(f"  output_root: {summary['output_root']}")
    if summary["warning_counts"]:
        print("  warning_counts:")
        for warning, count in summary["warning_counts"].items():
            print(f"    {warning}: {count}")
    if summary["failed_ids"]:
        print(f"  failed_ids: {', '.join(summary['failed_ids'])}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=(
            "Extract YouTube transcripts from cg_pipeline/video/url.json using "
            "manual captions, local Whisper, and Apple Vision OCR fallback."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=script_dir / "url.json",
        help="Path to JSON list of {id, title, url} objects.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "output",
        help="Output directory. Defaults to cg_pipeline/video/output.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract videos even when source_manifest.json already exists.",
    )
    parser.add_argument(
        "--only",
        help="Comma-separated video ids to process, for example: --only 3,14,78",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=_worker_count(
            None,
            env_names=("CG_PIPELINE_VIDEO_WORKERS",),
            default=DEFAULT_VIDEO_WORKER_COUNT,
        ),
        help=f"Maximum concurrent video jobs. Default: {DEFAULT_VIDEO_WORKER_COUNT}.",
    )
    parser.add_argument(
        "--stt-workers",
        type=int,
        default=_worker_count(
            None,
            env_names=("CG_PIPELINE_WHISPER_JOBS", "CG_PIPELINE_STT_WORKERS"),
            default=DEFAULT_STT_WORKER_COUNT,
        ),
        help=f"Maximum concurrent Whisper jobs. Default: {DEFAULT_STT_WORKER_COUNT}.",
    )
    parser.add_argument(
        "--frame-interval",
        type=float,
        default=None,
        help="Seconds between sampled video frames for Apple Vision OCR.",
    )
    parser.add_argument(
        "--max-ocr-frames",
        type=int,
        default=None,
        help=f"Maximum sampled frames per video. Default: {DEFAULT_MAX_OCR_FRAMES}.",
    )
    args = parser.parse_args(argv)

    if args.concurrency < 1:
        raise SystemExit("--concurrency must be >= 1")
    if args.stt_workers < 1:
        raise SystemExit("--stt-workers must be >= 1")
    if args.frame_interval is not None and args.frame_interval < 0.5:
        raise SystemExit("--frame-interval must be >= 0.5")
    if args.max_ocr_frames is not None and args.max_ocr_frames < 1:
        raise SystemExit("--max-ocr-frames must be >= 1")

    args.input = args.input.resolve()
    args.output = args.output.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    _load_pipeline_env()

    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        only_ids = parse_only_ids(args.only)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    videos, missing_requested = load_videos(args.input, only_ids)
    if missing_requested:
        print(f"Warning: requested ids not found: {', '.join(sorted(missing_requested))}")
    if not videos:
        print("No videos selected.")
        return 0

    print(
        f"Processing {len(videos)} video(s) with concurrency={args.concurrency}, "
        f"stt_workers={args.stt_workers}, force={args.force}, output={args.output}"
    )
    results = run_batch(args, videos)
    summary = build_summary(results, selected_count=len(videos), output_root=args.output)
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_summary(summary)
    print(f"  summary_json: {summary_path}")
    print(f"  run_log_jsonl: {args.output / 'run_log.jsonl'}")
    return 1 if summary["failed_ids"] else 0


def _is_youtube_url(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return hostname == "youtu.be" or hostname == "youtube.com" or hostname.endswith(".youtube.com")


def _certificate_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    return {}


def _worker_count(
    override: int | None,
    *,
    env_names: tuple[str, ...],
    default: int,
) -> int:
    if override is not None:
        return max(1, int(override))
    raw = next(
        (
            value
            for name in env_names
            if (value := os.environ.get(name, "").strip())
        ),
        "",
    )
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def _word_count_from_manifest(manifest: dict[str, Any]) -> int:
    return int(manifest.get("word_count", 0) or 0)


def _segment_as_dict(segment: VideoTranscriptSegment) -> dict[str, Any]:
    return {
        "start_seconds": segment.start_seconds,
        "duration_seconds": segment.duration_seconds,
        "text": segment.text,
    }


def _transcript_text(response: VideoTranscriptResponse) -> str:
    lines = [" ".join(segment.text.split()) for segment in response.segments]
    text = "\n".join(line for line in lines if line).strip()
    if not text and response.raw_captions:
        text = _plain_text_from_captions(response.raw_captions)
    if text:
        text += "\n"
    return text


def _video_warnings(response: VideoTranscriptResponse) -> list[str]:
    warnings = []
    if response.transcript_source == "auto_captions":
        warnings.append("auto_captions")
    elif response.transcript_source == "local_whisper":
        warnings.append("local_whisper_fallback")
    elif response.transcript_source == "video_ocr":
        warnings.append("video_ocr_fallback")
    if response.transcript_source in {"manual_captions", "auto_captions"}:
        if not response.caption_language:
            warnings.append("caption_language_unknown")
    if not response.segments:
        warnings.append("sparse_transcript")
    else:
        word_count = len(_transcript_text(response).split())
        if (
            response.duration_seconds is not None
            and response.duration_seconds > 60
            and word_count < max(15, int(response.duration_seconds / 4))
        ):
            warnings.append("sparse_transcript")
    return warnings


def _preferred_video_languages(video: VideoRef) -> list[str]:
    title = video.title.lower()
    portuguese_markers = (
        "aprender",
        "forma",
        "linguagem",
        "nuvem",
        "pln",
        "processamento",
        "programador",
        "regulares",
        "melhor",
        "express",
        "vídeo",
        "video",
    )
    if any(marker in title for marker in portuguese_markers):
        return ["pt", "pt-BR", "pt-PT", "en", "en-US"]
    return ["en", "en-US", "pt", "pt-BR", "pt-PT"]


def _local_whisper_unusable_reasons(
    response: VideoTranscriptResponse,
    video: VideoRef,
) -> list[str]:
    text = _transcript_text(response)
    normalized_lines = [
        line.strip().lower()
        for line in re.split(r"[\r\n]+", text)
        if line.strip()
    ]
    phrase_units = [
        unit.strip().lower()
        for unit in re.split(r"[.!?]+", text)
        if unit.strip()
    ]
    tokens = _text_tokens(text)
    reasons: list[str] = []
    if not tokens:
        reasons.append("empty")
        return reasons
    if response.duration_seconds is not None and response.duration_seconds >= 60:
        if len(tokens) < max(15, int(response.duration_seconds / 4)):
            reasons.append("very_low_word_count")
    if _dominant_repeat_ratio(normalized_lines) >= 0.75 and len(normalized_lines) >= 3:
        reasons.append("repeated_lines")
    if _dominant_repeat_ratio(phrase_units) >= 0.75 and len(phrase_units) >= 3:
        reasons.append("repeated_phrase")
    if _preferred_video_languages(video)[0].startswith("pt") and _tiny_english_boilerplate(text, tokens):
        reasons.append("language_mismatch")
    return _dedupe_preserving_order(reasons)


def _text_tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9']+", text.lower())


def _dominant_repeat_ratio(values: list[str]) -> float:
    if not values:
        return 0.0
    counts: dict[str, int] = {}
    for value in values:
        normalized = " ".join(value.split())
        counts[normalized] = counts.get(normalized, 0) + 1
    return max(counts.values()) / len(values)


def _tiny_english_boilerplate(text: str, tokens: list[str]) -> bool:
    lowered = text.lower()
    english_boilerplate = (
        "we'll be right back",
        "we will be right back",
        "thanks for watching",
        "don't forget to subscribe",
        "music",
    )
    return len(tokens) < 40 and any(phrase in lowered for phrase in english_boilerplate)


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _extract_ytdlp_info(url: str) -> dict[str, Any]:
    try:
        import yt_dlp
    except ImportError as exc:
        raise VideoExtractionFailure(
            "yt-dlp is not installed; cannot fetch YouTube captions",
            unavailable=True,
        ) from exc
    try:
        with yt_dlp.YoutubeDL(
            {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
            }
        ) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise _video_failure_from_message("yt-dlp caption extraction failed", str(exc))
    if isinstance(info, dict):
        return info
    raise VideoExtractionFailure("yt-dlp returned invalid video metadata", retriable=True)


def _select_caption_track(
    tracks_by_language: Any,
    preferred_languages: list[str],
) -> dict[str, Any] | None:
    if not isinstance(tracks_by_language, dict):
        return None
    language_order = _caption_language_order(
        list(tracks_by_language.keys()),
        preferred_languages,
    )
    for allow_translated in (False, True):
        for language in language_order:
            formats = tracks_by_language.get(language)
            if not isinstance(formats, list):
                continue
            selected = _select_caption_format(
                formats,
                allow_translated=allow_translated,
            )
            if selected is not None:
                return {
                    "language": language,
                    "url": str(selected.get("url", "")),
                    "ext": str(selected.get("ext", "")),
                }
    return None


def _caption_language_order(
    available_languages: list[str],
    preferred_languages: list[str],
) -> list[str]:
    ordered = []
    for preferred in preferred_languages:
        for available in available_languages:
            if available == preferred and available not in ordered:
                ordered.append(available)
        preferred_base = preferred.split("-", 1)[0]
        for available in available_languages:
            available_base = available.split("-", 1)[0]
            if available_base == preferred_base and available not in ordered:
                ordered.append(available)
    for available in sorted(available_languages):
        if available not in ordered:
            ordered.append(available)
    return ordered


def _select_caption_format(
    formats: list[Any],
    *,
    allow_translated: bool,
) -> dict[str, Any] | None:
    valid_formats = [
        item
        for item in formats
        if isinstance(item, dict)
        and item.get("url")
        and (allow_translated or not _is_translated_caption_format(item))
    ]
    for extension in ("vtt", "ttml", "json3", "srv3"):
        for item in valid_formats:
            if str(item.get("ext", "")) == extension:
                return item
    return valid_formats[0] if valid_formats else None


def _is_translated_caption_format(format_info: dict[str, Any]) -> bool:
    query = dict(parse_qsl(urlparse(str(format_info.get("url", ""))).query))
    return bool(query.get("tlang"))


def _caption_url_as_vtt(url: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["fmt"] = "vtt"
    return urlunparse(parsed._replace(query=urlencode(query)))


def _download_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "companion-cg-video-pipeline/1.0",
            "Accept": "text/html,text/vtt,application/json;q=0.9,*/*;q=0.5",
        },
    )
    try:
        with urlopen(request, timeout=20, context=_certificate_context()) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise VideoExtractionFailure(
            f"HTTP {exc.code} fetching video transcript data",
            retriable=500 <= exc.code < 600 or exc.code == 429,
            terminal=exc.code in {401, 403, 404, 410},
        ) from exc
    except URLError as exc:
        raise VideoExtractionFailure(
            f"Network error fetching video transcript data: {exc.reason}",
            retriable=True,
        ) from exc


def _segments_from_caption_payload(raw_captions: str) -> list[VideoTranscriptSegment]:
    stripped = raw_captions.strip()
    if stripped.startswith("{"):
        return _segments_from_json3(stripped)
    return _segments_from_vtt(stripped)


def _segments_from_json3(payload: str) -> list[VideoTranscriptSegment]:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return []
    events = decoded.get("events", []) if isinstance(decoded, dict) else []
    segments = []
    for event in events:
        if not isinstance(event, dict):
            continue
        text = "".join(
            str(seg.get("utf8", ""))
            for seg in event.get("segs", [])
            if isinstance(seg, dict)
        ).strip()
        if not text:
            continue
        start_ms = _optional_float(event.get("tStartMs"))
        duration_ms = _optional_float(event.get("dDurationMs"))
        segments.append(
            VideoTranscriptSegment(
                start_seconds=start_ms / 1000 if start_ms is not None else None,
                duration_seconds=(
                    duration_ms / 1000 if duration_ms is not None else None
                ),
                text=" ".join(text.split()),
            )
        )
    return segments


def _segments_from_vtt(payload: str) -> list[VideoTranscriptSegment]:
    segments = []
    cue_lines: list[str] = []
    start_seconds: float | None = None
    duration_seconds: float | None = None
    for raw_line in payload.splitlines() + [""]:
        line = raw_line.strip()
        timing_match = re.match(
            r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{1,3})?)\s+-->\s+"
            r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{1,3})?)",
            line,
        )
        if timing_match:
            cue_lines = []
            start_seconds = _parse_timestamp(timing_match.group("start"))
            end_seconds = _parse_timestamp(timing_match.group("end"))
            duration_seconds = (
                end_seconds - start_seconds
                if start_seconds is not None and end_seconds is not None
                else None
            )
            continue
        if line:
            if line == "WEBVTT" or line.startswith(("NOTE", "STYLE", "Kind:", "Language:")):
                continue
            if "-->" not in line:
                cue_lines.append(_strip_caption_markup(line))
            continue
        if cue_lines:
            text = " ".join(" ".join(cue_lines).split())
            if text:
                segments.append(
                    VideoTranscriptSegment(
                        start_seconds=start_seconds,
                        duration_seconds=duration_seconds,
                        text=text,
                    )
                )
        cue_lines = []
        start_seconds = None
        duration_seconds = None
    return segments


def _plain_text_from_captions(raw_captions: str) -> str:
    segments = _segments_from_caption_payload(raw_captions)
    if segments:
        return "\n".join(segment.text for segment in segments if segment.text).strip()
    lines = []
    for raw_line in raw_captions.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT" or "-->" in line:
            continue
        if line.startswith(("NOTE", "STYLE", "Kind:", "Language:")):
            continue
        lines.append(_strip_caption_markup(line))
    return "\n".join(lines).strip()


def _segments_from_plain_text(text: str) -> list[VideoTranscriptSegment]:
    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not cleaned:
        return []
    return [VideoTranscriptSegment(text=cleaned)]


def _strip_caption_markup(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).replace("&nbsp;", " ").strip()


def _parse_timestamp(value: str) -> float | None:
    parts = value.split(":")
    try:
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        return None
    return None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any, *, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _video_failure_from_message(prefix: str, message: str) -> VideoExtractionFailure:
    normalized = message.lower()
    terminal_markers = (
        "private video",
        "video unavailable",
        "this video is unavailable",
        "removed",
        "deleted",
        "unsupported url",
    )
    retriable_markers = (
        "429",
        "too many requests",
        "rate-limit",
        "rate limit",
        "timed out",
        "timeout",
        "temporarily",
    )
    unavailable_markers = (
        "no audio",
        "does not contain audio",
        "audio only",
        "requested format is not available",
    )
    return VideoExtractionFailure(
        f"{prefix}: {message}".strip(),
        terminal=any(marker in normalized for marker in terminal_markers),
        retriable=any(marker in normalized for marker in retriable_markers),
        unavailable=any(marker in normalized for marker in unavailable_markers),
    )


def _first_existing_command(names: list[str]) -> str:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return ""


def _first_existing_path(paths: list[str]) -> str:
    for path in paths:
        expanded = Path(path).expanduser()
        if expanded.exists():
            return str(expanded)
    return ""


def _yt_dlp_command() -> list[str]:
    path = shutil.which("yt-dlp")
    if path:
        return [path]
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        return []
    return [sys.executable, "-m", "yt_dlp"]


def _configured_apple_vision_languages() -> list[str]:
    raw = os.environ.get("CG_PIPELINE_APPLE_VISION_LANGS", "").strip()
    if not raw:
        return []
    return [language.strip() for language in re.split(r"[+,]", raw) if language.strip()]


def _apple_vision_languages_from_preferred(preferred_languages: list[str]) -> list[str]:
    primary = (preferred_languages[0] if preferred_languages else "").split("-", 1)[0]
    if primary == "pt":
        return ["pt-BR", "en-US"]
    if primary == "en":
        return ["en-US"]
    return ["pt-BR", "en-US"]


def _load_ocrmac() -> Any:
    try:
        from ocrmac import ocrmac
    except ImportError as exc:
        raise VideoExtractionFailure(
            "Local video OCR unavailable: ocrmac Apple Vision wrapper is not installed",
            unavailable=True,
        ) from exc
    return ocrmac


def _run_apple_vision_ocr(
    ocrmac_module: Any,
    frame_path: Path,
    *,
    recognition_languages: list[str],
    recognition_level: str,
) -> AppleVisionOcrResult:
    try:
        annotations = ocrmac_module.OCR(
            str(frame_path.resolve()),
            language_preference=recognition_languages,
            recognition_level=recognition_level,
        ).recognize()
    except Exception as exc:
        raise VideoExtractionFailure(
            f"Apple Vision video OCR failed: {exc}",
            retriable=True,
        ) from exc

    lines: list[str] = []
    confidences: list[float] = []
    for annotation in annotations:
        if isinstance(annotation, (list, tuple)) and annotation:
            text = str(annotation[0]).strip()
            if len(annotation) > 1:
                try:
                    confidences.append(float(annotation[1]))
                except (TypeError, ValueError):
                    pass
        else:
            text = str(annotation).strip()
        if text:
            lines.append(text)
    return AppleVisionOcrResult(
        text="\n".join(lines),
        average_confidence=(
            sum(confidences) / len(confidences)
            if confidences
            else None
        ),
        line_count=len(lines),
    )


def _normalize_ocr_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cleaned = " ".join(line.split()).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines).strip()


def _near_duplicate_ocr_text(candidate: str, existing: str) -> bool:
    candidate_tokens = set(_text_tokens(candidate))
    existing_tokens = set(_text_tokens(existing))
    if not candidate_tokens or not existing_tokens:
        return candidate.strip().lower() == existing.strip().lower()
    overlap = len(candidate_tokens & existing_tokens)
    union = len(candidate_tokens | existing_tokens)
    containment = overlap / max(min(len(candidate_tokens), len(existing_tokens)), 1)
    jaccard = overlap / max(union, 1)
    return containment >= 0.9 or jaccard >= 0.82


if __name__ == "__main__":
    raise SystemExit(main())
