# 0019: Ordered raster sources reuse the PDF reconstruction Module

Date: 2026-08-11
Status: accepted

## Context

Manual screenshots and authenticated book-reader pages are the same domain
shape: an explicitly ordered sequence of immutable page images. The previous
manual path described each image independently, while the earlier book branch
published whole-page images and then ran a second visual reconstruction job.
Both Implementations lost document-wide reading order and repeated work that
the PDF path already performs for structure, figures, Blocks, Passages, and
cleanup.

Firecrawl can reconstruct a PDF structurally, including headings, formulas,
lists, and tables. ADR 0018 already gives the PDF Figure Placement Module
exhaustive page coverage, durable Gemini calls, local crops, Markdown anchors,
and explicit attention outcomes. Reimplementing any of those responsibilities
for screenshots or books would create a shallow parallel pipeline.

## Decision

Create one deep Ordered Reconstruction Module. Its Interface accepts a title
and ordered page evidence. A page carries its immutable raster asset and may
carry exact reader accessibility text. The Implementation validates contiguous
order, decodes each page, normalizes it losslessly to PNG, derives one
image-only transport PDF, and calls the existing PDF document acquisition
Interface in forced OCR mode.

The transport PDF is an immutable `ordered_document_pdf` asset, but it is an
Implementation detail and is never presented as the original source. Firecrawl
owns document-wide structural reconstruction. The existing PDF Figure
Placement Module sees every original normalized page render and owns figure
localization and placement exactly as defined by ADR 0018. Full-page evidence
remains audit-only and is never published in Markdown.

Original PDFs, manual ordered images, and Browserbase book capture are thin
Adapters:

- a native PDF supplies its bytes directly to PDF acquisition in `auto` mode;
- manual images supply their persisted upload assets in visible user order;
- Browserbase supplies one captured `book_page` at a time and exact reader text,
  committing every page before navigating to the next.

Browserbase capture is resumable on a contiguous completed prefix and holds an
exclusive persistent-context lease. Its session is released before Firecrawl
or Gemini is called. Exact reader text is preserved as a separate immutable
fact and is available to page-local validation; it does not override OCR
structure or formulas because reader accessibility layers can themselves be
wrong.

The Browserbase Adapter must prove that the reader page fits on both axes. It
checks the page root's client and scroll dimensions plus the bounds of visual
descendants, grows the viewport through a bounded sequence, and fails
retriably if any content still overflows. Only the reader page element may be
captured; falling back to a viewport or body screenshot would reintroduce
reader chrome and silent vertical clipping. DOM geometry is necessary but not
sufficient: the captured bitmap must also expose the reader's lower navigation
divider with safe visual clearance. Both row density and aggregate ink detect
sparse rotated captions in that clearance band. The Adapter removes the entire
verified-empty band with the chrome and clears reader hover/focus state before
capturing; otherwise it grows the viewport and captures again.

Gemini's semantic figure box is also not trusted as a pixel-perfect crop. The
Figure Placement Implementation applies a bounded asymmetric safety envelope,
with extra horizontal and lower-page room for rotated and tall diagrams.
Captions may remain inside a crop; losing a node, label, arrow, or connector is
the higher-severity failure.

There is no separate publication-quality Module. Essential invariants live at
the reconstruction boundary: ordered pages must be contiguous and decodable,
the derived PDF must stay within Firecrawl's limit, the durable parse must use
OCR, every page must reach figure localization, unresolved visual work blocks
cleanup, and only canonical cleanup output becomes visible.

Private export remains explicit. Manual submission names Firecrawl and
OpenRouter/Gemini. Book extraction additionally names Browserbase and the exact
book scope. The worker still stops at canonical Markdown; Tasks and Knowledge
Components are not started.

## Consequences

- Ordered reconstruction has Depth: callers provide evidence and do not know
  PDF packaging, provider options, durable call ledgers, crops, or anchoring.
- The PDF pipeline gains Leverage because three input modes share one
  structural and visual Implementation.
- Figure/text Locality and the cleanup Seam are identical for native PDFs,
  screenshots, and book pages.
- The old per-image description and whole-page book reconstruction paths pass
  the deletion test and are removed.
- A malformed, incomplete, oversized, or visually unresolved document fails
  closed instead of publishing a lower-quality alternate representation.
