# Gemini video acquisition

Full-video acquisition for YouTube URLs and direct video files. This runner creates the same downstream-facing artifact family as the Firecrawl article path: markdown with YAML frontmatter, `metadata.json`, `request.json`, `raw_response.json`, `gate_report.json`, `source_manifest.json`, run logs, and summary output.

The pipeline is intentionally two-pass:

1. Pass 1 gets an audio-only transcript using the local `legacy_extract_videos.py` helpers. Manual YouTube captions are used when available; otherwise local Whisper runs with VTT output so timestamps are preserved. Pass 1 is cached by source fingerprint and transcript settings.
2. Pass 2 calls Gemini with the video media and the Pass 1 transcript as temporal grounding. Gemini is instructed to focus on visual content and emit timestamped markdown with explicit spoken/on-screen slots and regex-able inline frame placeholders such as `![diagram: ...](video-frame://14@00:12:30)`.

## Setup

Install dependencies from the repo root:

```sh
python3 -m pip install -r requirements.txt
```

Set Gemini credentials:

```sh
export GEMINI_API_KEY=...
# or
export GOOGLE_API_KEY=...
# existing local pipeline envs may also use GOOGLE_API_KEY_ADMIN
```

For the audio grounding pass, keep the existing local video settings:

```sh
export CG_PIPELINE_WHISPER_CPP_BINARY=/path/to/whisper-cli
export CG_PIPELINE_WHISPER_MODEL=/path/to/ggml-large-v3-turbo-q5_0.bin
```

On this workstation, Whisper is installed outside `PATH`. The runner now checks
these local defaults automatically:

```text
~/.local/bin/whisper-cli
~/.local/share/whisper.cpp/models/ggml-large-v3-turbo-q5_0.bin
~/.local/share/whisper.cpp/models/ggml-large-v3-q5_0.bin
```

If a machine uses a different install location, set
`CG_PIPELINE_WHISPER_CPP_BINARY` and `CG_PIPELINE_WHISPER_MODEL` explicitly.

## Run

From `cg_pipeline/`, default triage profile using copied `url.json`:

```sh
python3 video/extract_videos.py
```

Selected ids:

```sh
python3 video/extract_videos.py --only 14,78
```

Escalate a flagged video with the denser Pro profile:

```sh
python3 video/extract_videos.py --only 78 --profile dense --force
```

Override the cost knobs explicitly:

```sh
python3 video/extract_videos.py --fps 0.25 --media-resolution low --model gemini-2.5-flash
```

## Outputs

Artifacts are written under:

```text
video/output/{id}/
```

Cache entries are written under:

```text
video/cache/pass1/{cache_key}/
video/cache/gemini/{cache_key}/
```

The Gemini cache key includes the video source, Pass 1 transcript hash, Gemini model, FPS, media resolution, prompt version, prompt hash, and chunk window. Re-running downstream phases or re-rendering artifacts from cached Gemini responses does not re-burn API quota unless `--refresh-cache` is used.

## Quality gates

A run writes `gate_report.json` per video. Failures use `acquisition_failed` and include explicit reasons, including empty output, missing timestamps, title mismatch, invalid duration, and timestamp span that does not plausibly cover the video duration. Warnings are kept separate for short content, unknown duration, missing visual placeholders, and timestamps slightly beyond the probed duration.
