# 0021: YouTube transcript acquisition is resumable and transcript-only

Date: 2026-08-10
Status: superseded by ADR 0022

ADR 0022 replaces the transcript-only publication decision with multimodal
video evidence. This record remains the rationale and ledger contract for the
caption and legacy STT Implementations that already exist.

## Context

The Syllabus already gives YouTube Sources stable identity, but it had no
operating Adapter. A video cannot be treated as ready merely because captions
or one speech-to-text response were obtained: the published source must pass
through the same element-preserving canonical cleanup as other Markdown.

The earlier CG Pipeline policy prohibited automatic speech-to-text when a
publisher caption was absent. That decision belongs to a different system and
does not govern Concept Universe. Video visual analysis is also a separate,
future capability; transcript acquisition must not imply that the visual
content was read.

## Decision

YouTube acquisition begins with a refreshable, provider-free metadata
preflight. It records stable video identity, title, channel, duration and only
publisher-uploaded subtitle languages. YouTube's `automatic_captions` catalog
is ignored. The immutable preflight selects exactly one route:

- `uploaded_caption` when a publisher track exists;
- `automatic_stt` when no publisher track exists and duration is at most 120
  minutes, including exactly 120:00;
- `approval_required` when duration is longer than 120 minutes or unknown.

Long or unknown-duration transcription requires an explicit UI authorization.
The authorization, exact preflight id, route, grouping version, chunk size,
model route and operation version are persisted as job input and included in
the input fingerprint. Repeated clicks reuse the same active paid-work chain.

The caption route downloads VTT for the selected publisher track only. The
original VTT bytes, hash, language and canonical public YouTube URL are
immutable evidence. A listed track that fails to download or parse is an
explicit retryable failure and never falls through to automatic captions or
STT.

The STT route downloads audio only, normalizes it with `ffmpeg`, and splits it
into deterministic 60-second MP3 chunks. Chunk work is durable before paid
calls. Identity includes Source, audio and chunk hashes, time window, language,
model route and operation version. Workers claim chunks with leases; succeeded
chunks are globally reusable by retries. Every primary and fallback attempt
records requested and response model, provider, generation id, language,
usage, duration and failure. The default route is
`openai/whisper-large-v3`, falling back once to `openai/whisper-1` only after
an eligible primary failure. Temporary audio is deleted after chunk
materialization and neither audio nor signed media URLs enter Postgres.

Caption cues and STT segments remain ordered timestamp facts, separate from
Markdown. `timestamp-groups/v1` joins exact adjacent text until the first of a
45-second span, 700 characters, or a gap over four seconds is reached. It
never summarizes, rewrites or invents content. The thresholds were checked
against the real publisher track for YouTube `UFtXy0KRxVI`: 129 cues with a
2.85-second median cue became 9 groups, with a maximum 44.39-second span and
673 characters, while preserving exact cue order and text.

The deterministic timestamped transcript Artifact is intermediate. A
provider-neutral publication contract queues Blocks, Passage cuts,
triage/refine/retriage and a canonical clean Artifact. Cleanup may remove only
immutable elements; it cannot rewrite transcript text. The Syllabus modal
withholds intermediate captions and STT and resolves only the succeeded
canonical Artifact on the newest Source Snapshot. Task and KC generation are
not part of this operation.

Every video acquisition and canonical Artifact is stamped
`visual_analysis: deferred`. No frames, screenshots, images, OCR, multimodal
calls or `video-frame://` placeholders are produced.

## Consequences

- Publisher captions cost no STT calls; uncaptioned videos up to two hours can
  complete from the ordinary Process action.
- One failed chunk can be retried without paying again for successful siblings.
- Preflight, caption evidence, STT attempts, transcript facts, cleanup and
  publication remain independently auditable.
- Article and video publication share an artifact-lineage capability rather
  than a provider-name check.
- A canonical transcript is complete for spoken evidence but explicitly not
  visually complete.
- Worker deployments require `yt-dlp`, `ffmpeg`, `ffprobe` and an OpenRouter
  credential for the STT route.
