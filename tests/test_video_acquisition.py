"""Tracer for YouTube captions through canonical clean Markdown publication."""

import json
import base64
import hashlib
import io
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from psycopg.types.json import Jsonb

from universe.acquisition import (
    image_jobs,
    job_lease,
    runner,
    source_cleanup_jobs,
    videos,
)
from universe.acquisition.source_images import (
    SourceImageAnalysis,
    SourceImageBatchResult,
)
from universe.acquisition.video_teaching_beats import (
    TeachingBeat,
    TeachingBeatDocument,
)
from universe.assets import LocalAssetStore
from universe.blocks import split_blocks
from universe.harness import PROMPTS_DIR, load_tool
from universe.model_client import ModelClient
from adalove_workbook import activity, write_adalove_workbook
from universe.syllabus import import_workbook
from universe.web.app import create_app


VTT = """WEBVTT

00:00:00.000 --> 00:00:03.000
Hello.

00:00:03.200 --> 00:00:07.000
This lesson stays exact.

00:01:10.000 --> 00:01:15.000
Later segment.
"""


def test_adapter_url_repairs_a_legacy_textual_query_identity():
    identity = {
        "kind": "video",
        "provider": "youtube",
        "video_id": (
            "h4gw6gCP5ls e list=PL9iw99lS3Prg0hPSCiOz9AXeEmj8W8fL8 "
            "e index=14 e t=49s"
        ),
    }

    assert videos.youtube_url(identity) == (
        "https://www.youtube.com/watch?v=h4gw6gCP5ls"
    )


class FakeYouTubeAdapter:
    def __init__(self) -> None:
        self.stt_calls = 0

    def probe(self, _source_url: str) -> videos.VideoMetadata:
        return videos.VideoMetadata(
            title="Captioned lesson",
            channel="Publisher",
            duration_seconds=75.0,
            uploaded_caption_languages=("en",),
        )

    def download_uploaded_caption(
        self, _source_url: str, *, language: str
    ) -> videos.CaptionDownload:
        assert language == "en"
        return videos.CaptionDownload(language=language, vtt=VTT)

    def transcribe_audio(self, *_args, **_kwargs):
        self.stt_calls += 1
        raise AssertionError("captioned videos must not call STT")


class FakeSttYouTubeAdapter:
    def __init__(self, tmp_path, *, fail_second: bool = False) -> None:
        self.tmp_path = tmp_path
        self.cleaned = False
        self.calls = []
        self.fail_second = fail_second
        self.stt_workers = 1

    def probe(self, _source_url: str) -> videos.VideoMetadata:
        return videos.VideoMetadata(
            title="Spoken lesson",
            channel="Publisher",
            duration_seconds=75.0,
            uploaded_caption_languages=(),
            language="en",
        )

    @contextmanager
    def prepare_audio(self, _source_url: str, *, chunk_seconds: int):
        assert chunk_seconds == 60
        first = self.tmp_path / "chunk-1.mp3"
        second = self.tmp_path / "chunk-2.mp3"
        first.write_bytes(b"first-audio")
        second.write_bytes(b"second-audio")
        try:
            yield videos.PreparedAudio(
                audio_sha256="a" * 64,
                duration_ms=75_000,
                chunks=(
                    videos.AudioChunk(1, 0, 60_000, "b" * 64, first),
                    videos.AudioChunk(2, 60_000, 75_000, "c" * 64, second),
                ),
            )
        finally:
            first.unlink(missing_ok=True)
            second.unlink(missing_ok=True)
            self.cleaned = True

    def transcribe_chunk(self, chunk, *, model: str, language: str | None):
        self.calls.append((chunk.ordinal, model, language))
        if self.fail_second and chunk.ordinal == 2:
            raise videos.SttError(
                "video_stt_rate_limited",
                fallback_allowed=model == "openai/whisper-large-v3",
                diagnostics={"category": "rate_limited"},
                usage={"cost": 0.0005},
                duration_ms=50,
            )
        text = "First minute." if chunk.ordinal == 1 else "Final seconds."
        return videos.SttResponse(
            text=text,
            language="en",
            segments=(),
            response_model=model,
            provider="fake-openrouter",
            usage={"cost": 0.001 * chunk.ordinal},
            duration_ms=100 + chunk.ordinal,
        )

    def extract_frames(self, _source_url: str) -> tuple[videos.VideoFrame, ...]:
        return (
            videos.VideoFrame(
                timestamp_ms=5_000,
                body=_png_bytes((70, 80, 90)),
                mime_type="image/png",
                filename="frame-00-00-05.png",
            ),
        )


class FakeMetadataAdapter:
    def __init__(self, duration_seconds) -> None:
        self.duration_seconds = duration_seconds

    def probe(self, _source_url: str) -> videos.VideoMetadata:
        return videos.VideoMetadata(
            title="Long lesson",
            channel="Publisher",
            duration_seconds=self.duration_seconds,
            uploaded_caption_languages=(),
            language="pt-BR",
        )


class ConcurrentFakeSttAdapter(FakeSttYouTubeAdapter):
    def __init__(self, tmp_path) -> None:
        super().__init__(tmp_path)
        self.stt_workers = 2
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def transcribe_chunk(self, chunk, *, model: str, language: str | None):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.05)
            return super().transcribe_chunk(chunk, model=model, language=language)
        finally:
            with self.lock:
                self.active -= 1


class MixedLanguageSttAdapter(FakeSttYouTubeAdapter):
    def probe(self, _source_url: str) -> videos.VideoMetadata:
        return videos.VideoMetadata(
            title="Mixed language lesson",
            channel="Publisher",
            duration_seconds=75.0,
            uploaded_caption_languages=(),
            language=None,
        )

    def transcribe_chunk(self, chunk, *, model: str, language: str | None):
        response = super().transcribe_chunk(chunk, model=model, language=language)
        return videos.SttResponse(
            text=response.text,
            language="en" if chunk.ordinal == 1 else "pt",
            segments=response.segments,
            response_model=response.response_model,
            provider=response.provider,
            usage=response.usage,
            duration_ms=response.duration_ms,
        )


def _force_explicit_stt_preflight(db, source_id: str, adapter) -> dict:
    """Keep the durable STT Module covered without making it the default route."""
    base = videos.refresh_preflight(db, source_id, adapter=adapter)
    preflight_id = f"{base['id']}-explicit-stt"
    db.execute(
        "INSERT INTO video_preflight"
        " (id, source_id, probe_version, input_fingerprint, status, title, channel,"
        " duration_seconds, uploaded_caption_languages, selected_caption_language,"
        " route, diagnostics)"
        " VALUES (%s, %s, %s, %s, 'succeeded', %s, %s, %s, '[]', NULL,"
        " 'automatic_stt', %s)",
        (
            preflight_id,
            source_id,
            base["probe_version"] if "probe_version" in base else videos.PREFLIGHT_VERSION,
            base["input_fingerprint"],
            base["title"],
            base["channel"],
            base["duration_seconds"],
            Jsonb(base.get("diagnostics") or {}),
        ),
    )
    db.commit()
    forced = videos.latest_preflight(db, source_id)
    assert forced is not None and forced["route"] == "automatic_stt"
    return forced


def _video_workbook(path, *, url: str) -> None:
    lesson = activity(
        title="Aula",
        kind="Class",
        week=1,
        order=1,
        subject="COM",
    )
    source = activity(
        title="Vídeo sem legendas",
        kind="Self-study",
        week=1,
        order=2,
        parent_uuid=lesson["Activity UUID"],
        parent_title=lesson["Title"],
        subject="COM",
        description="Assista antes da aula.",
        url=url,
    )
    write_adalove_workbook(path, [lesson, source], project="Video project")


def _tool_response(name: str, arguments: dict) -> dict:
    return {
        "choices": [{
            "message": {
                "content": "",
                "tool_calls": [{
                    "function": {"name": name, "arguments": json.dumps(arguments)}
                }],
            },
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        "provider": "test",
    }


def _client(arguments: dict, stage: str, tool: str) -> ModelClient:
    def transport(_url, _headers, payload, _timeout):
        return _tool_response(payload["tools"][0]["function"]["name"], arguments)

    return ModelClient(
        "fake/model",
        api_base="https://example.invalid/v1",
        transport=transport,
        extra=load_tool(str(PROMPTS_DIR / stage / tool)),
    )


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (48, 32), color).save(stream, format="PNG")
    return stream.getvalue()


def _fake_video_runtime_tools(tmp_path: Path) -> dict[str, str]:
    tools_dir = tmp_path / "fake-video-runtime-tools"
    tools_dir.mkdir()
    tools = {}
    for name in ("node", "yt-dlp", "ffmpeg", "ffprobe"):
        path = tools_dir / name
        path.write_bytes(b"test executable")
        path.chmod(0o700)
        tools[name] = str(path)
    return tools


class FakeSilentVisualAdapter:
    def __init__(self) -> None:
        self.beat_calls = 0
        self.stt_calls = 0

    def probe(self, _source_url: str) -> videos.VideoMetadata:
        return videos.VideoMetadata(
            title="Silent visual lesson",
            channel="Publisher",
            duration_seconds=18.0,
            uploaded_caption_languages=(),
            speech_evidence="absent",
            speech_probe={
                "version": videos.SPEECH_PROBE_VERSION,
                "status": "absent",
                "reason": "empty_original_auto_caption",
                "cue_count": 0,
            },
        )

    def acquire_visual_teaching_beats(
        self, source_url: str, *, duration_seconds: float | None
    ) -> TeachingBeatDocument:
        assert source_url == "https://www.youtube.com/watch?v=silent123"
        assert duration_seconds == 18.0
        self.beat_calls += 1
        return TeachingBeatDocument(
            beats=(
                TeachingBeat(
                    start_ms=1_000,
                    end_ms=5_000,
                    frame_ms=2_000,
                    heading="Create a frame",
                    explanation="The canvas demonstrates the frame tool and dimensions.",
                    visible_text="Create a frame",
                    visual_description="A design canvas with the frame tool selected.",
                    limitations=None,
                ),
                TeachingBeat(
                    start_ms=6_000,
                    end_ms=10_000,
                    frame_ms=8_000,
                    heading="Resize the frame",
                    explanation="The second state demonstrates resizing the same frame.",
                    visible_text="Resize",
                    visual_description="The selected frame shows resize handles.",
                    limitations=None,
                ),
            ),
            frames=(
                videos.VideoFrame(
                    timestamp_ms=2_000,
                    body=_png_bytes((10, 20, 30)),
                    mime_type="image/png",
                    filename="frame-00-00-02.png",
                ),
                videos.VideoFrame(
                    timestamp_ms=8_000,
                    body=_png_bytes((30, 20, 10)),
                    mime_type="image/png",
                    filename="frame-00-00-08.png",
                ),
            ),
            requested_model="google/gemini-2.5-flash",
            response_model="google/gemini-2.5-flash",
            provider="test",
            usage={"prompt_tokens": 42},
            duration_ms=20,
            prompt_ref="video-teaching-beats/v001",
            prompt_sha="a" * 64,
            input_manifest_hash="b" * 64,
            result_hash="c" * 64,
        )

    def extract_frames(self, _source_url: str):
        raise AssertionError("visual-only acquisition must use teaching beats")

    def prepare_audio(self, *_args, **_kwargs):
        self.stt_calls += 1
        raise AssertionError("a visual-only route must not prepare audio")

    def transcribe_chunk(self, *_args, **_kwargs):
        self.stt_calls += 1
        raise AssertionError("a visual-only route must not call OpenRouter STT")


class FakeCaptionedVisualAdapter(FakeYouTubeAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.frame_calls = 0

    def extract_frames(self, _source_url: str) -> tuple[videos.VideoFrame, ...]:
        self.frame_calls += 1
        return (
            videos.VideoFrame(
                timestamp_ms=4_000,
                body=_png_bytes((40, 50, 60)),
                mime_type="image/png",
                filename="frame-00-00-04.png",
            ),
        )


def test_silent_youtube_video_becomes_canonical_markdown_from_useful_frames(
    db, test_database_url, tmp_path
):
    source_id = "source-video-silent-visual-tracer"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Silent visual lesson', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "silent123"}),
        ),
    )
    db.commit()
    adapter = FakeSilentVisualAdapter()
    store = LocalAssetStore(tmp_path / "video-frame-assets")

    preflight = videos.refresh_preflight(db, source_id, adapter=adapter)
    assert preflight["route"] == "visual_only"
    assert preflight["diagnostics"]["speech_evidence"] == "absent"
    assert preflight["diagnostics"]["speech_probe"]["cue_count"] == 0
    queued = runner.enqueue_source(db, source_id)
    acquired = runner.process_next_job(
        db,
        job_id=queued["id"],
        video_adapter=adapter,
        asset_store=store,
    )

    assert acquired["status"] == "succeeded", acquired
    assert adapter.beat_calls == 1
    assert adapter.stt_calls == 0
    assert db.execute(
        "SELECT count(*) FROM video_transcript WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT c.status, a.kind, a.metadata->>'timestamp_ms'"
        " FROM source_image_candidate c JOIN source_asset a ON a.id = c.asset_id"
        " WHERE c.acquisition_job_id = %s ORDER BY c.ordinal",
        (queued["id"],),
    ).fetchall() == [
        ("useful", "video_frame", "2000"),
        ("useful", "video_frame", "8000"),
    ]
    assert db.execute(
        "SELECT count(*) FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()[0] == 1
    assert db.execute(
        "SELECT operation_kind, status, diagnostics->>'beat_count', result_hash"
        " FROM source_image_analysis_call WHERE markdown_artifact_id = %s",
        (acquired["artifact_id"],),
    ).fetchall() == [("video_teaching_beats", "succeeded", "2", "c" * 64)]
    assert db.execute(
        "SELECT count(*) FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s AND operation_kind = 'source_image_analysis'",
        (acquired["artifact_id"],),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM source_asset_analysis"
        " WHERE purpose = 'video_teaching_beat'"
        " AND analysis_call_id = (SELECT id FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s)",
        (acquired["artifact_id"],),
    ).fetchone()[0] == 2

    cleanup_id = db.execute(
        "SELECT id FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()[0]
    published = source_cleanup_jobs.process_next_source_cleanup(
        db,
        job_id=cleanup_id,
        cuts_client=_client({"cuts": []}, "passage-cuts", "tool-v001.json"),
        triage_client=_client(
            {"verdict": "keep"}, "passage-triage", "tool-v003.json"
        ),
        atomic_triage_client=_client(
            {"verdict": "keep"}, "passage-triage", "tool-v003-atomic.json"
        ),
        refine_client=_client(
            {"drop_elements": []}, "passage-refine", "tool-v002.json"
        ),
    )
    assert published["status"] == "succeeded", published

    app = create_app(
        lambda: psycopg.connect(test_database_url),
        asset_store_factory=lambda: store,
    )
    with TestClient(app) as client:
        response = client.get(f"/api/sources/{source_id}/markdown")
        assert response.status_code == 200
        payload = response.json()
        markdown = payload["markdown"]
        assert markdown.count("/api/source-assets/") == 2
        assert "video-frame://" not in markdown
        assert "Visual explanation:" not in markdown
        assert "Image description: The canvas demonstrates" in markdown
        assert "Visual organization: A design canvas" in markdown
        assert "OCR: Create a frame" in markdown
        asset_url = next(
            image["asset_url"] for image in payload["images"] if image["status"] == "useful"
        )
        asset_response = client.get(asset_url)
        assert asset_response.status_code == 200
        assert asset_response.headers["content-type"] == "image/png"

    image_blocks = [block for block in split_blocks(markdown) if block.kind == "image"]
    assert len(image_blocks) == 2
    assert all(block.image_state == "enriched" for block in image_blocks)


def test_captioned_video_runs_speech_and_visual_tracks_before_cleanup(db, tmp_path):
    source_id = "source-video-caption-and-frames"
    legacy_video_id = (
        "h4gw6gCP5ls e list=PL9iw99lS3Prg0hPSCiOz9AXeEmj8W8fL8 "
        "e index=14 e t=49s"
    )
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Caption plus frames', 'video')",
        (
            source_id,
            Jsonb(
                {
                    "kind": "video",
                    "provider": "youtube",
                    "video_id": legacy_video_id,
                }
            ),
        ),
    )
    db.commit()
    adapter = FakeCaptionedVisualAdapter()
    store = LocalAssetStore(tmp_path / "caption-frame-assets")
    videos.refresh_preflight(db, source_id, adapter=adapter)
    queued = runner.enqueue_source(db, source_id)

    acquired = runner.process_next_job(
        db,
        job_id=queued["id"],
        video_adapter=adapter,
        asset_store=store,
    )

    assert acquired["status"] == "succeeded", acquired
    assert adapter.stt_calls == 0
    assert adapter.frame_calls == 1
    assert db.execute(
        "SELECT route, segment_count, visual_analysis FROM video_transcript"
        " WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone() == ("uploaded_caption", 3, "pending")
    base_markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (acquired["artifact_id"],)
    ).fetchone()[0]
    assert "Hello. This lesson stays exact." in base_markdown
    assert "video-frame://h4gw6gCP5ls/4000" in base_markdown

    call_id = db.execute(
        "SELECT id FROM source_image_analysis_call WHERE markdown_artifact_id = %s",
        (acquired["artifact_id"],),
    ).fetchone()[0]

    def analyze(_markdown, images):
        image = images[0]
        return SourceImageBatchResult(
            analyses={
                image.image_id: SourceImageAnalysis(
                    image_id=image.image_id,
                    retain=True,
                    reason_code="context",
                    ocr=None,
                    description="The demonstrated interface state at this step.",
                    limitations=None,
                )
            },
            unresolved={},
            requested_model="google/gemini-2.5-flash",
            response_model="google/gemini-2.5-flash",
            provider="test",
            usage={},
            duration_ms=10,
            prompt_ref="source-image-analysis/v003",
            prompt_sha="c" * 64,
            input_manifest_hash="d" * 64,
        )

    image_jobs.process_next_source_image_analysis(
        db, call_id=call_id, asset_store=store, analyzer=analyze
    )
    enriched_id, enriched = db.execute(
        "SELECT c.source_artifact_id, a.body FROM source_cleanup_job c"
        " JOIN artifact a ON a.id = c.source_artifact_id"
        " WHERE c.acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()
    assert enriched_id.endswith(":images")
    assert "Hello. This lesson stays exact." in enriched
    assert "Image description: The demonstrated interface state" in enriched
    assert "video-frame://" not in enriched


def test_summarize_adapter_extracts_timestamped_frame_bytes_without_paid_models(
    tmp_path, monkeypatch
):
    commands = []
    environments = []
    runtime_entry_names = []
    first_body = _png_bytes((5, 15, 25))
    second_body = _png_bytes((25, 15, 5))

    def run(command, **kwargs):
        commands.append(command)
        environments.append(kwargs["env"])
        runtime_entry_names.append(
            {item.name for item in Path(kwargs["env"]["PATH"]).iterdir()}
        )
        slides_dir = Path(command[command.index("--slides-dir") + 1])
        output_dir = slides_dir / "youtube-UFtXy0KRxVI"
        output_dir.mkdir(parents=True)
        first = output_dir / "slide_0001_1.50s.png"
        second = output_dir / "slide_0002_120.80s.png"
        first.write_bytes(first_body)
        second.write_bytes(second_body)
        payload = {
            "ok": True,
            "slides": {
                "sourceId": "youtube-UFtXy0KRxVI",
                "slides": [
                    {"index": 1, "timestamp": 1.5, "imagePath": str(first)},
                    {"index": 2, "timestamp": 120.8, "imagePath": str(second)},
                ]
            },
        }
        return type("Result", (), {"stdout": json.dumps(payload), "stderr": ""})()

    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-summarize")
    monkeypatch.setenv("GEMINI_API_KEY", "must-not-reach-summarize")
    unsafe_bin = tmp_path / "unsafe-host-bin"
    unsafe_bin.mkdir()
    (unsafe_bin / "whisper-cli").write_bytes(b"must not be discoverable")
    monkeypatch.setenv("PATH", str(unsafe_bin))
    adapter = videos.SummarizeYouTubeAdapter(
        executable="summarize",
        runner=run,
        temporary_root=tmp_path,
        runtime_tools=_fake_video_runtime_tools(tmp_path),
    )

    frames = adapter.extract_frames(
        "https://www.youtube.com/watch?v=UFtXy0KRxVI"
    )

    assert [(item.timestamp_ms, item.filename, item.body) for item in frames] == [
        (1_500, "slide_0001_1.50s.png", first_body),
        (120_800, "slide_0002_120.80s.png", second_body),
    ]
    command = commands[0]
    assert command[:3] == [
        "summarize",
        "slides",
        "https://www.youtube.com/watch?v=UFtXy0KRxVI",
    ]
    for contract in (
        "--slides-max",
        "20",
        "--json",
        "--no-cache",
    ):
        assert contract in command
    for forbidden in (
        "--youtube",
        "--video-mode",
        "--transcriber",
        "--extract",
        "--slides-ocr",
    ):
        assert forbidden not in command
    assert "OPENAI_API_KEY" not in environments[0]
    assert "GEMINI_API_KEY" not in environments[0]
    assert environments[0]["SUMMARIZE_WHISPER_CPP_BINARY"].endswith(
        "/transcription-disabled"
    )
    assert runtime_entry_names[0] == {
        "node",
        "yt-dlp",
        "ffmpeg",
        "ffprobe",
    }
    assert "whisper-cli" not in runtime_entry_names[0]


def test_summarize_adapter_fails_closed_on_non_slides_json(tmp_path):
    def run(_command, **_kwargs):
        return type(
            "Result",
            (),
            {
                "stdout": json.dumps(
                    {
                        "extracted": {
                            "transcriptSource": "whisper",
                            "transcriptionProvider": "local-whisper.cpp",
                        }
                    }
                ),
                "stderr": "",
            },
        )()

    adapter = videos.SummarizeYouTubeAdapter(
        executable="summarize",
        runner=run,
        temporary_root=tmp_path,
        runtime_tools=_fake_video_runtime_tools(tmp_path),
    )

    with pytest.raises(videos.VideoAdapterError) as caught:
        adapter.extract_frames("https://www.youtube.com/watch?v=UFtXy0KRxVI")

    assert caught.value.category == "summarize_invalid_json"


def test_summarize_adapter_wraps_missing_runtime_as_dependency_failure(tmp_path):
    def run(_command, **_kwargs):
        raise FileNotFoundError("node")

    adapter = videos.SummarizeYouTubeAdapter(
        executable="summarize",
        runner=run,
        temporary_root=tmp_path,
        runtime_tools=_fake_video_runtime_tools(tmp_path),
    )

    with pytest.raises(videos.VideoAdapterError) as caught:
        adapter.extract_frames("https://www.youtube.com/watch?v=UFtXy0KRxVI")

    assert caught.value.category == "summarize_spawn_failed"
    assert caught.value.retriable is False


def test_captioned_youtube_source_fails_closed_without_visual_frames(db):
    source_id = "source-video-caption-tracer"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Captioned lesson', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "abc123"}),
        ),
    )
    db.commit()
    adapter = FakeYouTubeAdapter()

    preflight = videos.refresh_preflight(db, source_id, adapter=adapter)
    assert preflight["route"] == "uploaded_caption"
    assert preflight["selected_caption_language"] == "en"

    queued = runner.enqueue_source(db, source_id)
    result = runner.process_next_job(
        db, job_id=queued["id"], video_adapter=adapter
    )

    assert result["status"] == "failed", result
    assert result["failure_code"] == "video_frame_extraction_unavailable"
    assert result["diagnostics"]["category"] == "frame_adapter_missing"
    assert adapter.stt_calls == 0
    assert db.execute(
        "SELECT count(*) FROM video_transcript WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()[0] == 0


def test_uncaptioned_youtube_source_uses_durable_ordered_stt_chunks(db, tmp_path):
    source_id = "source-video-stt-tracer"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Spoken lesson', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "stt123"}),
        ),
    )
    db.commit()
    adapter = FakeSttYouTubeAdapter(tmp_path)

    preflight = videos.refresh_preflight(db, source_id, adapter=adapter)
    assert preflight["route"] == "automatic_stt"
    queued = runner.enqueue_source(db, source_id)
    acquired = runner.process_next_job(db, job_id=queued["id"], video_adapter=adapter)

    assert acquired["status"] == "succeeded", acquired
    assert adapter.cleaned is True
    assert adapter.calls == [
        (1, "openai/whisper-large-v3", "en"),
        (2, "openai/whisper-large-v3", "en"),
    ]
    assert db.execute(
        "SELECT jc.ordinal, c.window_start_ms, c.window_end_ms, c.status, c.text"
        " FROM video_stt_job_chunk jc JOIN video_stt_chunk c ON c.id = jc.chunk_id"
        " WHERE jc.acquisition_job_id = %s ORDER BY jc.ordinal",
        (queued["id"],),
    ).fetchall() == [
        (1, 0, 60_000, "succeeded", "First minute."),
        (2, 60_000, 75_000, "succeeded", "Final seconds."),
    ]
    assert db.execute(
        "SELECT a.requested_model, a.status, a.response_model, a.provider, a.usage"
        " FROM video_stt_attempt a"
        " JOIN video_stt_job_chunk jc ON jc.chunk_id = a.chunk_id"
        " WHERE jc.acquisition_job_id = %s ORDER BY jc.ordinal, a.attempt_no",
        (queued["id"],),
    ).fetchall() == [
        (
            "openai/whisper-large-v3",
            "succeeded",
            "openai/whisper-large-v3",
            "fake-openrouter",
            {"cost": 0.001},
        ),
        (
            "openai/whisper-large-v3",
            "succeeded",
            "openai/whisper-large-v3",
            "fake-openrouter",
            {"cost": 0.002},
        ),
    ]
    assert db.execute(
        "SELECT body FROM artifact WHERE id = %s", (acquired["artifact_id"],)
    ).fetchone()[0] == (
        "## [00:00–01:00]\n\nFirst minute.\n\n"
        "[![Video frame at 00:05](video-frame://stt123/5000)]"
        "(https://www.youtube.com/watch?v=stt123&t=5s)\n\n"
        "## [01:00–01:15]\n\nFinal seconds.\n"
    )
    assert db.execute(
        "SELECT count(*) FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s",
        (acquired["artifact_id"],),
    ).fetchone()[0] == 1


def test_stt_retry_reuses_successful_sibling_chunks_without_paying_again(db, tmp_path):
    source_id = "source-video-stt-selective-retry"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Retry lesson', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "retry123"}),
        ),
    )
    db.commit()
    adapter = FakeSttYouTubeAdapter(tmp_path, fail_second=True)
    _force_explicit_stt_preflight(db, source_id, adapter)

    first_job = runner.enqueue_source(db, source_id)
    first = runner.process_next_job(db, job_id=first_job["id"], video_adapter=adapter)
    assert first["status"] == "queued"
    assert first["failure_code"] is None
    assert first["diagnostics"]["retry_scheduled"] is True
    assert adapter.calls == [
        (1, "openai/whisper-large-v3", "en"),
        (2, "openai/whisper-large-v3", "en"),
        (2, "openai/whisper-1", "en"),
    ]

    adapter.fail_second = False
    second_job = runner.enqueue_source(db, source_id)
    assert second_job["id"] == first_job["id"]
    second = runner.process_next_job(db, job_id=second_job["id"], video_adapter=adapter)

    assert second["status"] == "succeeded", second
    assert adapter.calls == [
        (1, "openai/whisper-large-v3", "en"),
        (2, "openai/whisper-large-v3", "en"),
        (2, "openai/whisper-1", "en"),
        (2, "openai/whisper-large-v3", "en"),
    ]
    mappings = db.execute(
        "SELECT first.ordinal, first.chunk_id, second.chunk_id"
        " FROM video_stt_job_chunk first"
        " JOIN video_stt_job_chunk second ON second.ordinal = first.ordinal"
        " WHERE first.acquisition_job_id = %s AND second.acquisition_job_id = %s"
        " ORDER BY first.ordinal",
        (first_job["id"], second_job["id"]),
    ).fetchall()
    assert [(ordinal, left == right) for ordinal, left, right in mappings] == [
        (1, True),
        (2, True),
    ]
    attempts = db.execute(
        "SELECT jc.ordinal, a.requested_model, a.status, a.failure_code"
        " FROM video_stt_attempt a"
        " JOIN video_stt_job_chunk jc ON jc.chunk_id = a.chunk_id"
        " WHERE jc.acquisition_job_id = %s ORDER BY jc.ordinal, a.attempt_no",
        (second_job["id"],),
    ).fetchall()
    assert attempts == [
        (1, "openai/whisper-large-v3", "succeeded", None),
        (2, "openai/whisper-large-v3", "failed", "video_stt_rate_limited"),
        (2, "openai/whisper-1", "failed", "video_stt_rate_limited"),
        (2, "openai/whisper-large-v3", "succeeded", None),
    ]


def test_long_video_authorization_is_explicit_persisted_and_deduplicated(
    db, test_database_url
):
    source_id = "source-video-long-approval"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Long lesson', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "long123"}),
        ),
    )
    db.commit()
    preflight = videos.refresh_preflight(
        db, source_id, adapter=FakeMetadataAdapter(120 * 60 + 1)
    )
    assert preflight["route"] == "approval_required"

    app = create_app(lambda: psycopg.connect(test_database_url))
    with TestClient(app) as client:
        blocked = client.post(f"/api/sources/{source_id}/queue")
        assert blocked.status_code == 409
        assert "autoriz" in blocked.json()["detail"].lower()

        first = client.post(f"/api/sources/{source_id}/authorize-transcription")
        second = client.post(f"/api/sources/{source_id}/authorize-transcription")

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["job"]["id"] == second.json()["job"]["id"]
    assert first.json()["job"]["request_input"] == {
        "video_preflight_id": preflight["id"],
        "transcript_route": "automatic_stt",
        "video_processing_authorized": True,
        "policy_version": "video-speech-policy/v2",
        "grouping_version": "timestamp-groups/v1",
        "visual_route": "summarize-slides/v1",
        "stt_model": "openai/whisper-large-v3",
        "stt_fallback_model": "openai/whisper-1",
        "stt_chunk_seconds": 60,
        "stt_operation_version": "openrouter-stt/v1",
    }
    assert second.json()["job"]["deduplicated"] is True
    assert db.execute(
        "SELECT count(*) FROM acquisition_job WHERE source_id = %s",
        (source_id,),
    ).fetchone()[0] == 1


def test_video_preflight_endpoint_is_idempotent_and_reports_unknown_duration(
    db, test_database_url
):
    source_id = "source-video-preflight-endpoint"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Unknown duration', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "unknown123"}),
        ),
    )
    db.commit()
    app = create_app(
        lambda: psycopg.connect(test_database_url),
        video_adapter_factory=lambda: FakeMetadataAdapter(None),
    )

    with TestClient(app) as client:
        first = client.post(f"/api/sources/{source_id}/video-preflight")
        second = client.post(f"/api/sources/{source_id}/video-preflight")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["video_preflight"] == {
        "id": first.json()["video_preflight"]["id"],
        "status": "succeeded",
        "title": "Long lesson",
        "channel": "Publisher",
        "duration_seconds": None,
        "uploaded_caption_languages": [],
        "selected_caption_language": None,
        "route": "approval_required",
        "failure_code": None,
        "diagnostics": {
            "category": "success",
            "automatic_captions_used": False,
            "detected_language": "pt-BR",
            "speech_evidence": "unknown",
            "speech_probe": {
                "version": videos.SPEECH_PROBE_VERSION,
                "status": "unknown",
                "reason": "adapter_did_not_probe",
            },
        },
        "deduplicated": False,
    }
    assert second.json()["video_preflight"]["id"] == first.json()["video_preflight"]["id"]
    assert second.json()["video_preflight"]["deduplicated"] is True


def test_syllabus_card_projects_video_route_and_exposes_matching_actions(
    test_database_url, applied_migrations, tmp_path
):
    path = tmp_path / "video-syllabus.xlsx"
    _video_workbook(path, url="https://youtu.be/h4gw6gCP5ls?t=30")
    app = create_app(
        lambda: psycopg.connect(test_database_url),
        video_adapter_factory=lambda: FakeMetadataAdapter(74 * 60),
    )
    with psycopg.connect(test_database_url) as conn:
        uploaded = import_workbook(
            conn, path, "Video syllabus", require_syllabus_metadata=False
        )
    with TestClient(app) as client:
        detail = client.get(f"/api/syllabi/{uploaded['syllabus_id']}").json()
        source_id = detail["lessons"][0]["sources"][0]["source_id"]
        assert client.post(f"/api/sources/{source_id}/video-preflight").status_code == 200
        source = client.get(f"/api/syllabi/{uploaded['syllabus_id']}").json()[
            "lessons"
        ][0]["sources"][0]

    assert source["acquisition_capability"] == {
        "supported": True,
        "adapter": "youtube",
        "label": "YouTube",
    }
    assert source["video_preflight"]["route"] == "automatic_stt"
    assert source["video_preflight"]["duration_seconds"] == 74 * 60
    assert source["video_preflight"]["uploaded_caption_languages"] == []


def test_openrouter_stt_request_and_provider_segments_are_stamped(tmp_path):
    chunk_path = tmp_path / "chunk.mp3"
    chunk_path.write_bytes(b"bounded-audio")
    requests = []

    def transport(url, headers, payload, timeout):
        requests.append((url, headers, payload, timeout))
        return {
            "id": "generation-123",
            "model": "openai/whisper-large-v3",
            "provider": "OpenAI",
            "language": "en",
            "text": "Provider timed text.",
            "segments": [
                {"start": 1.25, "end": 3.5, "text": "Provider timed text."}
            ],
            "usage": {"cost": 0.004, "total_tokens": 42},
        }

    adapter = videos.YtDlpYouTubeAdapter(
        executable="yt-dlp",
        ffmpeg_path="ffmpeg",
        api_key="test-openrouter-key",
        stt_transport=transport,
    )
    response = adapter.transcribe_chunk(
        videos.AudioChunk(1, 0, 60_000, "d" * 64, chunk_path),
        model="openai/whisper-large-v3",
        language="en",
    )

    assert len(requests) == 1
    url, headers, payload, timeout = requests[0]
    assert url == "https://openrouter.ai/api/v1/audio/transcriptions"
    assert headers == {
        "Authorization": "Bearer test-openrouter-key",
        "Content-Type": "application/json",
    }
    assert payload == {
        "model": "openai/whisper-large-v3",
        "input_audio": {
            "data": base64.b64encode(b"bounded-audio").decode("ascii"),
            "format": "mp3",
        },
        "temperature": 0,
        "response_format": "verbose_json",
        "timestamp_granularities": ["segment"],
        "language": "en",
    }
    assert timeout == 300
    assert response.text == "Provider timed text."
    assert response.segments == (
        videos.SttSegment(1250, 3500, "Provider timed text."),
    )
    assert response.response_model == "openai/whisper-large-v3"
    assert response.provider == "OpenAI"
    assert response.generation_id == "generation-123"
    assert response.usage == {"cost": 0.004, "total_tokens": 42}


def test_openrouter_transport_is_stamped_when_response_omits_provider(tmp_path):
    chunk_path = tmp_path / "chunk.mp3"
    chunk_path.write_bytes(b"bounded-audio")
    adapter = videos.YtDlpYouTubeAdapter(
        executable="yt-dlp",
        ffmpeg_path="ffmpeg",
        api_key="test-openrouter-key",
        stt_transport=lambda *_args: {
            "language": "en",
            "text": "Provider omitted its routing metadata.",
            "usage": {"cost": 0.001},
        },
    )

    response = adapter.transcribe_chunk(
        videos.AudioChunk(1, 0, 60_000, "d" * 64, chunk_path),
        model="openai/whisper-large-v3",
        language="en",
    )

    assert response.provider == "openrouter"
    assert response.response_model is None


def test_audio_preparation_downloads_audio_only_chunks_it_and_removes_temporary_files(
    monkeypatch
):
    commands = []

    def run(command, **_kwargs):
        commands.append(command)
        if command[0] == "yt-dlp":
            template = Path(command[command.index("-o") + 1])
            template.with_suffix(".webm").write_bytes(b"source-audio-only")
            return type("Result", (), {"stdout": "", "stderr": ""})()
        if command[0] == "ffmpeg":
            pattern = Path(command[-1])
            pattern.parent.mkdir(parents=True, exist_ok=True)
            Path(str(pattern).replace("%05d", "00000")).write_bytes(b"chunk-one")
            Path(str(pattern).replace("%05d", "00001")).write_bytes(b"chunk-two")
            return type("Result", (), {"stdout": "", "stderr": ""})()
        if command[0] == "ffprobe":
            duration = "60.0\n" if command[-1].endswith("00000.mp3") else "15.0\n"
            return type("Result", (), {"stdout": duration, "stderr": ""})()
        raise AssertionError(command)

    monkeypatch.setattr(videos.subprocess, "run", run)
    adapter = videos.YtDlpYouTubeAdapter(
        executable="yt-dlp",
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        api_key="unused",
    )

    with adapter.prepare_audio(
        "https://www.youtube.com/watch?v=audio123", chunk_seconds=60
    ) as prepared:
        directory = prepared.chunks[0].path.parent
        assert prepared.duration_ms == 75_000
        assert [(item.ordinal, item.start_ms, item.end_ms) for item in prepared.chunks] == [
            (1, 0, 60_000),
            (2, 60_000, 75_000),
        ]
        assert all(item.path.exists() for item in prepared.chunks)
        assert prepared.audio_sha256 == hashlib.sha256(
            (prepared.chunks[0].sha256 + prepared.chunks[1].sha256).encode()
        ).hexdigest()

    assert not directory.exists()
    assert commands[0][0] == "yt-dlp"
    assert "bestaudio/best" in commands[0]
    assert "--write-auto-subs" not in commands[0]
    assert all("video-frame" not in " ".join(command) for command in commands)


def test_stt_chunks_run_with_bounded_concurrency(db, tmp_path):
    source_id = "source-video-stt-concurrency"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Concurrent lesson', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "parallel123"}),
        ),
    )
    db.commit()
    adapter = ConcurrentFakeSttAdapter(tmp_path)
    _force_explicit_stt_preflight(db, source_id, adapter)
    queued = runner.enqueue_source(db, source_id)

    acquired = runner.process_next_job(db, job_id=queued["id"], video_adapter=adapter)

    assert acquired["status"] == "succeeded", json.dumps(acquired, default=str)
    assert adapter.max_active == 2
    assert sorted(call[0] for call in adapter.calls) == [1, 2]


def test_two_workers_cannot_pay_for_the_same_stt_chunk(
    db, test_database_url, tmp_path
):
    source_id = "source-video-shared-chunk-claim"
    chunk_id = "vsc-" + "1" * 64
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Shared chunk claim', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "claim123"}),
        ),
    )
    db.execute(
        "INSERT INTO video_stt_chunk"
        " (id, source_id, audio_sha256, chunk_sha256, window_start_ms,"
        " window_end_ms, requested_model, operation_version, model_route_hash)"
        " VALUES (%s, %s, %s, %s, 0, 60000, %s, %s, %s)",
        (
            chunk_id,
            source_id,
            "a" * 64,
            "b" * 64,
            "openai/whisper-large-v3",
            videos.STT_OPERATION_VERSION,
            "c" * 64,
        ),
    )
    db.commit()
    path = tmp_path / "shared.mp3"
    path.write_bytes(b"shared-audio")
    audio_chunk = videos.AudioChunk(1, 0, 60_000, "b" * 64, path)
    gate = threading.Barrier(2)
    calls = []
    results = []
    errors = []
    call_lock = threading.Lock()

    class Adapter:
        def transcribe_chunk(self, _chunk, *, model, language):
            with call_lock:
                calls.append((model, language))
            time.sleep(0.05)
            return videos.SttResponse(
                text="Paid once.",
                language="en",
                segments=(),
                response_model=model,
                provider="openrouter",
                usage={"cost": 0.001},
                duration_ms=50,
            )

    adapter = Adapter()

    def work():
        try:
            with psycopg.connect(test_database_url) as conn:
                gate.wait(timeout=5)
                results.append(
                    videos._process_stt_chunk(
                        conn,
                        adapter=adapter,
                        audio_chunk=audio_chunk,
                        chunk_id=chunk_id,
                        language="en",
                        primary_model="openai/whisper-large-v3",
                        fallback_model="openai/whisper-1",
                        operation_version=videos.STT_OPERATION_VERSION,
                    )
                )
        except Exception as exc:
            errors.append(exc)

    workers = [threading.Thread(target=work) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=5)

    assert all(not worker.is_alive() for worker in workers)
    assert len(calls) == 1
    assert [result["status"] for result in results] == ["succeeded"]
    assert len(errors) == 1
    assert isinstance(errors[0], videos.VideoAdapterError)
    assert errors[0].category == "chunk_claim_unavailable"
    assert db.execute(
        "SELECT status, attempt_count FROM video_stt_chunk WHERE id = %s",
        (chunk_id,),
    ).fetchone() == ("succeeded", 1)
    assert db.execute(
        "SELECT count(*) FROM video_stt_attempt WHERE chunk_id = %s",
        (chunk_id,),
    ).fetchone()[0] == 1


def test_stt_resolves_its_lease_connection_before_claiming(
    db, tmp_path, monkeypatch
):
    source_id = "source-video-stt-lease-factory"
    chunk_id = "vsc-" + "3" * 64
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'STT lease factory', 'video')",
        (
            source_id,
            Jsonb(
                {
                    "kind": "video",
                    "provider": "youtube",
                    "video_id": "lease123",
                }
            ),
        ),
    )
    db.execute(
        "INSERT INTO video_stt_chunk"
        " (id, source_id, audio_sha256, chunk_sha256, window_start_ms,"
        " window_end_ms, requested_model, operation_version, model_route_hash)"
        " VALUES (%s, %s, %s, %s, 0, 60000, %s, %s, %s)",
        (
            chunk_id,
            source_id,
            "a" * 64,
            "b" * 64,
            "openai/whisper-large-v3",
            videos.STT_OPERATION_VERSION,
            "c" * 64,
        ),
    )
    db.commit()
    path = tmp_path / "lease-factory.mp3"
    path.write_bytes(b"not-used")

    def unavailable_factory(_conn):
        raise RuntimeError("lease connection configuration is unavailable")

    monkeypatch.setattr(videos, "separate_connection_factory", unavailable_factory)

    with pytest.raises(RuntimeError, match="lease connection configuration"):
        videos._process_stt_chunk(
            db,
            adapter=object(),
            audio_chunk=videos.AudioChunk(1, 0, 60_000, "b" * 64, path),
            chunk_id=chunk_id,
            language="en",
            primary_model="openai/whisper-large-v3",
            fallback_model=None,
            operation_version=videos.STT_OPERATION_VERSION,
        )

    assert db.execute(
        "SELECT status, attempt_count, claim_token FROM video_stt_chunk WHERE id = %s",
        (chunk_id,),
    ).fetchone() == ("queued", 0, None)


def test_a_slow_stt_call_renews_its_chunk_before_another_worker_can_pay(
    db, test_database_url, tmp_path, monkeypatch
):
    source_id = "source-video-stt-heartbeat"
    chunk_id = "vsc-" + "2" * 64
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'STT heartbeat', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "heart123"}),
        ),
    )
    db.execute(
        "INSERT INTO video_stt_chunk"
        " (id, source_id, audio_sha256, chunk_sha256, window_start_ms,"
        " window_end_ms, requested_model, operation_version, model_route_hash)"
        " VALUES (%s, %s, %s, %s, 0, 60000, %s, %s, %s)",
        (
            chunk_id,
            source_id,
            "d" * 64,
            "e" * 64,
            "openai/whisper-large-v3",
            videos.STT_OPERATION_VERSION,
            "f" * 64,
        ),
    )
    db.commit()
    path = tmp_path / "heartbeat.mp3"
    path.write_bytes(b"heartbeat-audio")
    audio_chunk = videos.AudioChunk(1, 0, 60_000, "e" * 64, path)
    started = threading.Event()
    release = threading.Event()
    results = []
    errors = []

    class Adapter:
        def transcribe_chunk(self, _chunk, *, model, language):
            started.set()
            assert release.wait(timeout=5)
            return videos.SttResponse(
                text="Renewed once.",
                language="en",
                segments=(),
                response_model=model,
                provider="openrouter",
                usage={"cost": 0.001},
                duration_ms=50,
            )

    monkeypatch.setattr(videos, "acquisition_lease_minutes", lambda: 0.002)
    monkeypatch.setattr(job_lease, "acquisition_lease_minutes", lambda: 0.002)

    def work():
        try:
            with psycopg.connect(test_database_url) as worker:
                results.append(
                    videos._process_stt_chunk(
                        worker,
                        adapter=Adapter(),
                        audio_chunk=audio_chunk,
                        chunk_id=chunk_id,
                        language="en",
                        primary_model="openai/whisper-large-v3",
                        fallback_model="openai/whisper-1",
                        operation_version=videos.STT_OPERATION_VERSION,
                    )
                )
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=work)
    worker.start()
    assert started.wait(timeout=5), errors
    try:
        time.sleep(0.3)
        with psycopg.connect(test_database_url) as contender_connection:
            contender = videos._claim_stt_chunk(contender_connection, chunk_id)
    finally:
        release.set()
        worker.join(timeout=5)

    assert not worker.is_alive()
    assert errors == []
    assert contender is None
    assert results[0]["status"] == "succeeded"


@pytest.mark.parametrize(
    ("duration_seconds", "expected_route"),
    [
        (119 * 60 + 59, "automatic_stt"),
        (120 * 60, "automatic_stt"),
        (120 * 60 + 1, "approval_required"),
        (None, "approval_required"),
    ],
)
def test_no_caption_duration_policy_has_an_inclusive_two_hour_boundary(
    db, duration_seconds, expected_route
):
    marker = "unknown" if duration_seconds is None else str(duration_seconds)
    source_id = f"source-video-duration-{marker}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Duration policy', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": marker}),
        ),
    )
    db.commit()

    preflight = videos.refresh_preflight(
        db, source_id, adapter=FakeMetadataAdapter(duration_seconds)
    )

    assert preflight["route"] == expected_route


@pytest.mark.parametrize(
    ("probe_body", "expected_evidence", "expected_cues"),
    [
        ("WEBVTT\n\n", "absent", 0),
        (VTT, "present", 3),
    ],
)
def test_ytdlp_probe_uses_original_auto_caption_only_as_speech_presence(
    monkeypatch, probe_body, expected_evidence, expected_cues
):
    payload = {
        "title": "Automatic only",
        "channel": "Publisher",
        "duration": 60,
        "language": "pt-BR",
        "subtitles": {},
        "automatic_captions": {
            "en-orig": [
                {"ext": "vtt", "url": "https://signed.example/automatic"}
            ]
        },
        "formats": [{"acodec": "opus", "vcodec": "none"}],
    }

    def run(*_args, **_kwargs):
        return type(
            "Result", (), {"stdout": json.dumps(payload), "stderr": ""}
        )()

    monkeypatch.setattr(videos.subprocess, "run", run)
    metadata = videos.YtDlpYouTubeAdapter(
        executable="yt-dlp",
        caption_probe_transport=lambda _url: probe_body.encode(),
    ).probe(
        "https://www.youtube.com/watch?v=automatic123"
    )

    assert metadata.uploaded_caption_languages == ()
    assert metadata.language == "pt-BR"
    assert metadata.speech_evidence == expected_evidence
    assert metadata.speech_probe == {
        "version": videos.SPEECH_PROBE_VERSION,
        "status": expected_evidence,
        "reason": "original_auto_caption",
        "language": "en-orig",
        "cue_count": expected_cues,
    }
    assert "signed.example" not in json.dumps(metadata.speech_probe)
    assert "Hello." not in json.dumps(metadata.speech_probe)


def test_ytdlp_probe_does_not_treat_live_chat_as_an_uploaded_caption(monkeypatch):
    payload = {
        "title": "Archived live lesson",
        "channel": "Publisher",
        "duration": 75 * 60,
        "language": "pt",
        "subtitles": {
            "live_chat": [
                {
                    "ext": "json",
                    "protocol": "youtube_live_chat_replay",
                    "url": "https://www.youtube.com/watch?v=lesson123",
                }
            ]
        },
        "automatic_captions": {
            "pt-orig": [
                {"ext": "vtt", "url": "https://signed.example/automatic"}
            ]
        },
        "formats": [{"acodec": "opus", "vcodec": "none"}],
    }
    monkeypatch.setattr(
        videos.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result", (), {"stdout": json.dumps(payload), "stderr": ""}
        )(),
    )

    metadata = videos.YtDlpYouTubeAdapter(
        executable="yt-dlp",
        caption_probe_transport=lambda _url: VTT.encode(),
    ).probe("https://www.youtube.com/watch?v=lesson123")

    assert metadata.uploaded_caption_languages == ()
    assert metadata.speech_evidence == "present"
    assert metadata.speech_probe["language"] == "pt-orig"
    assert videos._route(metadata) == ("automatic_stt", None)


def test_refresh_preflight_does_not_reuse_an_obsolete_probe_version(db):
    source_id = "source-video-obsolete-preflight"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Archived live lesson', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "lesson123"}),
        ),
    )
    db.commit()
    db.execute(
        "INSERT INTO video_preflight"
        " (id, source_id, probe_version, input_fingerprint, status, title, channel,"
        " duration_seconds, uploaded_caption_languages, selected_caption_language,"
        " route, diagnostics)"
        " VALUES ('obsolete-live-chat', %s, 'youtube-preflight/v2', %s,"
        " 'succeeded', 'Archived live lesson', 'Publisher', 4500,"
        " '[\"live_chat\"]', 'live_chat', 'uploaded_caption', '{}')",
        (source_id, videos._input_fingerprint(videos._source(db, source_id))),
    )
    db.commit()

    current = videos.refresh_preflight(
        db, source_id, adapter=FakeMetadataAdapter(75 * 60)
    )

    assert current["id"] != "obsolete-live-chat"
    assert current["probe_version"] == videos.PREFLIGHT_VERSION
    assert current["deduplicated"] is False


def test_queue_endpoint_refreshes_an_obsolete_video_preflight(
    db, test_database_url
):
    source_id = "source-video-obsolete-queue"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Archived live lesson', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "lesson123"}),
        ),
    )
    db.execute(
        "INSERT INTO video_preflight"
        " (id, source_id, probe_version, input_fingerprint, status, title, channel,"
        " duration_seconds, uploaded_caption_languages, selected_caption_language,"
        " route, diagnostics)"
        " VALUES ('obsolete-live-chat-queue', %s, 'youtube-preflight/v2', %s,"
        " 'succeeded', 'Archived live lesson', 'Publisher', 4500,"
        " '[\"live_chat\"]', 'live_chat', 'uploaded_caption', '{}')",
        (source_id, "a" * 64),
    )
    db.commit()
    app = create_app(
        lambda: psycopg.connect(test_database_url),
        video_adapter_factory=lambda: FakeMetadataAdapter(75 * 60),
    )

    with TestClient(app) as client:
        response = client.post(f"/api/sources/{source_id}/queue")

    assert response.status_code == 202, response.text
    job = response.json()["job"]
    assert job["video_preflight_id"] != "obsolete-live-chat-queue"
    assert job["request_input"]["transcript_route"] == "automatic_stt"
    current = videos.latest_preflight(db, source_id)
    assert current is not None
    assert current["id"] == job["video_preflight_id"]
    assert current["probe_version"] == videos.PREFLIGHT_VERSION


def test_ytdlp_speech_probe_unavailable_defaults_to_openrouter(monkeypatch):
    payload = {
        "title": "Probe unavailable",
        "duration": 60,
        "subtitles": {},
        "automatic_captions": {
            "en-orig": [
                {"ext": "vtt", "url": "https://signed.example/automatic"}
            ]
        },
        "formats": [{"acodec": "opus", "vcodec": "none"}],
    }

    monkeypatch.setattr(
        videos.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result", (), {"stdout": json.dumps(payload), "stderr": ""}
        )(),
    )

    def unavailable(_url):
        raise TimeoutError("caption probe unavailable")

    metadata = videos.YtDlpYouTubeAdapter(
        executable="yt-dlp", caption_probe_transport=unavailable
    ).probe("https://www.youtube.com/watch?v=automatic123")

    assert metadata.speech_evidence == "unknown"
    assert metadata.speech_probe["status"] == "unknown"
    assert videos._route(metadata) == ("automatic_stt", None)


def test_syllabus_progress_reports_stt_chunks_then_canonical_cleanup(
    test_database_url, applied_migrations, tmp_path
):
    path = tmp_path / "video-progress.xlsx"
    _video_workbook(path, url="https://www.youtube.com/watch?v=progress123")
    adapter = FakeSttYouTubeAdapter(tmp_path)
    app = create_app(
        lambda: psycopg.connect(test_database_url),
        video_adapter_factory=lambda: adapter,
    )
    with psycopg.connect(test_database_url) as conn:
        uploaded = import_workbook(
            conn, path, "Video progress", require_syllabus_metadata=False
        )
    with TestClient(app) as client:
        detail = client.get(f"/api/syllabi/{uploaded['syllabus_id']}").json()
        source_id = detail["lessons"][0]["sources"][0]["source_id"]
        assert client.post(f"/api/sources/{source_id}/video-preflight").status_code == 200
        with psycopg.connect(test_database_url) as conn:
            _force_explicit_stt_preflight(conn, source_id, adapter)
        queued = client.post(f"/api/sources/{source_id}/queue").json()["job"]

        with psycopg.connect(test_database_url) as conn:
            result = runner.process_next_job(
                conn, job_id=queued["id"], video_adapter=adapter
            )
        assert result["status"] == "succeeded", result
        source = client.get(f"/api/syllabi/{uploaded['syllabus_id']}").json()[
            "lessons"
        ][0]["sources"][0]

    assert source["pipeline"]["status"] == "images"
    assert source["video_progress"]["stage"] == "frame_analysis"
    assert source["video_progress"]["speech"] == "stt"
    assert source["video_progress"]["speech_diagnostics"] == {
        "chunks_total": 2,
        "chunks_succeeded": 2,
        "chunks_failed": 0,
        "chunks_running": 0,
    }


def test_stt_rejects_inconsistent_languages_across_successful_chunks(db, tmp_path):
    source_id = "source-video-stt-mixed-language"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Mixed language', 'video')",
        (
            source_id,
            Jsonb({"kind": "video", "provider": "youtube", "video_id": "mixed123"}),
        ),
    )
    db.commit()
    adapter = MixedLanguageSttAdapter(tmp_path)
    _force_explicit_stt_preflight(db, source_id, adapter)
    queued = runner.enqueue_source(db, source_id)

    result = runner.process_next_job(db, job_id=queued["id"], video_adapter=adapter)

    assert result["status"] == "failed"
    assert result["failure_code"] == "video_stt_language_mismatch"
    assert result["diagnostics"]["observed_languages"] == ["en", "pt"]
