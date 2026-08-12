# 0014: First-class images and element-preserving passage cleanup

Date: 2026-08-07
Status: accepted

PDF-specific cleanup immunity was superseded by ADR 0018. The unresolved-image
safety rule and atomic image Block rules remain accepted.

## Context

An acquired page is not faithfully represented when its images are appended
after text processing or interpreted one at a time without the source around
them. The old article-image branch also allowed passage segmentation to start
from base Markdown while image work was still running. That made the visual
content invisible to passage boundaries and created two competing relevance
decisions: an early metadata heuristic and a later model judgment.

The source-cleaning problem has a related constraint. A passage can contain
both teachable content and removable material. A passage-only keep/drop gate
either preserves noise or loses useful content. Letting a model rewrite the
passage would solve neither problem: the canonical source must remain an
auditable projection of acquired evidence, not newly generated prose.

## Decision

The canonical source path is:

    raw Markdown and image candidates
        -> durable image assets and one source-level visual call
        -> ordered enriched document
        -> deterministic atomic blocks
        -> passage cuts
        -> triage -> refine -> triage
        -> canonical cleaned Markdown
        -> optional task generation

### Images

Image discovery runs alongside textual acquisition. Before the visual model,
code may reject only technical impossibilities such as an invalid or unsafe
URL, an unreadable payload, a byte-identical duplicate, or an unsupported
image. Filename, placement, dimensions, alt text, or apparent site-chrome
semantics are not sufficient to delete an otherwise valid image.

Downloaded originals remain immutable assets in object storage. Postgres
stores identity, hashes, order, lineage, analysis state, and references; it
does not store the binary bodies or multimodal data URLs.

All downloaded article images for one Markdown artifact are presented with
that source in one forced structured visual call. Every image has a stable
identifier. The response decides whether the image remains and, for retained
images, records meaningful visible text, a description of visual information,
and any analysis limitation. A missing, duplicated, malformed, or failed
result affects only that image. It is represented as unresolved and preserved
rather than silently discarded.

The text artifact may therefore succeed while visual work is incomplete or
partially failed. Passage processing, however, resolves the terminal enriched
artifact and never races ahead on raw or base Markdown. This supersedes ADR
0013 only where that ADR allowed downstream textual processing to run before
the article-image branch had reached a terminal state.

Each retained image and its derived fields become one atomic image block.
Refinement may ordinarily remove that whole block, but can never detach its
OCR, description, limitation, or asset reference. ADR 0016 adds a narrower
loss-prevention rule for enriched PDF-page visuals, because those atoms are
the primary representation of information missing from the exact text layer.
An unresolved image is protected: its passage terminates as `unknown` and the
image remains in canonical output.

### Passage cleanup

Passage cuts continue to group adjacent deterministic blocks and do not copy
or rewrite their text. Triage has four verdicts:

- `keep`: preserve the current passage state;
- `drop`: remove the passage from canonical Markdown;
- `refine`: ask for atomic elements that should be removed, then triage the
  resulting state again;
- `unknown`: preserve the current state when a safe decision cannot be made.

Refinement returns only local numbered element identifiers. Code maps them to
immutable block identifiers and materializes a child revision by omission.
It rejects duplicate or out-of-range identifiers, deletion of all remaining
content, deletion of unresolved images, and refinement of a one-element
passage. An empty removal list makes no progress and terminates safely as
`unknown`. Every valid child removes at least one element, so the loop is
finite without an arbitrary iteration limit.

The canonical Markdown is assembled deterministically from terminal `keep`
and `unknown` states. `drop` states are omitted. Original artifacts, blocks,
passages, model calls, revisions, and removal lineage remain queryable.

Task generation consumes the exact terminal passage revision. `keep` and
`unknown` are eligible, `drop` is not, and `refine` is never terminal. A valid
task-generation response may contain zero tasks when a preserved passage has
no suitable learner task.

## Consequences

- Visual meaning can influence passage boundaries without making image
  failures invalidate successful textual acquisition.
- Relevance is judged once with source context instead of by competing
  semantic filters.
- Cleaning cannot hallucinate, paraphrase, or subtly change acquired text.
- Unknown evidence is visible and preserved rather than treated as approval or
  deletion.
- Block-version stamps are part of cuts lineage; old cuts keep their original
  numbering after the image-aware blocker is introduced.
- A source-level image call owns usage and provider telemetry once, while each
  image retains an independently auditable outcome.
