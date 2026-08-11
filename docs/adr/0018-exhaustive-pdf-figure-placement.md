# 0018: Exhaustive PDF figure placement precedes passage cleanup

Date: 2026-08-10
Status: accepted

## Context

ADR 0017 made Firecrawl Markdown the structural PDF representation and used
Gemini only as a fallback for caption-bearing or text-empty pages. The fallback
stopped entirely when Firecrawl returned any image. In real acceptance PDFs,
that source-level shortcut preserved one large cited figure but missed several
small diagrams on other pages. Recovered crops were also appended to a global
`Extracted figures` section, detaching them from the Blocks and Passages that
explain them.

ADR 0016 separately made enriched PDF visuals immune to passage cleanup. Once
figure discovery is exhaustive and every crop is attached to its explanatory
context, that structural override creates a second relevance decision and can
preserve useless images against triage/refine.

## Decision

One deep PDF Figure Placement Module owns Firecrawl image localization,
technical page batching, durable Gemini localization calls, region validation,
crop persistence, deduplication, Markdown anchoring, placement outcomes, and
diagnostics. Its public Interface receives the canonical Firecrawl Markdown,
the persisted Poppler pages, and the existing Adapter seams for image download,
asset storage, and semantic localization. PDF orchestration does not know how
those operations are implemented.

Every persisted page enters exactly one technically bounded Gemini call,
regardless of whether Firecrawl returned zero, one, or multiple images. There
is no page-classifier Adapter and no caption-only candidate gate. Gemini returns
zero, one, or multiple informative non-table regions per page. An empty region
array is a successful result; a disabled or failed call remains an explicit
attention outcome.

At most eight adjacent page renders enter one localization call. This is a
technical coordinate-reliability limit, not a semantic candidate filter: a
24-page acceptance call correctly described the page-8 workflow but bound it
to page 4 and cropped prose. Version 4 also checks meaningful returned visible
text against every usable text layer in the batch. Strong evidence that a
region belongs to another page becomes an auditable attention outcome instead
of a silently published crop.

Before each call, the Module exposes deterministic `md-block-...` identifiers
for the canonical Markdown Blocks. Each accepted region may reference the
caption, explanatory paragraph, or heading that owns it. The crop is inserted
immediately before that Block, so block and passage construction see the image
in its teaching context. A region without a valid anchor is still preserved,
but only under the explicit `Extracted figures (unanchored)` fallback heading.

Provider region order does not define identity. Regions are sorted by page and
geometry before crop ordinals are assigned. Each semantic region writes an
immutable outcome row connecting the durable call to its page, model and final
boxes, anchor, terminal status, and asset when present. `placed`, `unanchored`,
and `duplicate` are successful terminal outcomes; crop/provider failures remain
auditable and prevent silent clean publication.

Model geometry receives a deterministic local polish before cropping. A small
side/bottom margin prevents tangent circles, arrowheads, and labels from being
clipped. On pages with multiple independent regions, Poppler's exact text-line
boxes identify the visual gaps between prose bands; regions are assigned to
those gaps monotonically and only Gemini's drifting vertical axis is replaced.
Both the model and final boxes remain in the region ledger, so this correction
is inspectable and replayable without another provider call.

Firecrawl remains authoritative for headings, prose, formulas, lists, and
tables. The Module may only rewrite remote image URLs and insert atomic image
Blocks with descriptions/OCR. Poppler page renders remain audit evidence and
crop sources; full pages are never published.

Enriched PDF figures now follow ordinary passage triage and refinement. Code no
longer changes a model `drop` into `keep`, and the triage prompt no longer gives
enriched images semantic immunity. Unresolved images retain ADR 0014's safety
rule because their relevance has not been successfully decided.

This decision supersedes ADR 0017's caption-only/candidate-page Gemini rule and
its no-per-page-call consequence. It supersedes ADR 0016's PDF visual cleanup
immunity. ADRs 0014, 0016, and 0017 continue to govern atomic image Blocks,
immutable page evidence, and Firecrawl's structural role respectively.

## Consequences

- Small and multiple diagrams no longer depend on caption heuristics or on
  Firecrawl returning no images.
- Diagram placement has Locality: the resulting Block and Passage contain both
  the crop and the text that explains it.
- All-page semantic inspection increases Gemini input cost, while eight-page batching,
  durable call reuse, and zero-region results keep the process simple and
  idempotent.
- Every returned region has an inspectable terminal outcome instead of
  disappearing between model output and Markdown.
- Cleanup can remove irrelevant figures, so final retention is observed through
  ordinary cleanup decisions rather than guaranteed by PDF-specific policy.
