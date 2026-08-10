# 0016: Page-aware PDF acquisition

Date: 2026-08-10
Status: accepted

## Context

ADR 0013 treated a PDF as either a textual document for `pdftotext` or an
image set that the operator had to create manually. That split loses document
structure in born-digital PDFs and rejects mixed or scanned documents even
though every PDF page is already an ordered visual surface. Multi-column text,
tables, diagrams and headings can become unreadable while the extraction still
looks technically successful.

## Decision

Every uploaded PDF is acquired page by page. The original PDF remains the
immutable primary asset. Poppler extracts the text layer and renders a stable
PNG for every page. Each ordered page becomes an immutable `source_pdf_page`
fact with its exact text, text hash, text-layer status and render asset. Derived
page images are content-addressed `source_asset(kind = 'pdf_page')` facts; they
do not replace the PDF.

The visual model receives page renders together with their corresponding text
layers. Calls group adjacent pages only to satisfy request-byte and context
limits; there is no arbitrary page-count cap. The prompt asks for one result
per stable page id and retains visual material only when it contributes
information that the text layer does not faithfully express. Tables, diagrams,
spatial relationships and meaningful typography may therefore become atomic
image elements. Ordinary page text is emitted once from the text layer and is
not repeated as model OCR or prose.

For a page without usable text, the render is primary evidence. Its model
result must retain and reconstruct meaningful OCR or description. A missing,
malformed or failed page result remains an independently auditable failed
analysis; successful sibling pages are preserved, but the Source enters an
attention state and is not published as canonical Markdown.

`pdf_page_analysis_call` records each paid grouped call once, including prompt,
model, provider, input manifest, usage and duration. `source_asset_analysis`
records the reconciled result for each page. Deterministic raw page Markdown
and visually enriched Markdown are separate Artifacts. When every page is
resolved, the enriched Artifact enters the same durable passage-cleanup queue
used by article acquisition. The Syllabus UI publishes only the succeeded
cleanup Artifact. Reprocessing the same terminal acquisition does not repeat
page calls or create duplicate page facts.

A retained PDF-page visual is primary evidence for information the exact text
layer could not represent. Cleanup may remove surrounding text elements, but
must not remove an enriched image atom or drop the passage that contains it.
If a model proposes either action, code preserves the current passage and
records `primary_enriched_image_preserved` separately from the model's paid
decision. This policy is activated only by PDF-pipeline Artifact metadata;
article-image cleanup keeps ADR 0014's ordinary relevance behavior.

This decision supersedes ADR 0013's textual-PDF-only rule and its instruction
to re-upload scanned PDFs as ordered images. ADR 0013 continues to govern
Source identity, immutable external asset storage and explicitly ordered image
uploads.

## Consequences

- Born-digital, scanned and mixed PDFs use one acquisition path.
- Reading order and page provenance remain inspectable even when layout
  reconstruction is imperfect.
- Page renders make vector diagrams and tables visible to the model even when
  the PDF has no embedded raster images.
- A multi-page table continuation cannot disappear merely because cleanup
  mistakes one page for context-free citation or boilerplate.
- One unresolved page cannot silently disappear or invalidate successful
  siblings, but it blocks clean publication until addressed.
- Poppler must provide `pdfinfo`, `pdftotext` and `pdftoppm` in the worker
  runtime; visual model credentials are required for PDF acquisition.
- PDF model cost scales with rendered pages and technical batch limits, and is
  visible through durable per-call usage records.
