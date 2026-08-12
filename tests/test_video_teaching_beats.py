import io
import json

import pytest
from PIL import Image

from universe.acquisition import videos
from universe.acquisition.video_teaching_beats import (
    OpenRouterGeminiTeachingBeatAdapter,
    TeachingBeat,
    TeachingBeatDocument,
    YtDlpTeachingBeatFrameMaterializer,
    parse_beats,
)
from universe.model_client import ModelClient, ModelError
from universe.settings import openrouter_video_provider_routing


def _png(color: tuple[int, int, int]) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (48, 32), color).save(stream, format="PNG")
    return stream.getvalue()


def test_visual_only_video_becomes_markdown_from_every_teaching_beat():
    class Adapter:
        def __init__(self) -> None:
            self.beat_calls = 0

        def acquire_visual_teaching_beats(
            self, source_url: str, *, duration_seconds: float | None
        ) -> TeachingBeatDocument:
            assert source_url == "https://www.youtube.com/watch?v=silent123"
            assert duration_seconds == 68.0
            self.beat_calls += 1
            return TeachingBeatDocument(
                beats=(
                    TeachingBeat(
                        start_ms=10_000,
                        end_ms=22_000,
                        frame_ms=14_000,
                        heading="Principais usos do PLN",
                        explanation=(
                            "A tela ensina quatro aplicações: opinião de clientes, "
                            "faturas, classificação de documentos e tendências."
                        ),
                        visible_text="Estes são os principais usos do PLN",
                        visual_description="Quatro itens ligados por uma linha vertical.",
                        limitations=None,
                    ),
                    TeachingBeat(
                        start_ms=23_000,
                        end_ms=36_000,
                        frame_ms=28_000,
                        heading="API Natural Language",
                        explanation=(
                            "A API fornece modelos pré-treinados para análise de linguagem."
                        ),
                        visible_text="API Natural Language",
                        visual_description="Cartão do produto com um robô ao lado.",
                        limitations=None,
                    ),
                ),
                frames=(
                    videos.VideoFrame(
                        timestamp_ms=14_000,
                        body=_png((10, 20, 30)),
                        mime_type="image/png",
                        filename="beat-0001.png",
                    ),
                    videos.VideoFrame(
                        timestamp_ms=28_000,
                        body=_png((30, 20, 10)),
                        mime_type="image/png",
                        filename="beat-0002.png",
                    ),
                ),
                requested_model="google/gemini-2.5-flash",
                response_model="google/gemini-2.5-flash",
                provider="openrouter",
                usage={"prompt_tokens": 100},
                duration_ms=500,
                prompt_ref="video-teaching-beats/v001",
                prompt_sha="a" * 64,
                input_manifest_hash="b" * 64,
                result_hash="c" * 64,
            )

        def extract_frames(self, _source_url: str):
            raise AssertionError(
                "visual-only videos must not use sparse Summarize slide sampling"
            )

    adapter = Adapter()
    result = videos.acquire_video(
        {
            "id": "source-silent",
            "identity": {
                "kind": "video",
                "provider": "youtube",
                "video_id": "silent123",
            },
        },
        {
            "id": "preflight-silent",
            "route": "visual_only",
            "duration_seconds": 68.0,
        },
        adapter=adapter,
    )

    assert adapter.beat_calls == 1
    assert result.route == "visual_only"
    assert result.segments == ()
    assert [frame.timestamp_ms for frame in result.frames] == [14_000, 28_000]
    assert "Visual explanation:" not in result.markdown
    assert "## [00:10–00:22] Principais usos do PLN" in result.markdown
    assert "video-frame://silent123/14000" in result.markdown
    assert "## [00:23–00:36] API Natural Language" in result.markdown
    assert "video-frame://silent123/28000" in result.markdown
    assert result.teaching_beats is not None


def test_openrouter_adapter_reads_the_full_video_and_materializes_beat_frames():
    requests = []

    def transport(_url, _headers, payload, _timeout):
        requests.append(payload)
        return {
            "model": "google/gemini-2.5-flash",
            "provider": "google-ai-studio",
            "usage": {"prompt_tokens": 800, "completion_tokens": 120},
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "report_visual_teaching_beats",
                                    "arguments": json.dumps(
                                        {
                                            "beats": [
                                                {
                                                    "start_s": 10,
                                                    "end_s": 22,
                                                    "frame_s": 14,
                                                    "heading": "Principais usos do PLN",
                                                    "explanation": "A tela ensina quatro aplicações de PLN.",
                                                    "visible_text": "Estes são os principais usos do PLN",
                                                    "visual_description": "Quatro itens ligados verticalmente.",
                                                    "limitations": None,
                                                },
                                                {
                                                    "start_s": 23,
                                                    "end_s": 36,
                                                    "frame_s": 28,
                                                    "heading": "API Natural Language",
                                                    "explanation": "A API oferece modelos pré-treinados.",
                                                    "visible_text": "API Natural Language",
                                                    "visual_description": "Cartão de produto com um robô.",
                                                    "limitations": None,
                                                },
                                            ]
                                        }
                                    ),
                                }
                            }
                        ],
                    }
                }
            ],
        }

    client = ModelClient(
        "google/gemini-2.5-flash",
        api_base="https://openrouter.example/v1",
        api_key="test-key",
        transport=transport,
    )
    materialized = []

    def materialize(source_url, timestamps):
        materialized.append((source_url, timestamps))
        return tuple(
            videos.VideoFrame(
                timestamp_ms=timestamp,
                body=_png((timestamp // 1000, 10, 20)),
                mime_type="image/png",
                filename=f"beat-{index:04d}.png",
            )
            for index, timestamp in enumerate(timestamps, 1)
        )

    adapter = OpenRouterGeminiTeachingBeatAdapter(
        client=client,
        frame_materializer=materialize,
    )
    source_url = "https://www.youtube.com/watch?v=silent123"
    result = adapter.acquire_visual_teaching_beats(
        source_url, duration_seconds=68.0
    )

    assert len(requests) == 1
    content = requests[0]["messages"][0]["content"]
    assert content[0] == {
        "type": "video_url",
        "video_url": {"url": source_url},
    }
    assert content[1]["type"] == "text"
    assert "every major teaching beat" in content[1]["text"]
    assert requests[0]["tool_choice"]["function"]["name"] == (
        "report_visual_teaching_beats"
    )
    assert materialized == [(source_url, (14_000, 28_000))]
    assert [beat.heading for beat in result.beats] == [
        "Principais usos do PLN",
        "API Natural Language",
    ]
    assert result.provider == "google-ai-studio"
    assert result.usage == {"prompt_tokens": 800, "completion_tokens": 120}


def test_teaching_beat_frames_are_extracted_at_model_selected_timestamps(tmp_path):
    commands = []

    def run(command, **_kwargs):
        commands.append(command)
        if command[0] == "yt-dlp":
            template = command[command.index("-o") + 1]
            from pathlib import Path

            path = Path(template.replace("%(ext)s", "mp4"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"video")
        elif command[0] == "ffmpeg":
            path = command[-1]
            from pathlib import Path

            Path(path).write_bytes(_png((10, 20, 30)))
        return type("Result", (), {"stdout": "", "stderr": ""})()

    materializer = YtDlpTeachingBeatFrameMaterializer(
        executable="yt-dlp",
        ffmpeg_path="ffmpeg",
        runner=run,
        temporary_root=tmp_path / "materializer",
    )
    frames = materializer(
        "https://www.youtube.com/watch?v=silent123", (14_000, 28_000)
    )

    assert [frame.timestamp_ms for frame in frames] == [14_000, 28_000]
    assert len(commands) == 3
    assert commands[0][0] == "yt-dlp"
    assert "--no-playlist" in commands[0]
    assert commands[0][-1] == "https://www.youtube.com/watch?v=silent123"
    assert commands[1][commands[1].index("-ss") + 1] == "14.000"
    assert commands[2][commands[2].index("-ss") + 1] == "28.000"
    assert all("-frames:v" in command for command in commands[1:])


def test_live_youtube_adapter_exposes_the_deep_teaching_beat_interface():
    expected = TeachingBeatDocument(
        beats=(
            TeachingBeat(
                start_ms=0,
                end_ms=5_000,
                frame_ms=3_000,
                heading="One visual lesson",
                explanation="The screen teaches one complete idea.",
                visible_text=None,
                visual_description="A diagram with one relationship.",
                limitations=None,
            ),
        ),
        frames=(
            videos.VideoFrame(
                timestamp_ms=3_000,
                body=_png((1, 2, 3)),
                mime_type="image/png",
                filename="beat.png",
            ),
        ),
        requested_model="fake/gemini",
        response_model="fake/gemini",
        provider="test",
        usage={},
        duration_ms=1,
        prompt_ref="video-teaching-beats/v001",
        prompt_sha="a" * 64,
        input_manifest_hash="b" * 64,
        result_hash="c" * 64,
    )

    class BeatAdapter:
        def acquire_visual_teaching_beats(
            self, source_url: str, *, duration_seconds: float | None
        ):
            assert source_url.endswith("watch?v=lesson123")
            assert duration_seconds == 5.0
            return expected

    adapter = videos.YtDlpYouTubeAdapter(
        executable="yt-dlp",
        ffmpeg_path="ffmpeg",
        api_key="test-key",
        teaching_beat_adapter=BeatAdapter(),
    )

    assert adapter.acquire_visual_teaching_beats(
        "https://www.youtube.com/watch?v=lesson123", duration_seconds=5.0
    ) is expected


def test_video_route_is_locked_to_google_ai_studio_without_fallbacks():
    assert openrouter_video_provider_routing() == {
        "only": ["google-ai-studio"],
        "allow_fallbacks": False,
        "data_collection": "deny",
    }


def test_provider_must_return_teaching_beats_in_timeline_order():
    def beat(start_s: int, end_s: int, frame_s: int) -> dict:
        return {
            "start_s": start_s,
            "end_s": end_s,
            "frame_s": frame_s,
            "heading": f"Beat {start_s}",
            "explanation": "A complete teaching explanation.",
            "visible_text": None,
            "visual_description": "A stable visual state.",
            "limitations": None,
        }

    with pytest.raises(ModelError, match="timeline order"):
        parse_beats(
            {"beats": [beat(20, 30, 25), beat(5, 10, 8)]},
            duration_seconds=40,
        )
