# 0022: YouTube acquisition produces multimodal source Markdown

Date: 2026-08-10
Status: accepted
Supersedes: ADR 0021
Partially superseded by: ADR 0023 for the `visual_only` route

## Context

A transcript-only YouTube Adapter loses whatever the instructor teaches on
screen. The loss is total for a silent animation, demonstration, slide deck,
diagram, or screen recording: a successful empty-audio decision produces no
useful source at all. It is also inconsistent with article acquisition, where
images are immutable evidence, interpreted in source context, and represented
as atomic elements before passage work begins.

The product needs one useful contract rather than a second video-specific
interpretation pipeline: transform a video into rich Markdown, preserve useful
frames with clear provenance, then feed that Markdown through the same Blocks,
Passages, triage, refinement, and canonical-publication Modules used by other
Sources.

## Decision

YouTube acquisition keeps the provider-free `yt-dlp` metadata preflight. A
publisher-uploaded caption track, when present, remains exact timestamped
speech evidence. If no publisher track exists, preflight v2 fetches only the
original YouTube automatic-caption VTT and parses it as a non-published
speech-presence probe, unless the metadata already proves there is no audio
stream. The probe URL, body, and text are discarded; they never become source
evidence, a ledger fact, or Markdown. Only its versioned result and bounded
diagnostics survive: `present`, `absent`, or `unknown`, plus a reason,
language/cue count when available, and failure category when needed.

Under `video-speech-policy/v2`, a proven-absent result—no audio stream or a
successfully fetched probe with zero cues—selects `visual_only` and performs
zero STT. A nonempty probe selects `automatic_stt`; an unavailable or ambiguous
probe defaults conservatively to the same route rather than silently losing
speech. That route means the existing durable, chunked, resumable OpenRouter
STT Implementation—never a local Whisper model or binary. Videos of at most
120 minutes enter it automatically. Longer videos and videos of unknown
duration retain the explicit paid-work authorization gate and enter OpenRouter
STT when authorized. Publisher-caption, OpenRouter-STT, and visual-only routes
all require frame extraction; speech never substitutes for the visual track.

Frame discovery is a narrow Adapter around the pinned
`@steipete/summarize@0.21.11` CLI on Node.js 24 or newer. The repository lockfile
is authoritative and installations use `npm ci`. The Adapter invokes
Summarize's dedicated `slides` command with a maximum of 20 slides, JSON
output, rendering disabled, and caches disabled. The child receives a blank
home, an allowlisted environment, and a `PATH` containing only `node`,
`yt-dlp`, `ffmpeg`, and `ffprobe`; cloud-provider credentials, local-model
endpoints, ONNX runtimes, and Whisper binaries are undiscoverable. Summarize
therefore selects candidate frames and calls local media tools; it does not
enter transcript selection, summarize, transcribe missing speech, OCR frames,
or call a model on CG Pipeline's behalf.

The Summarize output is untrusted Adapter input. Code verifies that the result
belongs to the requested YouTube id, accepts only unique positive slide
indices and finite non-negative timestamps, confines paths to the private
temporary directory, accepts the expected raster format, reads bytes before
the directory is destroyed, and removes byte-identical duplicates. Native
`yt-dlp`, `ffmpeg`, and `ffprobe` are runtime requirements for this
Implementation.

Caption groups and frames are deterministically interleaved by time. A frame
is initially represented by a `video-frame://` locator wrapped in a link to
the exact YouTube timestamp. Frames without speech are valid source content;
therefore a frames-only video produces Markdown instead of an empty-transcript
failure. Neither the temporary locator nor temporary filesystem path may reach
published Markdown.

Each extracted frame is stored as an immutable `source_asset(kind =
'video_frame')` in the existing content-addressed Asset Store. Postgres keeps
its hash, order, timestamp, extractor version, storage key, and candidate
state. The image-analysis Seam is intentionally shared with articles: one
source-level Gemini call receives the Markdown and all candidate frames under
stable ids. It compares frames with both the text and one another, retains only
frames that add distinct teachable information, and records OCR, visual
description, and limitations for each retained frame. Rejected or repetitive
frames remain auditable in the ledger but do not enter enriched Markdown.

A stored frame whose visual interpretation fails is primary video evidence,
not presumed decoration. It remains as an unresolved atomic image element and
is protected by the existing unknown-evidence behavior. A successful visual
association replaces the temporary locator with the same-origin Source Asset
URL while preserving the clickable YouTube timestamp.

The enriched Artifact, not the preliminary caption/frame manifest, is the
input to deterministic Blocks, Passage cuts, triage/refine/retriage, and
canonical clean Markdown. Each retained image, description, OCR, limitation,
asset reference, and timestamp link is one atomic image Block. No
post-publication interpretation exists in this pilot. This keeps the new
Adapter shallow and the publication Module deep.

## Consequences

- Silent and visually taught videos can become useful source Markdown without
  inventing speech or paying for STT when the presence probe is successfully
  empty.
- Spoken or probe-ambiguous uncaptioned videos default to durable OpenRouter
  STT, avoiding silent loss of speech while never running local Whisper.
- Captioned videos preserve exact speech while gaining visual evidence from
  the same timeline.
- Summarize owns candidate-frame extraction only; CG Pipeline owns
  evidence storage, model policy, relevance, Markdown composition, and
  publication.
- Near-duplicate and low-value frames are decided once with full source
  context. Byte-identical duplicates are removed deterministically before the
  model call.
- Frame bytes use the local Asset Store contract and are retrievable by
  the same authenticated Source Asset Interface as article and manual images.
- Worker deployments add Node.js 24+, the pinned npm dependency, `yt-dlp`,
  `ffmpeg`, and `ffprobe`; routed STT and frame analysis need the existing
  OpenRouter-compatible credential, while Summarize receives none of it.
- ADR 0021's transcript-only and `visual_analysis: deferred` publication
  contract is retired. Its durable caption and OpenRouter STT ledgers are
  retained and reused by this multimodal flow.
