# 0023: Visual-only videos are interpreted as teaching beats once

Date: 2026-08-10
Status: accepted
Supersedes: ADR 0022 for the `visual_only` route

## Context

ADR 0022 fixed transcript-only video acquisition by sampling frames with
Summarize and sending those candidates through the grouped source-image
Module. That is effective when speech supplies the document spine. It is too
sparse for a visual-only lesson: a sampler does not know which screen changes
teach a new idea, and a later image-relevance call sees isolated candidates
rather than the full temporal sequence.

The older acquisition path demonstrated the missing capability by giving the
whole video to Gemini, but it emitted unresolved `video-frame://` placeholders
and did not preserve frame evidence. The desired Module needs whole-video
understanding and the current system's durable visual atoms.

## Decision

The speech policy in ADR 0022 remains unchanged. Publisher captions win;
present or ambiguous speech defaults to durable OpenRouter STT; proven absence
selects `visual_only`; local Whisper is never used.

`visual_only` deepens one Visual Teaching Beats Module with this Interface:

    acquire_visual_teaching_beats(
        source_url,
        duration_seconds,
    ) -> TeachingBeatDocument

Its OpenRouter Gemini Adapter sends the full YouTube URL in one forced-tool
call routed only to Google AI Studio, the provider compatible with YouTube
video URLs. The model reports ordered major teaching beats at whole-second
precision. Each beat contains a time range, stable representative timestamp,
heading, teaching explanation, visible text, visual organization and optional
pixel-level limitation. The prompt excludes title cards, repetition,
promotion and irrelevant player chrome. Application validation bounds the
result, rejects malformed ordering, out-of-range timestamps, duplicate frame
identities and missing educational descriptions.

After interpretation, the Adapter downloads the video once and materializes
one 720p frame at each selected timestamp. Frame bytes are validated and enter
the existing content-addressed Asset Store as immutable
`source_asset(kind='video_frame')` facts.

The `TeachingBeatDocument` is the sole semantic visual decision for this
route. Its call, provider/model/usage stamps, input hash, result hash and full
ordered result are recorded in the grouped visual-call ledger with operation
`video_teaching_beats`. Each representative frame is immediately terminal and
useful, with a per-asset `video_teaching_beat` analysis projected from the same
result. The generic source-image model call is not queued, so the system does
not pay twice or let a second model discard already-selected evidence.

Code renders headings and timestamp-linked frame locators, then the existing
association Implementation localizes each image and attaches the teaching
explanation plus visual organization as `Image description`, visible text as
`OCR`, and uncertainty as `Image limitations`. Those fields and the frame are
one ordinary atomic image Block. Blocks, Passage cuts, triage,
refine/retriage, canonical publication and later KC extraction remain
source-neutral and unchanged.

Caption and OpenRouter-STT routes keep ADR 0022's Summarize candidate-frame
Adapter and grouped contextual image analysis because speech already provides
their document spine and the visual task is supplemental selection.

## Consequences

- A silent slide, diagram or screen lesson can recover every major visual
  teaching beat instead of depending on sparse uniform samples.
- The final Markdown retains real frame evidence, exact YouTube timestamp
  links, OCR and explanatory context while remaining compatible with the
  existing Passage Module.
- One paid whole-video call owns visual interpretation; representative-frame
  extraction and Markdown projection are deterministic Implementations behind
  that Interface.
- Non-teaching candidates can still be removed by the ordinary Passage triage
  Module without risking loss of the instructional beats.
- YouTube-URL compatibility deliberately trades provider fallback for a
  fail-closed Google AI Studio route.
- A crash between the paid interpretation and successful frame materialization
  can still repeat the model call on retry. If observed operationally, the
  existing visual-call ledger should deepen into an interpreted → materialized
  continuation without changing the public Interface.
