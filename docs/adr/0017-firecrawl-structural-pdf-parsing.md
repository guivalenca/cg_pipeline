# 0017: Firecrawl is the structural PDF adapter

Date: 2026-08-10
Status: accepted

## Context

ADR 0016 reconstructed PDFs from Poppler text layers and full-page vision. In
acceptance testing this published page screenshots containing unrelated prose,
while tables remained prose instead of Markdown tables. The model was choosing
pages, not extracting document elements, so its output could not be close to a
one-to-one structural conversion.

Firecrawl `/v2/parse` accepts private PDF bytes and returns document Markdown in
reading order, including Markdown tables and extracted image references. The
application already owns block and passage construction, so another semantic
chunking system is unnecessary.

## Decision

For an explicitly consented PDF upload, the worker calls Firecrawl `/v2/parse`
with `markdown` and `images` formats and PDF mode `auto`. Firecrawl Markdown is
the canonical acquisition input. The paid call and its response are recorded
once in `pdf_document_parse_call`; a reclaimed worker reuses that response.

Every returned figure is downloaded immediately and stored as immutable
`source_asset(kind = 'pdf_figure')` evidence. Remote or embedded image
references in the Markdown are rewritten to local asset URLs. A localized
figure and its provider label form one atomic image block. A failed figure
download leaves the source in attention and blocks cleanup, without deleting
the successfully parsed text or tables.

Firecrawl currently omits vector diagrams even in OCR mode. When a page has an
explicit figure caption (or lacks a text layer) and Firecrawl returned no
figure asset, an independently consented OpenRouter/Gemini call may locate
tight 0–1000 bounding boxes. Version 2 uses named `left`, `top`, `right`, and
`bottom` fields so coordinate order is not implicit, and requires the full
connected visual rather than its most salient fragment. The worker crops those
regions locally and stores only the crops as `pdf_figure` assets. Full-page
boxes, ordinary prose, and tables already represented in Markdown are forbidden
by validation and prompt.

Model boxes are advisory geometry, not sufficient evidence of completeness.
Poppler also extracts the first explicit figure-caption position from the PDF
text layer. When a candidate box ends above a lower caption, the local crop is
extended to the whitespace immediately before that caption. The model box,
caption position, and deterministic adjustment are retained in asset metadata.
This guard recovered terminal nodes omitted by Gemini in the real Figure 1
acceptance page without another external request or publishing the caption and
following prose.

Poppler still records exact page text and stable page renders in
`source_pdf_page`, but those renders are audit evidence only. They are never
inserted into published Markdown and are never sent through the previous
full-page Gemini selector. Firecrawl does document extraction; the existing
block and passage pipeline remains responsible for semantic organization.

Private PDF export is disabled unless
`FIRECRAWL_ALLOW_PRIVATE_PDF_UPLOADS=1`. The upload dialog names Firecrawl and
requires the operator's explicit submission before the file is queued. The
separate `OPENROUTER_ALLOW_PRIVATE_PDF_PAGE_UPLOADS=1` gate controls candidate
page export for diagram localization.

This decision supersedes ADR 0016's full-page visual selection and text-layer
publication rules. ADR 0016 continues to describe the immutable Poppler audit
ledger and the protection of primary visual evidence.

## Consequences

- Tables arrive as Markdown tables rather than page screenshots.
- Figures and diagrams are standalone local assets, not whole PDF pages.
- PDF acquisition no longer incurs one Gemini vision interpretation per page.
- Only caption-bearing or text-layer-empty candidate pages can reach Gemini;
  crop completion after localization is local and deterministic.
- Firecrawl cost scales with pages parsed and is reported as estimated credits.
- A Firecrawl outage or disabled private-export setting prevents PDF parsing;
  Poppler audit data is not silently promoted to canonical content.
