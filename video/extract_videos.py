#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, unquote, urlparse, urlunparse

from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from cg_pipeline.video import legacy_extract_videos as base_video  # noqa: E402

VideoTranscriptResponse = base_video.VideoTranscriptResponse
VideoTranscriptSegment = base_video.VideoTranscriptSegment
VideoExtractionFailure = base_video.VideoExtractionFailure
_run_apple_vision_ocr = base_video._run_apple_vision_ocr
_local_whisper_unusable_reasons = base_video._local_whisper_unusable_reasons
_extract_ytdlp_info = base_video._extract_ytdlp_info


class YtDlpCaptionFetcher(base_video.YtDlpCaptionFetcher):
    """Compatibility wrapper whose metadata hook can be monkeypatched here."""

    def fetch(
        self,
        url: str,
        *,
        preferred_languages: list[str],
    ) -> base_video.VideoTranscriptResponse:
        original = base_video._extract_ytdlp_info
        base_video._extract_ytdlp_info = _extract_ytdlp_info
        try:
            return super().fetch(url, preferred_languages=preferred_languages)
        finally:
            base_video._extract_ytdlp_info = original


DEFAULT_CONFIG_PATH = SCRIPT_DIR / "config.json"
DEFAULT_INPUT_PATH = SCRIPT_DIR / "url.json"
DEFAULT_OUTPUT_ROOT = SCRIPT_DIR / "output"
DEFAULT_CACHE_ROOT = SCRIPT_DIR / "cache"
PROMPT_VERSION = "video_gemini_pass2_v1"
AUDIO_PASS_VERSION = "audio_grounding_v1"
GEMINI_PROVIDER = "gemini_multimodal"
GEMINI_STRATEGY = "video_gemini_two_pass"
YOUTUBE_MIME_TYPE = "video/mp4"


class AcquisitionFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retriable: bool = False,
        gate_failures: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.retriable = retriable
        self.gate_failures = gate_failures or []


@dataclass(frozen=True)
class VideoRef:
    id: str
    title: str
    url: str
    original_url: str | None = None


@dataclass(frozen=True)
class ChunkWindow:
    index: int
    start_seconds: float | None
    end_seconds: float | None


@dataclass(frozen=True)
class Pass1Transcript:
    response: base_video.VideoTranscriptResponse
    cache_key: str
    cache_status: str
    transcript_sha256: str
    source_fingerprint: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GeminiSettings:
    profile: str
    model: str
    fps: float
    media_resolution: str
    temperature: float
    max_output_tokens: int
    prompt_version: str
    chunk_longer_than_seconds: int
    chunk_seconds: int
    chunk_overlap_seconds: int
    max_transcript_chars_per_chunk: int
    min_words: int
    timestamp_span_tolerance_seconds: int
    timestamp_span_min_ratio: float
    title_similarity_min: float
    upload_poll_seconds: float
    upload_timeout_seconds: int


@dataclass
class GeminiChunkResult:
    window: ChunkWindow
    cache_key: str
    cache_status: str
    markdown: str
    usage: dict[str, Any]
    request: dict[str, Any]
    response: dict[str, Any]
    model_version: str | None = None


@dataclass
class Result:
    video_id: str
    title: str
    url: str
    status: str
    output_path: str | None = None
    artifact_dir: str | None = None
    manifest_path: str | None = None
    gate_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    cache_keys: list[str] = field(default_factory=list)
    transcript_cache_key: str | None = None
    transcript_source: str = ""
    model: str = ""
    fps: float | None = None
    media_resolution: str = ""
    duration_seconds: float | None = None
    word_count: int = 0
    image_count: int = 0
    total_token_count: int = 0


class TimestampedAudioTranscriber:
    def __init__(
        self,
        *,
        binary_path: str | None = None,
        model_path: str | None = None,
        ffmpeg_path: str | None = None,
    ) -> None:
        base_video._load_pipeline_env()
        self.binary_path = (
            binary_path
            or os.environ.get("CG_PIPELINE_WHISPER_CPP_BINARY", "").strip()
            or base_video._first_existing_path(["~/.local/bin/whisper-cli"])
            or base_video._first_existing_command(["whisper-cli", "whisper-cpp", "main"])
        )
        self.model_path = (
            model_path
            or os.environ.get("CG_PIPELINE_WHISPER_MODEL", "").strip()
            or base_video._first_existing_path(
                [
                    "~/.local/share/whisper.cpp/models/ggml-large-v3-turbo-q5_0.bin",
                    "~/.local/share/whisper.cpp/models/ggml-large-v3-q5_0.bin",
                    "~/Models/whisper/ggml-large-v3-turbo-q5_0.bin",
                    "~/.cache/whisper.cpp/ggml-large-v3-turbo-q5_0.bin",
                    "./models/ggml-large-v3-turbo-q5_0.bin",
                ]
            )
        )
        self.ffmpeg_path = (
            ffmpeg_path
            or os.environ.get("CG_PIPELINE_FFMPEG_BINARY", "").strip()
            or base_video._first_existing_command(["ffmpeg"])
        )
        self.extra_args = shlex.split(
            os.environ.get("CG_PIPELINE_WHISPER_CPP_EXTRA_ARGS", "").strip()
        )

    def transcribe(
        self,
        source: str,
        *,
        artifact_dir: Path,
        input_dir: Path,
        preferred_languages: list[str],
        stt_semaphore: threading.Semaphore | None,
    ) -> base_video.VideoTranscriptResponse:
        del preferred_languages
        if not self.binary_path:
            raise base_video.VideoExtractionFailure(
                "Local Whisper unavailable: whisper.cpp binary not found",
                unavailable=True,
            )
        if not self.model_path:
            raise base_video.VideoExtractionFailure(
                "Local Whisper unavailable: model file not found",
                unavailable=True,
            )

        artifact_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="gemini_audio_", dir=artifact_dir) as temp:
            temp_dir = Path(temp)
            source_path = resolve_local_source_path(source, input_dir=input_dir)
            if source_path is not None:
                audio_path = self._extract_audio_from_local_file(source_path, temp_dir)
                duration_seconds = probe_local_duration(source_path)
                final_url = str(source_path)
                extraction_tool = self.ffmpeg_path
                extraction_source = "local_file"
            else:
                audio_path = self._extract_audio_from_url(source, temp_dir)
                probed = probe_remote_metadata(source)
                duration_seconds = optional_float(probed.get("duration_seconds"))
                final_url = str(probed.get("final_url") or source)
                extraction_tool = "yt-dlp"
                extraction_source = "remote_url"

            output_base = temp_dir / "whisper_transcript"
            whisper_command = [
                self.binary_path,
                *self.extra_args,
                "-m",
                self.model_path,
                "-f",
                str(audio_path),
                "-l",
                "auto",
                "-ovtt",
                "-otxt",
                "-of",
                str(output_base),
            ]
            try:
                completed = base_video._run_whisper_command(
                    whisper_command,
                    stt_semaphore=stt_semaphore,
                )
            except subprocess.TimeoutExpired as exc:
                raise base_video.VideoExtractionFailure(
                    "Timed out running local Whisper transcription",
                    retriable=True,
                ) from exc
            except subprocess.CalledProcessError as exc:
                if base_video._should_retry_whisper_without_gpu(exc) and "--no-gpu" not in whisper_command:
                    retry_command = [whisper_command[0], "--no-gpu", *whisper_command[1:]]
                    try:
                        completed = base_video._run_whisper_command(
                            retry_command,
                            stt_semaphore=stt_semaphore,
                        )
                    except subprocess.TimeoutExpired as retry_exc:
                        raise base_video.VideoExtractionFailure(
                            "Timed out running local Whisper transcription",
                            retriable=True,
                        ) from retry_exc
                    except subprocess.CalledProcessError as retry_exc:
                        raise base_video.VideoExtractionFailure(
                            "Local Whisper transcription failed after CPU retry: "
                            f"{retry_exc.stderr or retry_exc.stdout}",
                            retriable=True,
                        ) from retry_exc
                else:
                    raise base_video.VideoExtractionFailure(
                        f"Local Whisper transcription failed: {exc.stderr or exc.stdout}",
                        retriable=True,
                    ) from exc

            vtt_path = output_base.with_suffix(".vtt")
            txt_path = output_base.with_suffix(".txt")
            raw_captions = vtt_path.read_text(encoding="utf-8") if vtt_path.exists() else ""
            segments = base_video._segments_from_vtt(raw_captions) if raw_captions else []
            transcript_text = (
                txt_path.read_text(encoding="utf-8").strip()
                if txt_path.exists()
                else completed.stdout.strip()
            )
            if not segments:
                segments = base_video._segments_from_plain_text(transcript_text)
            if not segments:
                raise base_video.VideoExtractionFailure(
                    "Local Whisper returned an empty transcript",
                    retriable=True,
                )

            return base_video.VideoTranscriptResponse(
                final_url=final_url,
                title="",
                transcript_source="local_whisper_vtt" if raw_captions else "local_whisper",
                duration_seconds=duration_seconds,
                segments=segments,
                raw_captions=raw_captions,
                stt_model=Path(self.model_path).name,
                audio_manifest={
                    "cached_audio": False,
                    "audio_retained": False,
                    "audio_policy": (
                        "Audio is extracted as an intermediate and deleted after "
                        "timestamped transcription; replay uses cached transcript artifacts."
                    ),
                    "extraction_source": extraction_source,
                    "extraction_tool": extraction_tool,
                    "stt_tool": self.binary_path,
                    "stt_extra_args": self.extra_args,
                    "stt_model": Path(self.model_path).name,
                    "timestamped_output": bool(raw_captions),
                },
            )

    def _extract_audio_from_url(self, source: str, temp_dir: Path) -> Path:
        yt_dlp_command = base_video._yt_dlp_command()
        if not yt_dlp_command:
            raise base_video.VideoExtractionFailure(
                "Local Whisper unavailable: yt-dlp command not found",
                unavailable=True,
            )
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
                    source,
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
            )
        except subprocess.TimeoutExpired as exc:
            raise base_video.VideoExtractionFailure(
                "Timed out extracting remote audio for local Whisper",
                retriable=True,
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise base_video._video_failure_from_message(
                "yt-dlp audio extraction failed",
                f"{exc.stderr}\n{exc.stdout}",
            ) from exc

        audio_paths = sorted(temp_dir.glob("audio.*"))
        if not audio_paths:
            raise base_video.VideoExtractionFailure(
                "yt-dlp did not produce audio for local Whisper",
                unavailable=True,
            )
        return audio_paths[0]

    def _extract_audio_from_local_file(self, source_path: Path, temp_dir: Path) -> Path:
        if not self.ffmpeg_path:
            raise base_video.VideoExtractionFailure(
                "Local Whisper unavailable for direct files: ffmpeg command not found",
                unavailable=True,
            )
        audio_path = temp_dir / "audio.wav"
        try:
            subprocess.run(
                [
                    self.ffmpeg_path,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(source_path),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(audio_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
            )
        except subprocess.TimeoutExpired as exc:
            raise base_video.VideoExtractionFailure(
                "Timed out extracting direct-file audio for local Whisper",
                retriable=True,
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise base_video.VideoExtractionFailure(
                f"ffmpeg audio extraction failed: {exc.stderr or exc.stdout}",
                retriable=True,
            ) from exc
        return audio_path


class GeminiVideoClient:
    def __init__(self, settings: GeminiSettings) -> None:
        self.settings = settings
        self._client: Any | None = None
        self._uploaded_files_by_path: dict[str, Any] = {}
        self._upload_lock = threading.Lock()

    def generate_chunk(
        self,
        *,
        video: VideoRef,
        input_dir: Path,
        pass1: Pass1Transcript,
        window: ChunkWindow,
        settings: GeminiSettings,
        cache_root: Path,
        refresh_cache: bool,
        gemini_semaphore: threading.Semaphore | None,
    ) -> GeminiChunkResult:
        transcript_context = transcript_context_for_window(
            pass1.response,
            window,
            max_chars=settings.max_transcript_chars_per_chunk,
        )
        prompt = build_pass2_prompt(
            video=video,
            pass1=pass1,
            window=window,
            settings=settings,
            transcript_context=transcript_context,
        )
        prompt_sha256 = sha256_text(prompt)
        media_source = gemini_media_source(video.url)
        request_material = gemini_request_material(
            video=video,
            media_source=media_source,
            pass1=pass1,
            window=window,
            settings=settings,
            prompt_sha256=prompt_sha256,
        )
        cache_key = stable_hash(request_material)
        paths = gemini_cache_paths(cache_root, cache_key)
        if not refresh_cache and paths["response"].exists() and paths["text"].exists():
            response = load_json(paths["response"])
            usage = load_json(paths["usage"]) if paths["usage"].exists() else {}
            markdown = paths["text"].read_text(encoding="utf-8")
            request = load_json(paths["request"]) if paths["request"].exists() else request_material
            return GeminiChunkResult(
                window=window,
                cache_key=cache_key,
                cache_status="cache",
                markdown=markdown,
                usage=usage,
                request=request,
                response=response,
                model_version=str(response.get("model_version") or "") or None,
            )

        with maybe_semaphore(gemini_semaphore):
            client = self._get_client()
            media_part, media_reference = self._build_media_part(
                media_source,
                input_dir=input_dir,
                window=window,
                fps=settings.fps,
            )
            request_payload = {
                **request_material,
                "media_reference": media_reference,
                "prompt": prompt,
            }
            config = self._generation_config(settings)
            try:
                response_obj = client.models.generate_content(
                    model=settings.model,
                    contents=[
                        media_part,
                        prompt,
                    ],
                    config=config,
                )
            except Exception as exc:
                if should_retry_gemini_with_local_file(exc, media_source, media_reference):
                    try:
                        fallback_path = download_youtube_clip_for_gemini(
                            media_source,
                            window=window,
                            cache_root=cache_root,
                        )
                        fallback_window = ChunkWindow(
                            index=window.index,
                            start_seconds=None,
                            end_seconds=None,
                        )
                        media_part, fallback_reference = self._build_media_part(
                            str(fallback_path),
                            input_dir=input_dir,
                            window=fallback_window,
                            fps=settings.fps,
                        )
                        media_reference = {
                            **fallback_reference,
                            "fallback_from": media_reference,
                            "fallback_reason": str(exc),
                        }
                        request_payload["media_reference"] = media_reference
                        response_obj = client.models.generate_content(
                            model=settings.model,
                            contents=[
                                media_part,
                                prompt,
                            ],
                            config=config,
                        )
                    except Exception as fallback_exc:
                        raise AcquisitionFailure(
                            f"Gemini call failed for chunk {window.index}: {exc}; "
                            f"local file fallback failed: {fallback_exc}",
                            retriable=True,
                            gate_failures=["gemini_call_failed"],
                        ) from fallback_exc
                else:
                    raise AcquisitionFailure(
                        f"Gemini call failed for chunk {window.index}: {exc}",
                        retriable=True,
                        gate_failures=["gemini_call_failed"],
                    ) from exc

        markdown = normalize_model_markdown(getattr(response_obj, "text", "") or "")
        response = serialize_model(response_obj)
        usage = serialize_model(getattr(response_obj, "usage_metadata", None))
        paths["dir"].mkdir(parents=True, exist_ok=True)
        atomic_write_text(paths["request"], json.dumps(request_payload, ensure_ascii=False, indent=2) + "\n")
        atomic_write_text(paths["response"], json.dumps(response, ensure_ascii=False, indent=2) + "\n")
        atomic_write_text(paths["usage"], json.dumps(usage, ensure_ascii=False, indent=2) + "\n")
        atomic_write_text(paths["text"], markdown)
        return GeminiChunkResult(
            window=window,
            cache_key=cache_key,
            cache_status="network",
            markdown=markdown,
            usage=usage,
            request=request_payload,
            response=response,
            model_version=str(response.get("model_version") or "") or None,
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from google import genai
        except ImportError as exc:
            raise AcquisitionFailure(
                "google-genai is not installed; install requirements.txt",
                gate_failures=["gemini_sdk_missing"],
            ) from exc

        api_key = (
            os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY_ADMIN", "").strip()
        )
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()
        return self._client

    def _generation_config(self, settings: GeminiSettings) -> Any:
        from google.genai import types

        return types.GenerateContentConfig(
            temperature=settings.temperature,
            max_output_tokens=settings.max_output_tokens,
            media_resolution=media_resolution_enum(settings.media_resolution),
        )

    def _build_media_part(
        self,
        source: str,
        *,
        input_dir: Path,
        window: ChunkWindow,
        fps: float,
    ) -> tuple[Any, dict[str, Any]]:
        from google.genai import types

        video_metadata_kwargs: dict[str, Any] = {"fps": fps}
        if window.start_seconds is not None:
            video_metadata_kwargs["start_offset"] = seconds_offset(window.start_seconds)
        if window.end_seconds is not None:
            video_metadata_kwargs["end_offset"] = seconds_offset(window.end_seconds)
        video_metadata = types.VideoMetadata(**video_metadata_kwargs)

        local_path = resolve_local_source_path(source, input_dir=input_dir)
        if local_path is None:
            mime_type = infer_video_mime_type(source) or YOUTUBE_MIME_TYPE
            return (
                types.Part(
                    file_data=types.FileData(
                        file_uri=source,
                        mime_type=mime_type,
                    ),
                    video_metadata=video_metadata,
                ),
                {
                    "mode": "external_uri",
                    "file_uri": source,
                    "mime_type": mime_type,
                    "video_metadata": video_metadata_kwargs,
                },
            )

        uploaded = self._upload_local_file(local_path)
        mime_type = uploaded.mime_type or infer_video_mime_type(str(local_path)) or YOUTUBE_MIME_TYPE
        return (
            types.Part(
                file_data=types.FileData(
                    file_uri=uploaded.uri,
                    mime_type=mime_type,
                ),
                video_metadata=video_metadata,
            ),
            {
                "mode": "files_upload",
                "source_path": str(local_path),
                "file_name": uploaded.name,
                "file_uri": uploaded.uri,
                "mime_type": mime_type,
                "video_metadata": video_metadata_kwargs,
            },
        )

    def _upload_local_file(self, local_path: Path) -> Any:
        key = str(local_path.resolve())
        with self._upload_lock:
            existing = self._uploaded_files_by_path.get(key)
            if existing is not None:
                return existing
            client = self._get_client()
            uploaded = client.files.upload(file=local_path)
            uploaded = self._wait_for_active_file(uploaded)
            self._uploaded_files_by_path[key] = uploaded
            return uploaded

    def _wait_for_active_file(self, uploaded: Any) -> Any:
        client = self._get_client()
        started = time.monotonic()
        current = uploaded
        while True:
            state = str(getattr(current, "state", "") or "")
            if state.endswith("ACTIVE"):
                return current
            if state.endswith("FAILED"):
                raise AcquisitionFailure(
                    f"Gemini file upload failed: {serialize_model(current).get('error')}",
                    gate_failures=["gemini_file_upload_failed"],
                )
            if time.monotonic() - started > self.settings.upload_timeout_seconds:
                raise AcquisitionFailure(
                    "Timed out waiting for Gemini file upload processing",
                    retriable=True,
                    gate_failures=["gemini_file_upload_timeout"],
                )
            time.sleep(self.settings.upload_poll_seconds)
            current = client.files.get(name=current.name)


def media_resolution_enum(value: str) -> Any:
    from google.genai import types

    normalized = value.strip().lower().replace("-", "_")
    mapping = {
        "unspecified": types.MediaResolution.MEDIA_RESOLUTION_UNSPECIFIED,
        "low": types.MediaResolution.MEDIA_RESOLUTION_LOW,
        "medium": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
        "high": types.MediaResolution.MEDIA_RESOLUTION_HIGH,
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise SystemExit(
            "--media-resolution must be one of: low, medium, high, unspecified"
        ) from exc


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def stable_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str, max_length: int = 90) -> str:
    return base_video.slugify(value, max_length=max_length)


def yaml_scalar(value: Any) -> str:
    return base_video.yaml_scalar(value)


def yaml_frontmatter(data: dict[str, Any]) -> str:
    return base_video.yaml_frontmatter(data)


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def markdown_image_count(text: str) -> int:
    return len(re.findall(r"!\[[^\]]*]\([^)]+\)", text))


def markdown_link_count(text: str) -> int:
    without_images = re.sub(r"!\[[^\]]*]\([^)]+\)", "", text)
    return len(re.findall(r"\[[^\]]+]\([^)]+\)", without_images))


def optional_float(value: Any) -> float | None:
    return base_video._optional_float(value)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON file is not valid: {path}: {exc}") from exc


def load_config(path: Path) -> dict[str, Any]:
    raw = load_json(path)
    if not isinstance(raw, dict):
        raise SystemExit(f"Config JSON must be an object: {path}")
    return raw


def parse_only_ids(value: str | None) -> set[str] | None:
    return base_video.parse_only_ids(value)


def load_videos(input_path: Path, only_ids: set[str] | None) -> tuple[list[VideoRef], set[str]]:
    raw = load_json(input_path)
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
        seen_ids.add(video_id)
        if only_ids is None or video_id in only_ids:
            videos.append(VideoRef(id=video_id, title=title, url=url))
    missing_requested = only_ids - seen_ids if only_ids is not None else set()
    return videos, missing_requested


def is_youtube_url(url: str) -> bool:
    return base_video._is_youtube_url(url)


def is_youtube_playlist_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    if not is_youtube_url(url):
        return False
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return parsed.path.rstrip("/") == "/playlist" or ("list" in query and "v" not in query)


def resolve_playlist_video_ref(video: VideoRef) -> VideoRef:
    if not is_youtube_playlist_url(video.url):
        return video
    first_url = resolve_first_playlist_video_url(video.url)
    if first_url == video.url:
        return video
    return VideoRef(
        id=video.id,
        title=video.title,
        url=first_url,
        original_url=video.original_url or video.url,
    )


def resolve_first_playlist_video_url(url: str) -> str:
    try:
        import yt_dlp
    except ImportError:
        return url

    try:
        with yt_dlp.YoutubeDL(
            {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": "in_playlist",
                "playlist_items": "1",
            }
        ) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return url

    entries = info.get("entries") if isinstance(info, dict) else None
    if not isinstance(entries, list) or not entries:
        return url
    first = entries[0]
    if not isinstance(first, dict):
        return url
    video_id = str(first.get("id") or "").strip()
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    webpage_url = str(first.get("webpage_url") or first.get("url") or "").strip()
    return webpage_url or url


def normalize_remote_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return url.strip()
    query_pairs = sorted(parse_qsl(parsed.query, keep_blank_values=True))
    query = urlencode(query_pairs, doseq=True)
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            re.sub(r"/{2,}", "/", parsed.path or "/"),
            "",
            query,
            "",
        )
    )


def gemini_media_source(source: str) -> str:
    parsed = urlparse(source.strip())
    if not is_youtube_url(source):
        return source

    video_id = youtube_video_id(source)
    if not video_id:
        return source
    return f"https://www.youtube.com/watch?v={video_id}"


def youtube_video_id(source: str) -> str | None:
    parsed = urlparse(source.strip())
    hostname = (parsed.hostname or "").lower()
    if hostname == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
        return candidate or None
    if hostname == "youtube.com" or hostname.endswith(".youtube.com"):
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        candidate = str(query.get("v") or "").strip()
        return candidate or None
    return None


def should_retry_gemini_with_local_file(
    exc: Exception,
    source: str,
    media_reference: dict[str, Any],
) -> bool:
    if media_reference.get("mode") != "external_uri":
        return False
    if not is_youtube_url(source):
        return False
    message = str(exc)
    return "PERMISSION_DENIED" in message or "403" in message


def download_youtube_clip_for_gemini(
    source: str,
    *,
    window: ChunkWindow,
    cache_root: Path,
) -> Path:
    yt_dlp_command = base_video._yt_dlp_command()
    if not yt_dlp_command:
        raise AcquisitionFailure(
            "yt-dlp command not found for Gemini local-file fallback",
            retriable=True,
            gate_failures=["gemini_local_file_fallback_failed"],
        )

    cache_key = stable_hash(
        {
            "version": "gemini_youtube_local_clip_v1",
            "source": gemini_media_source(source),
            "window": {
                "start_seconds": window.start_seconds,
                "end_seconds": window.end_seconds,
            },
        }
    )
    clip_dir = cache_root / "media" / cache_key
    final_path = clip_dir / "clip.mp4"
    if final_path.exists():
        return final_path

    clip_dir.mkdir(parents=True, exist_ok=True)
    output_template = clip_dir / "download.%(ext)s"
    command = [
        *yt_dlp_command,
        "--no-playlist",
        "-f",
        "bv*[height<=360]+ba/b[height<=360]/best[height<=360]",
        "--merge-output-format",
        "mp4",
        "-o",
        str(output_template),
    ]
    section = yt_dlp_download_section(window)
    if section:
        command.extend(["--download-sections", section, "--force-keyframes-at-cuts"])
    command.append(source)

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
    except subprocess.TimeoutExpired as exc:
        raise AcquisitionFailure(
            "Timed out downloading YouTube video for Gemini local-file fallback",
            retriable=True,
            gate_failures=["gemini_local_file_fallback_failed"],
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise AcquisitionFailure(
            "yt-dlp failed during Gemini local-file fallback: "
            f"{exc.stderr or exc.stdout}",
            retriable=True,
            gate_failures=["gemini_local_file_fallback_failed"],
        ) from exc

    candidates = [
        path
        for path in sorted(clip_dir.glob("download.*"))
        if not path.name.endswith(".part")
    ]
    if not candidates:
        raise AcquisitionFailure(
            "yt-dlp did not produce a video for Gemini local-file fallback",
            retriable=True,
            gate_failures=["gemini_local_file_fallback_failed"],
        )
    candidates[0].replace(final_path)
    atomic_write_text(
        clip_dir / "metadata.json",
        json.dumps(
            {
                "schema_version": "1.0",
                "source": source,
                "final_path": str(final_path),
                "window": {
                    "start_seconds": window.start_seconds,
                    "end_seconds": window.end_seconds,
                },
                "created_at": iso_utc_now(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    return final_path


def yt_dlp_download_section(window: ChunkWindow) -> str | None:
    if window.start_seconds is None or window.end_seconds is None:
        return None
    return f"*{section_timestamp(window.start_seconds)}-{section_timestamp(window.end_seconds)}"


def section_timestamp(seconds: float) -> str:
    total = max(0.0, seconds)
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def resolve_local_source_path(source: str, *, input_dir: Path) -> Path | None:
    parsed = urlparse(source)
    if parsed.scheme == "file":
        path = Path(unquote(parsed.path)).expanduser()
        return path.resolve() if path.exists() else None
    if parsed.scheme:
        return None

    raw_path = Path(source).expanduser()
    candidates = [raw_path]
    if not raw_path.is_absolute():
        candidates.append((input_dir / raw_path).expanduser())
        candidates.append((REPO_ROOT / raw_path).expanduser())
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def source_fingerprint(source: str, *, input_dir: Path) -> dict[str, Any]:
    local_path = resolve_local_source_path(source, input_dir=input_dir)
    if local_path is not None:
        return {
            "kind": "local_file",
            "path": str(local_path),
            "sha256": sha256_file(local_path),
            "size_bytes": local_path.stat().st_size,
        }
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        return {
            "kind": "youtube_url" if is_youtube_url(source) else "remote_video_url",
            "url": normalize_remote_url(source),
        }
    return {
        "kind": "unresolved_source",
        "source": source,
    }


def infer_video_mime_type(source: str) -> str | None:
    mime_type, _ = mimetypes.guess_type(source)
    if mime_type and mime_type.startswith("video/"):
        return mime_type
    return None


def probe_remote_metadata(source: str) -> dict[str, Any]:
    try:
        info = base_video._extract_ytdlp_info(source)
    except Exception:
        return {}
    return {
        "title": info.get("title"),
        "duration_seconds": optional_float(info.get("duration")),
        "final_url": info.get("webpage_url") or info.get("original_url") or source,
    }


def probe_local_duration(path: Path) -> float | None:
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        return None
    try:
        completed = subprocess.run(
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nokey=1:noprint_wrappers=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return optional_float(completed.stdout.strip())


def probe_source_metadata(source: str, *, input_dir: Path) -> dict[str, Any]:
    local_path = resolve_local_source_path(source, input_dir=input_dir)
    if local_path is not None:
        return {
            "title": local_path.stem,
            "duration_seconds": probe_local_duration(local_path),
            "final_url": str(local_path),
        }
    return probe_remote_metadata(source)


def pass1_cache_key(
    video: VideoRef,
    *,
    input_dir: Path,
    preferred_languages: list[str],
    transcriber: TimestampedAudioTranscriber,
) -> tuple[str, dict[str, Any]]:
    fingerprint = source_fingerprint(video.url, input_dir=input_dir)
    material = {
        "audio_pass_version": AUDIO_PASS_VERSION,
        "source": fingerprint,
        "preferred_languages": preferred_languages,
        "whisper_model": Path(transcriber.model_path).name if transcriber.model_path else "",
        "whisper_extra_args": transcriber.extra_args,
    }
    return stable_hash(material), material


def pass1_cache_paths(cache_root: Path, cache_key: str) -> dict[str, Path]:
    directory = cache_root / "pass1" / cache_key
    return {
        "dir": directory,
        "transcript": directory / "transcript.json",
        "metadata": directory / "metadata.json",
        "captions": directory / "captions.vtt",
    }


def gemini_cache_paths(cache_root: Path, cache_key: str) -> dict[str, Path]:
    directory = cache_root / "gemini" / cache_key
    return {
        "dir": directory,
        "request": directory / "request.json",
        "response": directory / "response.json",
        "usage": directory / "usage.json",
        "text": directory / "markdown.md",
    }


def load_pass1_from_cache(cache_key: str, paths: dict[str, Path], fingerprint: str) -> Pass1Transcript | None:
    if not paths["transcript"].exists():
        return None
    payload = load_json(paths["transcript"])
    if not isinstance(payload, dict):
        return None
    segments = [
        base_video.VideoTranscriptSegment(
            text=str(segment.get("text") or ""),
            start_seconds=optional_float(segment.get("start_seconds")),
            duration_seconds=optional_float(segment.get("duration_seconds")),
        )
        for segment in payload.get("segments", [])
        if isinstance(segment, dict)
    ]
    response = base_video.VideoTranscriptResponse(
        final_url=str(payload.get("final_url") or ""),
        title=str(payload.get("title") or ""),
        transcript_source=str(payload.get("transcript_source") or ""),
        caption_language=str(payload.get("caption_language") or ""),
        duration_seconds=optional_float(payload.get("duration_seconds")),
        segments=segments,
        raw_captions=(
            paths["captions"].read_text(encoding="utf-8")
            if paths["captions"].exists()
            else str(payload.get("raw_captions") or "")
        ),
        stt_model=str(payload.get("stt_model") or ""),
        audio_manifest=payload.get("audio_manifest") if isinstance(payload.get("audio_manifest"), dict) else None,
    )
    text = transcript_text(response)
    return Pass1Transcript(
        response=response,
        cache_key=cache_key,
        cache_status="cache",
        transcript_sha256=sha256_text(text),
        source_fingerprint=fingerprint,
        warnings=list(payload.get("warnings", [])) if isinstance(payload.get("warnings"), list) else [],
    )


def write_pass1_cache(
    pass1: Pass1Transcript,
    *,
    paths: dict[str, Path],
    cache_material: dict[str, Any],
) -> None:
    response = pass1.response
    payload = {
        "schema_version": "1.0",
        "audio_pass_version": AUDIO_PASS_VERSION,
        "cache_material": cache_material,
        "final_url": response.final_url,
        "title": response.title,
        "transcript_source": response.transcript_source,
        "caption_language": response.caption_language,
        "duration_seconds": response.duration_seconds,
        "segments": [segment_as_dict(segment) for segment in response.segments],
        "text": transcript_text(response),
        "transcript_sha256": pass1.transcript_sha256,
        "stt_model": response.stt_model,
        "audio_manifest": response.audio_manifest,
        "warnings": pass1.warnings,
        "cached_at": iso_utc_now(),
    }
    atomic_write_text(paths["transcript"], json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(
        paths["metadata"],
        json.dumps(
            {
                "cache_key": pass1.cache_key,
                "transcript_sha256": pass1.transcript_sha256,
                "segment_count": len(response.segments),
                "word_count": word_count(transcript_text(response)),
                "transcript_source": response.transcript_source,
                "duration_seconds": response.duration_seconds,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    if response.raw_captions:
        atomic_write_text(paths["captions"], response.raw_captions)


def acquire_pass1_transcript(
    video: VideoRef,
    *,
    input_dir: Path,
    artifact_dir: Path,
    cache_root: Path,
    force_pass1: bool,
    caption_fetcher: Any,
    transcriber: TimestampedAudioTranscriber,
    stt_semaphore: threading.Semaphore | None,
) -> Pass1Transcript:
    preferred_languages = base_video._preferred_video_languages(
        base_video.VideoRef(id=video.id, title=video.title, url=video.url)
    )
    cache_key, cache_material = pass1_cache_key(
        video,
        input_dir=input_dir,
        preferred_languages=preferred_languages,
        transcriber=transcriber,
    )
    fingerprint = stable_hash(cache_material["source"])
    paths = pass1_cache_paths(cache_root, cache_key)
    if not force_pass1:
        cached = load_pass1_from_cache(cache_key, paths, fingerprint)
        if cached is not None:
            return cached

    failures: list[str] = []
    response: base_video.VideoTranscriptResponse | None = None
    warnings: list[str] = []

    if is_youtube_url(video.url):
        try:
            response = caption_fetcher.fetch(video.url, preferred_languages=preferred_languages)
        except base_video.VideoExtractionFailure as exc:
            failures.append(f"captions: {exc}")
        except Exception as exc:
            failures.append(f"captions: {type(exc).__name__}: {exc}")

    if response is None:
        try:
            response = transcriber.transcribe(
                video.url,
                artifact_dir=artifact_dir,
                input_dir=input_dir,
                preferred_languages=preferred_languages,
                stt_semaphore=stt_semaphore,
            )
            warnings.append("local_whisper_grounding")
        except base_video.VideoExtractionFailure as exc:
            failures.append(f"local_whisper: {exc}")
        except Exception as exc:
            failures.append(f"local_whisper: {type(exc).__name__}: {exc}")

    if response is None or not transcript_text(response).strip():
        reason = "; ".join(failures) or "Pass 1 transcript acquisition unavailable"
        raise AcquisitionFailure(
            f"Pass 1 failed: {reason}",
            retriable=True,
            gate_failures=["pass1_transcript_failed"],
        )

    probed = probe_source_metadata(video.url, input_dir=input_dir)
    duration = response.duration_seconds or optional_float(probed.get("duration_seconds"))
    title = response.title or str(probed.get("title") or "")
    final_url = response.final_url or str(probed.get("final_url") or video.url)
    response = base_video.VideoTranscriptResponse(
        final_url=final_url,
        title=title,
        transcript_source=response.transcript_source,
        caption_language=response.caption_language,
        duration_seconds=duration,
        segments=response.segments,
        raw_captions=response.raw_captions,
        stt_model=response.stt_model,
        audio_manifest=response.audio_manifest,
        video_ocr_manifest=response.video_ocr_manifest,
    )
    pass1 = Pass1Transcript(
        response=response,
        cache_key=cache_key,
        cache_status="network",
        transcript_sha256=sha256_text(transcript_text(response)),
        source_fingerprint=fingerprint,
        warnings=warnings,
    )
    write_pass1_cache(pass1, paths=paths, cache_material=cache_material)
    return pass1


def segment_as_dict(segment: base_video.VideoTranscriptSegment) -> dict[str, Any]:
    return {
        "start_seconds": segment.start_seconds,
        "duration_seconds": segment.duration_seconds,
        "text": segment.text,
    }


def transcript_text(response: base_video.VideoTranscriptResponse) -> str:
    return base_video._transcript_text(response)


def transcript_has_timestamps(response: base_video.VideoTranscriptResponse) -> bool:
    return any(segment.start_seconds is not None for segment in response.segments)


def timestamp_label(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    total = max(0, int(round(seconds)))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def seconds_offset(seconds: float) -> str:
    return f"{max(0.0, seconds):.3f}s"


def build_chunks(duration_seconds: float | None, settings: GeminiSettings) -> list[ChunkWindow]:
    if duration_seconds is None or duration_seconds <= settings.chunk_longer_than_seconds:
        return [ChunkWindow(index=1, start_seconds=None, end_seconds=None)]
    chunk_seconds = max(60, settings.chunk_seconds)
    overlap = max(0, min(settings.chunk_overlap_seconds, chunk_seconds // 3))
    min_tail_seconds = max(30.0, min(120.0, 2.0 / settings.fps))
    windows: list[ChunkWindow] = []
    start = 0.0
    index = 1
    while start < duration_seconds:
        end = min(duration_seconds, start + chunk_seconds)
        if duration_seconds - end < min_tail_seconds and windows:
            end = duration_seconds
        windows.append(
            ChunkWindow(
                index=index,
                start_seconds=round(start, 3),
                end_seconds=round(end, 3),
            )
        )
        if end >= duration_seconds:
            break
        start = max(0.0, end - overlap)
        index += 1
    return windows


def transcript_context_for_window(
    response: base_video.VideoTranscriptResponse,
    window: ChunkWindow,
    *,
    max_chars: int,
) -> str:
    start = window.start_seconds
    end = window.end_seconds
    lines: list[str] = []
    has_timestamps = transcript_has_timestamps(response)
    for segment in response.segments:
        text = " ".join(segment.text.split())
        if not text:
            continue
        if has_timestamps and segment.start_seconds is not None:
            segment_start = segment.start_seconds
            segment_end = (
                segment_start + segment.duration_seconds
                if segment.duration_seconds is not None
                else segment_start
            )
            if start is not None and segment_end < start:
                continue
            if end is not None and segment_start > end:
                continue
            lines.append(f"[{timestamp_label(segment_start)}] {text}")
        else:
            lines.append(text)
    context = "\n".join(lines).strip()
    if len(context) > max_chars:
        return context[:max_chars].rstrip() + "\n[transcript truncated for this chunk]"
    return context


def build_pass2_prompt(
    *,
    video: VideoRef,
    pass1: Pass1Transcript,
    window: ChunkWindow,
    settings: GeminiSettings,
    transcript_context: str,
) -> str:
    duration = pass1.response.duration_seconds
    chunk_text = (
        "Full video"
        if window.start_seconds is None
        else f"{timestamp_label(window.start_seconds)} to {timestamp_label(window.end_seconds)}"
    )
    return f"""You are the video acquisition layer for The Companion curriculum pipeline.

Task: convert the provided video into cleaned markdown that downstream concept extraction can process without branching by source type.

Source metadata:
- XLSX row id: {video.id}
- XLSX row title: {video.title}
- Source URL or file: {video.url}
- Probed source title: {pass1.response.title or "unknown"}
- Probed duration seconds: {duration if duration is not None else "unknown"}
- Chunk window: {chunk_text}
- Gemini model: {settings.model}
- Video sampling fps: {settings.fps}
- Media resolution: {settings.media_resolution}
- Prompt version: {settings.prompt_version}

Pass 1 audio transcript for temporal grounding:
```text
{transcript_context or "[no transcript text available]"}
```

Return only the markdown body. Do not include YAML frontmatter.

Required markdown structure:

## [MM:SS] Concise moment heading

**Spoken content:** faithful summary or transcript-aligned excerpt of what is being said at this timestamp.

**On-screen content:** slide text, code, equations, diagrams, tables, terminal output, whiteboard content, or visible UI state at this timestamp.

Visual reference rule:
- When a slide, diagram, chart, equation, code block, table, whiteboard, or UI state is useful for downstream extraction, emit an inline image placeholder using this exact form:
  ![descriptive alt text](video-frame://{video.id}@MM:SS)
- Use H:MM:SS in the URI timestamp when needed.
- The alt text must briefly name the visual type and key labels, for example: ![diagram: tokenization pipeline with normalization, vectorization, classifier](video-frame://{video.id}@12:34)
- Do not emit JSON for diagrams. The downstream Qwen-VL phase will convert frame placeholders to structured JSON later.

Behavior rules:
- Use the Pass 1 transcript as the timing anchor, but focus model capacity on visual reasoning.
- Preserve code blocks with fenced markdown.
- Preserve equations in readable markdown/LaTeX form.
- Do not invent content outside the video or outside the chunk window.
- Do not describe blank or repeated frames unless the visual content changes.
- Prefer timestamp sections that span the whole chunk/video, not a dense frame-by-frame log.
- If speech and visuals disagree, say so explicitly inside the relevant timestamp section.
"""


def gemini_request_material(
    *,
    video: VideoRef,
    media_source: str,
    pass1: Pass1Transcript,
    window: ChunkWindow,
    settings: GeminiSettings,
    prompt_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "provider": GEMINI_PROVIDER,
        "strategy": GEMINI_STRATEGY,
        "source_url": video.url,
        "gemini_media_source": media_source,
        "audio_transcript_sha256": pass1.transcript_sha256,
        "model": settings.model,
        "fps": settings.fps,
        "media_resolution": settings.media_resolution,
        "temperature": settings.temperature,
        "max_output_tokens": settings.max_output_tokens,
        "prompt_version": settings.prompt_version,
        "prompt_sha256": prompt_sha256,
        "chunk": {
            "index": window.index,
            "start_seconds": window.start_seconds,
            "end_seconds": window.end_seconds,
        },
    }


def normalize_model_markdown(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:markdown|md)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.rstrip() + "\n" if cleaned else ""


def stitch_chunk_markdown(chunks: list[GeminiChunkResult]) -> str:
    parts: list[str] = []
    for chunk in sorted(chunks, key=lambda item: item.window.index):
        body = chunk.markdown.strip()
        if not body:
            continue
        parts.append(body)
    return "\n\n".join(parts).strip() + "\n" if parts else ""


SECTION_HEADING_RE = re.compile(
    r"^##\s+(?:\[(?P<bracketed>(?:\d{1,2}:)?[0-5]?\d:[0-5]\d)\]|(?P<bare>(?:\d{1,2}:)?[0-5]?\d:[0-5]\d))",
    re.MULTILINE,
)


def merge_transcript_into_markdown(
    markdown: str,
    response: base_video.VideoTranscriptResponse,
) -> str:
    if not markdown.strip() or not response.segments:
        return markdown

    matches = list(SECTION_HEADING_RE.finditer(markdown))
    if not matches:
        return markdown

    parts: list[str] = []
    cursor = 0
    for index, match in enumerate(matches):
        section_start = match.start()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        section = markdown[section_start:section_end]
        start_seconds = timestamp_to_seconds(match.group("bracketed") or match.group("bare") or "")
        next_seconds = (
            timestamp_to_seconds(
                matches[index + 1].group("bracketed") or matches[index + 1].group("bare") or ""
            )
            if index + 1 < len(matches)
            else response.duration_seconds
        )
        transcript_block = transcript_markdown_for_range(response, start_seconds, next_seconds)
        if transcript_block:
            section = replace_spoken_content(section, transcript_block)
        parts.append(markdown[cursor:section_start])
        parts.append(section)
        cursor = section_end
    parts.append(markdown[cursor:])
    return "".join(parts).rstrip() + "\n"


def timestamp_to_seconds(value: str) -> float:
    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return float(minutes * 60 + seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return float(hours * 3600 + minutes * 60 + seconds)
    return 0.0


def transcript_markdown_for_range(
    response: base_video.VideoTranscriptResponse,
    start_seconds: float,
    end_seconds: float | None,
) -> str:
    lines: list[str] = []
    for segment in response.segments:
        text = " ".join(segment.text.split())
        if not text:
            continue
        segment_start = segment.start_seconds
        if segment_start is None:
            lines.append(f"- {text}")
            continue
        if segment_start < start_seconds:
            continue
        if end_seconds is not None and segment_start >= end_seconds:
            continue
        lines.append(f"- [{timestamp_label(segment_start)}] {text}")
    return "\n".join(lines)


def replace_spoken_content(section: str, transcript_block: str) -> str:
    replacement = f"**Spoken content:**\n{transcript_block}\n"
    spoken = re.search(r"\*\*Spoken content:\*\*", section, flags=re.IGNORECASE)
    onscreen = re.search(r"\*\*On-screen content:\*\*", section, flags=re.IGNORECASE)
    if spoken and onscreen and spoken.start() < onscreen.start():
        return section[: spoken.start()] + replacement + "\n" + section[onscreen.start() :]
    if onscreen:
        return section[: onscreen.start()] + replacement + "\n" + section[onscreen.start() :]
    if spoken:
        return section[: spoken.start()] + replacement
    return section.rstrip() + "\n\n" + replacement


def parse_markdown_timestamps(markdown: str) -> list[float]:
    timestamps: list[float] = []
    pattern = re.compile(
        r"(?<![\d:])(?:(?P<hours>\d{1,2}):)?(?P<minutes>[0-5]?\d):(?P<seconds>[0-5]\d)(?:\.\d+)?(?![\d:])"
    )
    for match in pattern.finditer(markdown):
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes"))
        seconds = int(match.group("seconds"))
        timestamps.append(hours * 3600 + minutes * 60 + seconds)
    return timestamps


def gate_report(
    *,
    video: VideoRef,
    pass1: Pass1Transcript,
    markdown: str,
    chunks: list[GeminiChunkResult],
    settings: GeminiSettings,
) -> dict[str, Any]:
    duration = pass1.response.duration_seconds
    words = word_count(markdown)
    timestamps = parse_markdown_timestamps(markdown)
    max_timestamp = max(timestamps) if timestamps else None
    title_similarity = (
        normalized_title_similarity(video.title, pass1.response.title)
        if pass1.response.title
        else None
    )
    failures: list[str] = []
    warnings: list[str] = []

    if not markdown.strip():
        failures.append("empty_output")
    elif words < settings.min_words:
        warnings.append("short_output")

    if not timestamps:
        failures.append("missing_timestamps")

    if duration is None:
        warnings.append("duration_unknown")
    elif duration <= 0:
        failures.append("invalid_duration")
    elif max_timestamp is not None:
        min_expected = duration * settings.timestamp_span_min_ratio
        if duration > 120 and max_timestamp < min_expected:
            failures.append("timestamp_span_short")
        if max_timestamp > duration + settings.timestamp_span_tolerance_seconds:
            warnings.append("timestamp_beyond_duration")

    if title_similarity is None:
        warnings.append("source_title_unknown")
    elif title_similarity < settings.title_similarity_min:
        warnings.append("title_mismatch")

    if markdown_image_count(markdown) == 0:
        warnings.append("no_visual_placeholders")

    if any(not chunk.markdown.strip() for chunk in chunks):
        failures.append("empty_chunk_output")

    return {
        "status": "failed_gate" if failures else "passed_with_warnings" if warnings else "passed",
        "failures": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
        "provider": GEMINI_PROVIDER,
        "strategy": GEMINI_STRATEGY,
        "requested_title": video.title,
        "source_title": pass1.response.title,
        "title_similarity": title_similarity,
        "duration_seconds": duration,
        "timestamp_count": len(timestamps),
        "max_timestamp_seconds": max_timestamp,
        "word_count": words,
        "image_count": markdown_image_count(markdown),
        "chunk_count": len(chunks),
        "chunk_cache_statuses": [chunk.cache_status for chunk in chunks],
        "model": settings.model,
        "fps": settings.fps,
        "media_resolution": settings.media_resolution,
    }


def normalized_title_similarity(left: str, right: str) -> float:
    left_tokens = title_tokens(left)
    right_tokens = title_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(intersection) / len(union)


def title_tokens(value: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "com",
        "de",
        "do",
        "da",
        "das",
        "dos",
        "e",
        "em",
        "for",
        "in",
        "o",
        "of",
        "os",
        "the",
        "to",
        "um",
        "uma",
        "with",
    }
    tokens = {
        token
        for token in re.findall(r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9]+", value.lower())
        if len(token) > 1 and token not in stopwords
    }
    return tokens


def usage_totals(chunks: list[GeminiChunkResult]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for chunk in chunks:
        for key, value in chunk.usage.items():
            if isinstance(value, int):
                totals[key] = totals.get(key, 0) + value
    return totals


def estimated_video_input_tokens(duration_seconds: float | None, *, fps: float, media_resolution: str) -> int | None:
    if duration_seconds is None:
        return None
    frame_tokens = 66 if media_resolution == "low" else 258
    audio_tokens_per_second = 32
    return int(duration_seconds * (audio_tokens_per_second + (fps * frame_tokens)))


def render_markdown(
    *,
    video: VideoRef,
    pass1: Pass1Transcript,
    markdown_body: str,
    settings: GeminiSettings,
    cache_keys: list[str],
    gate: dict[str, Any],
    usage: dict[str, int],
    fetched_at: str,
) -> str:
    warnings = list(gate.get("warnings", []))
    failures = list(gate.get("failures", []))
    body = markdown_body.rstrip()
    source_url = video.original_url or video.url
    frontmatter = {
        "id": video.id,
        "title": video.title,
        "source_url": source_url,
        "fetch_url": video.url,
        "resolved_url": pass1.response.final_url,
        "firecrawl_title": None,
        "description": None,
        "fetched_at": fetched_at,
        "provider": GEMINI_PROVIDER,
        "strategy": GEMINI_STRATEGY,
        "cache_key": cache_keys[0] if len(cache_keys) == 1 else None,
        "cache_keys": cache_keys,
        "gemini_model": settings.model,
        "gemini_media_resolution": settings.media_resolution,
        "gemini_fps": settings.fps,
        "prompt_version": settings.prompt_version,
        "duration_seconds": pass1.response.duration_seconds,
        "transcript_source": pass1.response.transcript_source,
        "transcript_sha256": pass1.transcript_sha256,
        "word_count": word_count(body),
        "char_count": len(body),
        "content_sha256": sha256_text(body),
        "image_count": markdown_image_count(body),
        "link_count": markdown_link_count(body),
        "total_token_count": usage.get("total_token_count"),
        "estimated_input_tokens": estimated_video_input_tokens(
            pass1.response.duration_seconds,
            fps=settings.fps,
            media_resolution=settings.media_resolution,
        ),
        "warnings": warnings,
        "gate_status": gate.get("status"),
        "gate_failures": failures,
        "route_notes": [],
    }
    return f"{yaml_frontmatter(frontmatter)}\n\n{body}\n"


def artifact_paths(output_root: Path, video: VideoRef) -> dict[str, Path]:
    video_dir = output_root / video.id
    return {
        "dir": video_dir,
        "markdown": video_dir / f"{video.id}-{slugify(video.title)}.md",
        "request": video_dir / "request.json",
        "raw_response": video_dir / "raw_response.json",
        "metadata": video_dir / "metadata.json",
        "gate_report": video_dir / "gate_report.json",
        "manifest": video_dir / "source_manifest.json",
        "transcript": video_dir / "transcript.json",
        "usage": video_dir / "gemini_usage.json",
        "captions": video_dir / "captions.vtt",
        "audio_manifest": video_dir / "audio_manifest.json",
    }


def existing_markdown_path(output_root: Path, video: VideoRef) -> Path | None:
    video_dir = output_root / video.id
    if not video_dir.exists():
        return None
    existing = sorted(video_dir.glob("*.md"))
    return existing[0] if existing else None


def persist_artifacts(
    *,
    video: VideoRef,
    output_root: Path,
    pass1: Pass1Transcript,
    chunks: list[GeminiChunkResult],
    settings: GeminiSettings,
) -> Result:
    paths = artifact_paths(output_root, video)
    paths["dir"].mkdir(parents=True, exist_ok=True)

    fetched_at = iso_utc_now()
    markdown_body = merge_transcript_into_markdown(
        stitch_chunk_markdown(chunks),
        pass1.response,
    )
    gate = gate_report(
        video=video,
        pass1=pass1,
        markdown=markdown_body,
        chunks=chunks,
        settings=settings,
    )
    totals = usage_totals(chunks)
    cache_keys = [chunk.cache_key for chunk in chunks]
    markdown = render_markdown(
        video=video,
        pass1=pass1,
        markdown_body=markdown_body,
        settings=settings,
        cache_keys=cache_keys,
        gate=gate,
        usage=totals,
        fetched_at=fetched_at,
    )

    transcript_payload = {
        "schema_version": "1.0",
        "transcript_source": pass1.response.transcript_source,
        "caption_language": pass1.response.caption_language,
        "duration_seconds": pass1.response.duration_seconds,
        "transcript_sha256": pass1.transcript_sha256,
        "segments": [segment_as_dict(segment) for segment in pass1.response.segments],
        "text": transcript_text(pass1.response),
        "cache_key": pass1.cache_key,
        "cache_status": pass1.cache_status,
    }
    usage_payload = {
        "schema_version": "1.0",
        "totals": totals,
        "chunks": [
            {
                "index": chunk.window.index,
                "start_seconds": chunk.window.start_seconds,
                "end_seconds": chunk.window.end_seconds,
                "cache_key": chunk.cache_key,
                "cache_status": chunk.cache_status,
                "usage": chunk.usage,
                "model_version": chunk.model_version,
            }
            for chunk in chunks
        ],
    }
    request_payload = {
        "schema_version": "1.0",
        "provider": GEMINI_PROVIDER,
        "strategy": GEMINI_STRATEGY,
        "settings": settings_as_dict(settings),
        "pass1_cache_key": pass1.cache_key,
        "pass1_transcript_sha256": pass1.transcript_sha256,
        "chunks": [chunk.request for chunk in chunks],
        "credential_fields_redacted": True,
    }
    response_payload = {
        "schema_version": "1.0",
        "provider": GEMINI_PROVIDER,
        "chunks": [
            {
                "index": chunk.window.index,
                "start_seconds": chunk.window.start_seconds,
                "end_seconds": chunk.window.end_seconds,
                "cache_key": chunk.cache_key,
                "cache_status": chunk.cache_status,
                "markdown": chunk.markdown,
                "response": chunk.response,
            }
            for chunk in chunks
        ],
    }
    metadata = {
        "id": video.id,
        "title": video.title,
        "source_url": video.original_url or video.url,
        "fetch_url": video.url,
        "final_url": pass1.response.final_url,
        "provider": GEMINI_PROVIDER,
        "strategy": GEMINI_STRATEGY,
        "model": settings.model,
        "fps": settings.fps,
        "media_resolution": settings.media_resolution,
        "prompt_version": settings.prompt_version,
        "duration_seconds": pass1.response.duration_seconds,
        "transcript_source": pass1.response.transcript_source,
        "transcript_segment_count": len(pass1.response.segments),
        "transcript_sha256": pass1.transcript_sha256,
        "pass1_cache_key": pass1.cache_key,
        "pass1_cache_status": pass1.cache_status,
        "gemini_cache_keys": cache_keys,
        "gemini_cache_statuses": [chunk.cache_status for chunk in chunks],
        "estimated_input_tokens": estimated_video_input_tokens(
            pass1.response.duration_seconds,
            fps=settings.fps,
            media_resolution=settings.media_resolution,
        ),
        "usage_totals": totals,
        "word_count": word_count(markdown_body),
        "image_count": markdown_image_count(markdown_body),
        "warnings": gate.get("warnings", []),
        "gate_status": gate.get("status"),
        "gate_failures": gate.get("failures", []),
        "captured_at": fetched_at,
    }
    artifacts = {
        "markdown": paths["markdown"].name,
        "metadata": paths["metadata"].name,
        "request": paths["request"].name,
        "raw_response": paths["raw_response"].name,
        "gate_report": paths["gate_report"].name,
        "transcript_json": paths["transcript"].name,
        "gemini_usage": paths["usage"].name,
    }
    if pass1.response.raw_captions:
        artifacts["captions_vtt"] = paths["captions"].name
    if pass1.response.audio_manifest:
        artifacts["audio_manifest"] = paths["audio_manifest"].name
    manifest = {
        "schema_version": "1.0",
        "id": video.id,
        "resource_kind": "video",
        "original_url": video.original_url or video.url,
        "fetch_url": video.url,
        "final_url": pass1.response.final_url,
        "source_identity": {
            "title": pass1.response.title or video.title,
            "url": pass1.response.final_url or video.url,
        },
        "provider": GEMINI_PROVIDER,
        "strategy": GEMINI_STRATEGY,
        "model": settings.model,
        "fps": settings.fps,
        "media_resolution": settings.media_resolution,
        "prompt_version": settings.prompt_version,
        "duration_seconds": pass1.response.duration_seconds,
        "transcript_source": pass1.response.transcript_source,
        "transcript_segment_count": len(pass1.response.segments),
        "transcript_sha256": pass1.transcript_sha256,
        "gemini_cache_keys": cache_keys,
        "gemini_cache_statuses": [chunk.cache_status for chunk in chunks],
        "word_count": word_count(markdown_body),
        "image_count": markdown_image_count(markdown_body),
        "usage_totals": totals,
        "artifacts": artifacts,
        "warnings": gate.get("warnings", []),
        "gate_status": gate.get("status"),
        "gate_failures": gate.get("failures", []),
        "content_sha256": sha256_text(markdown_body),
        "metadata_sha256": sha256_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True)),
        "captured_at": fetched_at,
        "credential_fields_redacted": True,
    }

    atomic_write_text(paths["markdown"], markdown)
    atomic_write_text(paths["transcript"], json.dumps(transcript_payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["request"], json.dumps(request_payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["raw_response"], json.dumps(response_payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["usage"], json.dumps(usage_payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["metadata"], json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["gate_report"], json.dumps(gate, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["manifest"], json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    if pass1.response.raw_captions:
        atomic_write_text(paths["captions"], pass1.response.raw_captions)
    if pass1.response.audio_manifest:
        atomic_write_text(
            paths["audio_manifest"],
            json.dumps(pass1.response.audio_manifest, ensure_ascii=False, indent=2) + "\n",
        )

    gate_failures = list(gate.get("failures", []))
    warnings = list(gate.get("warnings", [])) + pass1.warnings
    status = "acquisition_failed" if gate_failures else "saved_with_warnings" if warnings else "saved"
    return Result(
        video_id=video.id,
        title=video.title,
        url=video.url,
        status=status,
        output_path=str(paths["markdown"]),
        artifact_dir=str(paths["dir"]),
        manifest_path=str(paths["manifest"]),
        gate_failures=gate_failures,
        warnings=dedupe_preserving_order(warnings),
        cache_keys=cache_keys,
        transcript_cache_key=pass1.cache_key,
        transcript_source=pass1.response.transcript_source,
        model=settings.model,
        fps=settings.fps,
        media_resolution=settings.media_resolution,
        duration_seconds=pass1.response.duration_seconds,
        word_count=word_count(markdown_body),
        image_count=markdown_image_count(markdown_body),
        total_token_count=totals.get("total_token_count", 0),
    )


def persist_failure_artifacts(
    *,
    video: VideoRef,
    output_root: Path,
    settings: GeminiSettings,
    error: str,
    gate_failures: list[str],
) -> Result:
    paths = artifact_paths(output_root, video)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    captured_at = iso_utc_now()
    failures = sorted(set(gate_failures or ["acquisition_failed"]))
    gate = {
        "status": "failed_gate",
        "failures": failures,
        "warnings": [],
        "provider": GEMINI_PROVIDER,
        "strategy": GEMINI_STRATEGY,
        "requested_title": video.title,
        "requested_url": video.original_url or video.url,
        "fetch_url": video.url,
        "error": error,
        "model": settings.model,
        "fps": settings.fps,
        "media_resolution": settings.media_resolution,
        "captured_at": captured_at,
    }
    metadata = {
        "id": video.id,
        "title": video.title,
        "source_url": video.original_url or video.url,
        "fetch_url": video.url,
        "provider": GEMINI_PROVIDER,
        "strategy": GEMINI_STRATEGY,
        "model": settings.model,
        "fps": settings.fps,
        "media_resolution": settings.media_resolution,
        "prompt_version": settings.prompt_version,
        "warnings": [],
        "gate_status": "failed_gate",
        "gate_failures": failures,
        "error": error,
        "captured_at": captured_at,
    }
    manifest = {
        "schema_version": "1.0",
        "id": video.id,
        "resource_kind": "video",
        "original_url": video.original_url or video.url,
        "fetch_url": video.url,
        "provider": GEMINI_PROVIDER,
        "strategy": GEMINI_STRATEGY,
        "model": settings.model,
        "fps": settings.fps,
        "media_resolution": settings.media_resolution,
        "prompt_version": settings.prompt_version,
        "artifacts": {
            "metadata": paths["metadata"].name,
            "gate_report": paths["gate_report"].name,
        },
        "warnings": [],
        "gate_status": "failed_gate",
        "gate_failures": failures,
        "error": error,
        "captured_at": captured_at,
        "credential_fields_redacted": True,
    }
    atomic_write_text(paths["gate_report"], json.dumps(gate, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["metadata"], json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["manifest"], json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return Result(
        video_id=video.id,
        title=video.title,
        url=video.url,
        status="acquisition_failed",
        artifact_dir=str(paths["dir"]),
        manifest_path=str(paths["manifest"]),
        gate_failures=failures,
        error=error,
        model=settings.model,
        fps=settings.fps,
        media_resolution=settings.media_resolution,
    )


def settings_as_dict(settings: GeminiSettings) -> dict[str, Any]:
    return {
        "profile": settings.profile,
        "model": settings.model,
        "fps": settings.fps,
        "media_resolution": settings.media_resolution,
        "temperature": settings.temperature,
        "max_output_tokens": settings.max_output_tokens,
        "prompt_version": settings.prompt_version,
        "chunk_longer_than_seconds": settings.chunk_longer_than_seconds,
        "chunk_seconds": settings.chunk_seconds,
        "chunk_overlap_seconds": settings.chunk_overlap_seconds,
        "max_transcript_chars_per_chunk": settings.max_transcript_chars_per_chunk,
        "min_words": settings.min_words,
        "timestamp_span_tolerance_seconds": settings.timestamp_span_tolerance_seconds,
        "timestamp_span_min_ratio": settings.timestamp_span_min_ratio,
        "title_similarity_min": settings.title_similarity_min,
    }


def result_from_existing(video: VideoRef, existing: Path) -> Result:
    manifest_path = existing.parent / "source_manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = load_json(manifest_path)
        except SystemExit:
            manifest = {}
    return Result(
        video_id=video.id,
        title=video.title,
        url=video.url,
        status="skipped",
        output_path=str(existing),
        artifact_dir=str(existing.parent),
        manifest_path=str(manifest_path) if manifest_path.exists() else None,
        gate_failures=list(manifest.get("gate_failures", [])) if isinstance(manifest.get("gate_failures"), list) else [],
        warnings=list(manifest.get("warnings", [])) if isinstance(manifest.get("warnings"), list) else [],
        cache_keys=list(manifest.get("gemini_cache_keys", [])) if isinstance(manifest.get("gemini_cache_keys"), list) else [],
        transcript_source=str(manifest.get("transcript_source") or ""),
        model=str(manifest.get("model") or ""),
        fps=optional_float(manifest.get("fps")),
        media_resolution=str(manifest.get("media_resolution") or ""),
        duration_seconds=optional_float(manifest.get("duration_seconds")),
        word_count=int(manifest.get("word_count", 0) or 0),
        image_count=int(manifest.get("image_count", 0) or 0),
        total_token_count=int((manifest.get("usage_totals") or {}).get("total_token_count", 0))
        if isinstance(manifest.get("usage_totals"), dict)
        else 0,
    )


def _extract_video_gemini(
    video: VideoRef,
    *,
    input_dir: Path,
    output_root: Path,
    cache_root: Path,
    settings: GeminiSettings,
    force: bool,
    refresh_cache: bool,
    force_pass1: bool,
    caption_fetcher: Any,
    transcriber: TimestampedAudioTranscriber,
    gemini_client: GeminiVideoClient,
    stt_semaphore: threading.Semaphore | None,
    gemini_semaphore: threading.Semaphore | None,
    chunk_workers: int,
) -> Result:
    video = resolve_playlist_video_ref(video)
    if not force:
        existing = existing_markdown_path(output_root, video)
        if existing is not None:
            return result_from_existing(video, existing)

    artifact_dir = output_root / video.id
    pass1 = acquire_pass1_transcript(
        video,
        input_dir=input_dir,
        artifact_dir=artifact_dir,
        cache_root=cache_root,
        force_pass1=force_pass1,
        caption_fetcher=caption_fetcher,
        transcriber=transcriber,
        stt_semaphore=stt_semaphore,
    )
    windows = build_chunks(pass1.response.duration_seconds, settings)

    if len(windows) == 1:
        chunks = [
            gemini_client.generate_chunk(
                video=video,
                input_dir=input_dir,
                pass1=pass1,
                window=windows[0],
                settings=settings,
                cache_root=cache_root,
                refresh_cache=refresh_cache,
                gemini_semaphore=gemini_semaphore,
            )
        ]
    else:
        chunks_by_index: dict[int, GeminiChunkResult] = {}
        workers = max(1, min(chunk_workers, len(windows)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    gemini_client.generate_chunk,
                    video=video,
                    input_dir=input_dir,
                    pass1=pass1,
                    window=window,
                    settings=settings,
                    cache_root=cache_root,
                    refresh_cache=refresh_cache,
                    gemini_semaphore=gemini_semaphore,
                ): window.index
                for window in windows
            }
            for future in as_completed(futures):
                chunks_by_index[futures[future]] = future.result()
        chunks = [chunks_by_index[index] for index in sorted(chunks_by_index)]

    return persist_artifacts(
        video=video,
        output_root=output_root,
        pass1=pass1,
        chunks=chunks,
        settings=settings,
    )


def extract_video(video: VideoRef, *args, **kwargs) -> Result:
    """Dispatch old fallback-chain calls to the legacy extractor."""
    if "settings" not in kwargs:
        return base_video.extract_video(video, *args, **kwargs)
    return _extract_video_gemini(video, *args, **kwargs)


def result_event(result: Result) -> dict[str, Any]:
    return {
        "timestamp": iso_utc_now(),
        "id": result.video_id,
        "title": result.title,
        "url": result.url,
        "status": result.status,
        "output_path": result.output_path,
        "artifact_dir": result.artifact_dir,
        "manifest_path": result.manifest_path,
        "gate_failures": result.gate_failures,
        "warnings": result.warnings,
        "error": result.error,
        "gemini_cache_keys": result.cache_keys,
        "transcript_cache_key": result.transcript_cache_key,
        "transcript_source": result.transcript_source,
        "model": result.model,
        "fps": result.fps,
        "media_resolution": result.media_resolution,
        "duration_seconds": result.duration_seconds,
        "word_count": result.word_count,
        "image_count": result.image_count,
        "total_token_count": result.total_token_count,
    }


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def run_batch(args: argparse.Namespace, videos: list[VideoRef], settings: GeminiSettings) -> list[Result]:
    output_root = args.output
    cache_root = args.cache
    output_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)
    log_path = output_root / "run_log.jsonl"
    log_path.write_text("", encoding="utf-8")

    total = len(videos)
    worker_count = max(1, min(args.concurrency, total))
    stt_semaphore = threading.Semaphore(args.stt_workers)
    gemini_semaphore = threading.Semaphore(args.gemini_workers)
    caption_fetcher = base_video.YtDlpCaptionFetcher()
    transcriber = TimestampedAudioTranscriber()
    gemini_client = GeminiVideoClient(settings)
    print_lock = threading.Lock()
    results_by_index: dict[int, Result] = {}

    def process(index: int, video: VideoRef) -> Result:
        with print_lock:
            print(
                f"[{index}/{total}] id={video.id} acquire {video.url} "
                f"model={settings.model} fps={settings.fps} resolution={settings.media_resolution}",
                flush=True,
            )
        try:
            return extract_video(
                video,
                input_dir=args.input.parent,
                output_root=output_root,
                cache_root=cache_root,
                settings=settings,
                force=args.force,
                refresh_cache=args.refresh_cache,
                force_pass1=args.force_pass1,
                caption_fetcher=caption_fetcher,
                transcriber=transcriber,
                gemini_client=gemini_client,
                stt_semaphore=stt_semaphore,
                gemini_semaphore=gemini_semaphore,
                chunk_workers=args.chunk_workers,
            )
        except AcquisitionFailure as exc:
            return persist_failure_artifacts(
                video=video,
                output_root=output_root,
                settings=settings,
                error=str(exc),
                gate_failures=exc.gate_failures,
            )
        except Exception as exc:
            return persist_failure_artifacts(
                video=video,
                output_root=output_root,
                settings=settings,
                error=f"{type(exc).__name__}: {exc}",
                gate_failures=["unexpected_exception"],
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
                if result.status == "skipped":
                    print(f"[skip] id={result.video_id} existing={result.output_path}", flush=True)
                elif result.status == "acquisition_failed":
                    print(
                        f"[fail] id={result.video_id} failures={','.join(result.gate_failures) or 'none'} "
                        f"error={result.error or ''}",
                        flush=True,
                    )
                else:
                    print(
                        f"[done] id={result.video_id} status={result.status} "
                        f"words={result.word_count} images={result.image_count} "
                        f"tokens={result.total_token_count} warnings={','.join(result.warnings) or 'none'}",
                        flush=True,
                    )

    return [results_by_index[index] for index in range(total)]


def build_summary(results: list[Result], selected_count: int, output_root: Path, cache_root: Path) -> dict[str, Any]:
    counts: dict[str, int] = {}
    warning_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    total_tokens = 0
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
        total_tokens += result.total_token_count
        for warning in result.warnings:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
        for failure in result.gate_failures:
            failure_counts[failure] = failure_counts.get(failure, 0) + 1
    return {
        "timestamp": iso_utc_now(),
        "selected": selected_count,
        "counts": dict(sorted(counts.items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "failure_counts": dict(sorted(failure_counts.items())),
        "failed_ids": [result.video_id for result in results if result.status == "acquisition_failed"],
        "total_token_count": total_tokens,
        "output_root": str(output_root),
        "cache_root": str(cache_root),
        "results": [result_event(result) for result in results],
    }


def print_summary(summary: dict[str, Any]) -> None:
    print("\nSummary")
    print(f"  selected: {summary['selected']}")
    for status, count in summary["counts"].items():
        print(f"  {status}: {count}")
    print(f"  total_token_count: {summary['total_token_count']}")
    print(f"  output_root: {summary['output_root']}")
    print(f"  cache_root: {summary['cache_root']}")
    if summary["warning_counts"]:
        print("  warning_counts:")
        for warning, count in summary["warning_counts"].items():
            print(f"    {warning}: {count}")
    if summary["failure_counts"]:
        print("  failure_counts:")
        for failure, count in summary["failure_counts"].items():
            print(f"    {failure}: {count}")
    if summary["failed_ids"]:
        print(f"  failed_ids: {', '.join(summary['failed_ids'])}")


def settings_from_config(config: dict[str, Any], args: argparse.Namespace) -> GeminiSettings:
    profile_name = args.profile or str(config.get("default_profile") or "triage")
    profiles = config.get("profiles") if isinstance(config.get("profiles"), dict) else {}
    profile = profiles.get(profile_name) if isinstance(profiles.get(profile_name), dict) else {}
    if not profile and profile_name:
        raise SystemExit(f"Profile not found in config: {profile_name}")

    model = args.model or str(profile.get("model") or "gemini-2.5-flash")
    fps = args.fps if args.fps is not None else float(profile.get("fps", 0.33))
    media_resolution = args.media_resolution or str(profile.get("media_resolution") or "low")
    temperature = args.temperature if args.temperature is not None else float(profile.get("temperature", 0.2))
    max_output_tokens = (
        args.max_output_tokens
        if args.max_output_tokens is not None
        else int(profile.get("max_output_tokens", 8192))
    )
    chunk_longer_than_seconds = (
        args.chunk_longer_than_seconds
        if args.chunk_longer_than_seconds is not None
        else int(config.get("chunk_longer_than_seconds", 3600))
    )
    chunk_seconds = (
        args.chunk_seconds
        if args.chunk_seconds is not None
        else int(config.get("chunk_seconds", 1800))
    )
    chunk_overlap_seconds = (
        args.chunk_overlap_seconds
        if args.chunk_overlap_seconds is not None
        else int(config.get("chunk_overlap_seconds", 5))
    )
    max_transcript_chars_per_chunk = (
        args.max_transcript_chars_per_chunk
        if args.max_transcript_chars_per_chunk is not None
        else int(config.get("max_transcript_chars_per_chunk", 60000))
    )
    if fps <= 0:
        raise SystemExit("--fps must be > 0")
    if max_output_tokens < 512:
        raise SystemExit("--max-output-tokens must be >= 512")
    if chunk_longer_than_seconds < 60:
        raise SystemExit("--chunk-longer-than-seconds must be >= 60")
    if chunk_seconds < 60:
        raise SystemExit("--chunk-seconds must be >= 60")
    if chunk_overlap_seconds < 0:
        raise SystemExit("--chunk-overlap-seconds must be >= 0")
    if max_transcript_chars_per_chunk < 1000:
        raise SystemExit("--max-transcript-chars-per-chunk must be >= 1000")
    media_resolution_enum(media_resolution)

    return GeminiSettings(
        profile=profile_name,
        model=model,
        fps=fps,
        media_resolution=media_resolution.strip().lower(),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        prompt_version=str(args.prompt_version or config.get("prompt_version") or PROMPT_VERSION),
        chunk_longer_than_seconds=chunk_longer_than_seconds,
        chunk_seconds=chunk_seconds,
        chunk_overlap_seconds=chunk_overlap_seconds,
        max_transcript_chars_per_chunk=max_transcript_chars_per_chunk,
        min_words=int(config.get("min_words", 150)),
        timestamp_span_tolerance_seconds=int(config.get("timestamp_span_tolerance_seconds", 180)),
        timestamp_span_min_ratio=float(config.get("timestamp_span_min_ratio", 0.65)),
        title_similarity_min=float(config.get("title_similarity_min", 0.45)),
        upload_poll_seconds=float(config.get("upload_poll_seconds", 2)),
        upload_timeout_seconds=int(config.get("upload_timeout_seconds", 600)),
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Acquire full video markdown with Pass 1 audio grounding and Pass 2 "
            "Gemini multimodal extraction."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--only", help="Comma-separated video ids to process.")
    parser.add_argument("--profile", help="Profile from config.json, e.g. triage or dense.")
    parser.add_argument("--model", help="Gemini model override.")
    parser.add_argument("--fps", type=float, help="Explicit video sampling FPS for Gemini.")
    parser.add_argument(
        "--media-resolution",
        choices=["low", "medium", "high", "unspecified"],
        help="Explicit Gemini media resolution.",
    )
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--prompt-version", help="Prompt version string included in the cache key.")
    parser.add_argument("--force", action="store_true", help="Rewrite output artifacts even if markdown exists.")
    parser.add_argument("--refresh-cache", action="store_true", help="Re-call Gemini instead of using Gemini cache.")
    parser.add_argument("--force-pass1", action="store_true", help="Refresh the Pass 1 audio transcript cache.")
    parser.add_argument("--concurrency", type=int, default=None, help="Concurrent videos.")
    parser.add_argument("--gemini-workers", type=int, default=None, help="Concurrent Gemini calls.")
    parser.add_argument("--stt-workers", type=int, default=None, help="Concurrent local Whisper jobs.")
    parser.add_argument("--chunk-workers", type=int, default=None, help="Concurrent chunks within a long video.")
    parser.add_argument("--chunk-longer-than-seconds", type=int, default=None)
    parser.add_argument("--chunk-seconds", type=int, default=None)
    parser.add_argument("--chunk-overlap-seconds", type=int, default=None)
    parser.add_argument("--max-transcript-chars-per-chunk", type=int, default=None)
    args = parser.parse_args(argv)

    config = load_config(args.config.resolve())
    args.concurrency = positive_int(
        args.concurrency,
        int(config.get("concurrency", 3)),
        "--concurrency",
    )
    args.gemini_workers = positive_int(
        args.gemini_workers,
        int(config.get("gemini_workers", 2)),
        "--gemini-workers",
    )
    args.stt_workers = positive_int(
        args.stt_workers,
        int(config.get("stt_workers", 2)),
        "--stt-workers",
    )
    args.chunk_workers = positive_int(
        args.chunk_workers,
        args.gemini_workers,
        "--chunk-workers",
    )
    args.input = args.input.resolve()
    args.output = args.output.resolve()
    args.cache = args.cache.resolve()
    args.config = args.config.resolve()
    args.loaded_config = config
    return args


def positive_int(value: int | None, default: int, label: str) -> int:
    result = default if value is None else value
    if result < 1:
        raise SystemExit(f"{label} must be >= 1")
    return result


def main(argv: list[str] | None = None) -> int:
    load_dotenv(SCRIPT_DIR / ".env")
    load_dotenv(REPO_ROOT / ".env")
    base_video._load_pipeline_env()
    args = parse_args(argv if argv is not None else sys.argv[1:])
    settings = settings_from_config(args.loaded_config, args)
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
        f"gemini_workers={args.gemini_workers}, stt_workers={args.stt_workers}, "
        f"profile={settings.profile}, model={settings.model}, fps={settings.fps}, "
        f"media_resolution={settings.media_resolution}, output={args.output}"
    )
    results = run_batch(args, videos, settings)
    summary = build_summary(
        results,
        selected_count=len(videos),
        output_root=args.output,
        cache_root=args.cache,
    )
    summary_path = args.output / "summary.json"
    atomic_write_text(summary_path, json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print_summary(summary)
    print(f"  summary_json: {summary_path}")
    print(f"  run_log_jsonl: {args.output / 'run_log.jsonl'}")
    return 1 if summary["failed_ids"] else 0


def serialize_model(value: Any) -> Any:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return {key: serialize_model(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_model(item) for item in value]
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return value.value
    return value


class maybe_semaphore:
    def __init__(self, semaphore: threading.Semaphore | None) -> None:
        self.semaphore = semaphore

    def __enter__(self) -> None:
        if self.semaphore is not None:
            self.semaphore.acquire()

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.semaphore is not None:
            self.semaphore.release()


def dedupe_preserving_order(values: list[str]) -> list[str]:
    return base_video._dedupe_preserving_order(values)


if __name__ == "__main__":
    raise SystemExit(main())
