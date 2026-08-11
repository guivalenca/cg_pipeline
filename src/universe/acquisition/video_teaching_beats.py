"""Visual-only video understanding as ordered, frame-grounded teaching beats.

The public Interface is intentionally small: an Adapter returns one
``TeachingBeatDocument``.  Provider transport, whole-video reasoning,
timestamp validation and representative-frame materialization stay inside the
Adapter Implementation.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

import psycopg
from psycopg.types.json import Jsonb

from universe.model_client import ModelClient, ModelError


PROMPT_REF = "video-teaching-beats/v001"
PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"
PROMPT_PATH = PROMPTS_DIR / "video-teaching-beats" / "v001.md"
TOOL_PATH = PROMPTS_DIR / "video-teaching-beats" / "tool-v001.json"
MAX_TEACHING_BEATS = 120


@dataclass(frozen=True)
class TeachingBeat:
    """One major idea taught through a temporally bounded visual state."""

    start_ms: int
    end_ms: int
    frame_ms: int
    heading: str
    explanation: str
    visible_text: str | None
    visual_description: str
    limitations: str | None


@dataclass(frozen=True)
class TeachingBeatFrame:
    timestamp_ms: int
    body: bytes
    mime_type: str
    filename: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


@dataclass(frozen=True)
class TeachingBeatDocument:
    """Ordered visual interpretation plus its representative frame evidence."""

    beats: tuple[TeachingBeat, ...]
    frames: tuple[TeachingBeatFrame, ...]
    requested_model: str
    response_model: str | None
    provider: str
    usage: Mapping[str, Any]
    duration_ms: int
    prompt_ref: str
    prompt_sha: str
    input_manifest_hash: str
    result_hash: str


class TeachingBeatAdapter(Protocol):
    def acquire_visual_teaching_beats(
        self, source_url: str, *, duration_seconds: float | None
    ) -> TeachingBeatDocument: ...


def prompt_stamp() -> tuple[str, str, str]:
    raw = PROMPT_PATH.read_bytes()
    return PROMPT_REF, hashlib.sha256(raw).hexdigest(), raw.decode("utf-8")


def load_tool() -> dict[str, Any]:
    function = json.loads(TOOL_PATH.read_text())
    return {"type": "function", "function": function}


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ModelError(f"visual teaching beat {field} must be text or null")
    return value.strip() or None


def parse_beats(
    arguments: Mapping[str, Any], *, duration_seconds: float | None
) -> tuple[TeachingBeat, ...]:
    if not isinstance(arguments, Mapping) or set(arguments) != {"beats"}:
        raise ModelError("report_visual_teaching_beats returned an invalid object")
    raw_beats = arguments["beats"]
    if not isinstance(raw_beats, list) or not raw_beats:
        raise ModelError("report_visual_teaching_beats returned no teaching beats")
    if len(raw_beats) > MAX_TEACHING_BEATS:
        raise ModelError("report_visual_teaching_beats returned too many teaching beats")
    expected = {
        "start_s",
        "end_s",
        "frame_s",
        "heading",
        "explanation",
        "visible_text",
        "visual_description",
        "limitations",
    }
    beats: list[TeachingBeat] = []
    maximum_ms = (
        int(round(duration_seconds * 1000))
        if isinstance(duration_seconds, (int, float)) and duration_seconds >= 0
        else None
    )
    for value in raw_beats:
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ModelError("visual teaching beat has an invalid shape")
        try:
            start_ms = int(value["start_s"]) * 1000
            end_ms = int(value["end_s"]) * 1000
            frame_ms = int(value["frame_s"]) * 1000
        except (TypeError, ValueError) as exc:
            raise ModelError("visual teaching beat timestamp is invalid") from exc
        if (
            start_ms < 0
            or end_ms < start_ms
            or not start_ms <= frame_ms <= end_ms
            or (maximum_ms is not None and end_ms > maximum_ms + 1000)
        ):
            raise ModelError("visual teaching beat timestamp is out of range")
        heading = _optional_text(value["heading"], "heading")
        explanation = _optional_text(value["explanation"], "explanation")
        visual_description = _optional_text(
            value["visual_description"], "visual_description"
        )
        if not heading or not explanation or not visual_description:
            raise ModelError("visual teaching beat has no educational description")
        beats.append(
            TeachingBeat(
                start_ms=start_ms,
                end_ms=end_ms,
                frame_ms=frame_ms,
                heading=heading,
                explanation=explanation,
                visible_text=_optional_text(value["visible_text"], "visible_text"),
                visual_description=visual_description,
                limitations=_optional_text(value["limitations"], "limitations"),
            )
        )
    ordered = tuple(beats)
    if any(
        current.start_ms < previous.start_ms
        for previous, current in zip(ordered, ordered[1:])
    ):
        raise ModelError("visual teaching beats are not in timeline order")
    if len({beat.frame_ms for beat in ordered}) != len(ordered):
        raise ModelError("visual teaching beats contain duplicate representative frames")
    return ordered


class OpenRouterGeminiTeachingBeatAdapter:
    """Gemini whole-video reasoning plus representative-frame materialization."""

    def __init__(self, *, client: ModelClient, frame_materializer) -> None:
        self.client = client
        self.frame_materializer = frame_materializer

    def acquire_visual_teaching_beats(
        self, source_url: str, *, duration_seconds: float | None
    ) -> TeachingBeatDocument:
        prompt_ref, prompt_sha, template = prompt_stamp()
        prompt = template.replace("{{source_url}}", source_url).replace(
            "{{duration_seconds}}",
            str(duration_seconds) if duration_seconds is not None else "unknown",
        )
        arguments, raw_usage, duration_ms = self.client.call_tool(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "video_url", "video_url": {"url": source_url}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            load_tool(),
        )
        beats = parse_beats(arguments, duration_seconds=duration_seconds)
        frames = tuple(
            self.frame_materializer(
                source_url, tuple(beat.frame_ms for beat in beats)
            )
        )
        response_model = raw_usage.get("response_model")
        provider = raw_usage.get("provider") or "openrouter"
        usage = {
            key: value
            for key, value in raw_usage.items()
            if key not in {"provider", "response_model"}
        }
        return validate_document(
            TeachingBeatDocument(
                beats=beats,
                frames=frames,
                requested_model=self.client.model,
                response_model=str(response_model) if response_model else None,
                provider=str(provider),
                usage=usage,
                duration_ms=duration_ms,
                prompt_ref=prompt_ref,
                prompt_sha=prompt_sha,
                input_manifest_hash=input_manifest_hash(
                    source_url,
                    duration_seconds=duration_seconds,
                    prompt_sha=prompt_sha,
                    requested_model=self.client.model,
                ),
                result_hash=teaching_beat_result_hash(beats),
            )
        )


class YtDlpTeachingBeatFrameMaterializer:
    """Download once and materialize exact PNG evidence for reported beats."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        ffmpeg_path: str | None = None,
        runner=None,
        temporary_root: str | Path | None = None,
    ) -> None:
        self.executable = executable or shutil.which("yt-dlp")
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        self.runner = runner or subprocess.run
        self.temporary_root = Path(temporary_root) if temporary_root else None

    def __call__(
        self, source_url: str, timestamps_ms: Sequence[int]
    ) -> tuple[TeachingBeatFrame, ...]:
        if not self.executable or not self.ffmpeg_path:
            raise RuntimeError("yt-dlp and ffmpeg are required for teaching beats")
        timestamps = tuple(int(value) for value in timestamps_ms)
        if not timestamps or any(value < 0 for value in timestamps):
            raise ValueError("teaching-beat frame timestamps are invalid")
        if len(set(timestamps)) != len(timestamps):
            raise ValueError("teaching-beat frame timestamps must be unique")
        if self.temporary_root:
            self.temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="concept-universe-teaching-beats-",
            dir=str(self.temporary_root) if self.temporary_root else None,
        ) as directory:
            root = Path(directory).resolve()
            template = root / "video.%(ext)s"
            try:
                self.runner(
                    [
                        self.executable,
                        "--no-playlist",
                        "-f",
                        "bv*[height<=720]/best[height<=720]",
                        "-o",
                        str(template),
                        source_url,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=1800,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise RuntimeError("teaching-beat video download failed") from exc
            candidates = [
                path
                for path in sorted(root.glob("video.*"))
                if path.is_file() and not path.name.endswith(".part")
            ]
            if len(candidates) != 1:
                raise RuntimeError("teaching-beat video download produced no unique file")
            source = candidates[0]
            frames: list[TeachingBeatFrame] = []
            for ordinal, timestamp_ms in enumerate(timestamps, 1):
                output = root / f"beat-{ordinal:04d}.png"
                try:
                    self.runner(
                        [
                            self.ffmpeg_path,
                            "-hide_banner",
                            "-loglevel",
                            "error",
                            "-y",
                            "-ss",
                            f"{timestamp_ms / 1000:.3f}",
                            "-i",
                            str(source),
                            "-frames:v",
                            "1",
                            "-vf",
                            "scale=-2:720",
                            str(output),
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=120,
                    )
                except (OSError, subprocess.SubprocessError) as exc:
                    raise RuntimeError("teaching-beat frame extraction failed") from exc
                if not output.is_file():
                    raise RuntimeError("teaching-beat frame extraction produced no image")
                body = output.read_bytes()
                if not body:
                    raise RuntimeError("teaching-beat frame extraction produced an empty image")
                frames.append(
                    TeachingBeatFrame(
                        timestamp_ms=timestamp_ms,
                        body=body,
                        mime_type="image/png",
                        filename=output.name,
                    )
                )
            return tuple(frames)


def validate_document(document: TeachingBeatDocument) -> TeachingBeatDocument:
    """Fail closed when provider output cannot ground every beat to one frame."""
    if not document.beats:
        raise ValueError("visual teaching-beat analysis returned no teaching beats")
    if len(document.beats) != len(document.frames):
        raise ValueError("every visual teaching beat must own one representative frame")
    previous_start = -1
    frame_timestamps: set[int] = set()
    frame_hashes: set[str] = set()
    for beat, frame in zip(document.beats, document.frames):
        if (
            beat.start_ms < 0
            or beat.end_ms < beat.start_ms
            or not (beat.start_ms <= beat.frame_ms <= beat.end_ms)
        ):
            raise ValueError("visual teaching beat has an invalid time range")
        if beat.start_ms < previous_start:
            raise ValueError("visual teaching beats must be ordered")
        if beat.frame_ms in frame_timestamps:
            raise ValueError("visual teaching beats must use distinct representative frames")
        if int(getattr(frame, "timestamp_ms", -1)) != beat.frame_ms:
            raise ValueError("visual teaching beat is bound to the wrong frame")
        frame_sha = str(getattr(frame, "sha256", ""))
        if not frame_sha or frame_sha in frame_hashes:
            raise ValueError("visual teaching beats must use distinct frame evidence")
        if not beat.heading.strip() or not beat.explanation.strip():
            raise ValueError("visual teaching beat has no educational explanation")
        previous_start = beat.start_ms
        frame_timestamps.add(beat.frame_ms)
        frame_hashes.add(frame_sha)
    return document


def input_manifest_hash(
    source_url: str,
    *,
    duration_seconds: float | None,
    prompt_sha: str,
    requested_model: str,
) -> str:
    material = {
        "source_url": source_url,
        "duration_seconds": duration_seconds,
        "prompt_sha": prompt_sha,
        "requested_model": requested_model,
        "video_sampling": "provider-default-1fps",
    }
    return hashlib.sha256(
        json.dumps(
            material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def teaching_beat_result_hash(beats: Sequence[TeachingBeat]) -> str:
    material = [
        {
            "start_ms": beat.start_ms,
            "end_ms": beat.end_ms,
            "frame_ms": beat.frame_ms,
            "heading": beat.heading,
            "explanation": beat.explanation,
            "visible_text": beat.visible_text,
            "visual_description": beat.visual_description,
            "limitations": beat.limitations,
        }
        for beat in beats
    ]
    return hashlib.sha256(
        json.dumps(
            material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def persist_teaching_beat_reading(
    conn: psycopg.Connection,
    *,
    markdown_artifact_id: str,
    document: TeachingBeatDocument,
) -> str:
    """Stamp the one paid visual interpretation before projecting its frames."""
    document = validate_document(document)
    call_id = (
        f"{markdown_artifact_id}:video-teaching-beats:"
        f"{document.prompt_sha[:16]}"
    )
    result = {
        "schema_version": "video-teaching-beats.v1",
        "beats": [asdict(beat) for beat in document.beats],
    }
    conn.execute(
        "INSERT INTO source_image_analysis_call"
        " (id, markdown_artifact_id, prompt_ref, prompt_sha, requested_model,"
        " input_manifest_hash, operation_kind, status, attempt_count,"
        " response_model, provider, usage, duration_ms, result, result_hash,"
        " diagnostics, finished_at)"
        " VALUES (%s, %s, %s, %s, %s, %s, 'video_teaching_beats', 'succeeded',"
        " 1, %s, %s, %s, %s, %s, %s, %s, now())"
        " ON CONFLICT (markdown_artifact_id, prompt_ref) DO NOTHING",
        (
            call_id,
            markdown_artifact_id,
            document.prompt_ref,
            document.prompt_sha,
            document.requested_model,
            document.input_manifest_hash,
            document.response_model,
            document.provider,
            Jsonb(dict(document.usage)),
            document.duration_ms,
            Jsonb(result),
            document.result_hash,
            Jsonb(
                {
                    "beat_count": len(document.beats),
                    "frame_count": len(document.frames),
                    "timestamp_resolution": "seconds",
                }
            ),
        ),
    )
    row = conn.execute(
        "SELECT id, operation_kind, result_hash FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s AND prompt_ref = %s",
        (markdown_artifact_id, document.prompt_ref),
    ).fetchone()
    if row != (call_id, "video_teaching_beats", document.result_hash):
        raise ValueError("visual teaching-beat reading conflicts with the ledger")
    return call_id
