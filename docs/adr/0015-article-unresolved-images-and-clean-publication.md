# 0015: Article image failures do not become source evidence

Date: 2026-08-07
Status: accepted

## Context

ADR 0014 preserved an unresolved image in canonical Markdown and marked its
whole passage `unknown`. That was safe for primary evidence, but wrong for an
incidental image discovered in a public article. Unsupported menu SVGs,
broken image-proxy URLs and inaccessible logos consequently protected nearby
cookie controls, biographies, recommendations and footers from cleanup.

The Syllabus UI also treated acquisition or image completion as “Markdown
ready”, even though passage cleanup was only being run manually. A reextract
could therefore publish the newest intermediate artifact and look complete in
seconds without ever running cuts, triage or refinement.

## Decision

Article images and manually supplied evidence have different failure
semantics.

For a public article, a visual result classified as useful is rendered with
its asset reference, OCR, description and limitations. An irrelevant result
is omitted. An unresolved result is also omitted from the Markdown projection.
Its candidate, asset when available, failure code, diagnostics and lineage
remain in the ledger for inspection or retry. It creates no unresolved block
and therefore cannot change the triage state of adjacent text.

For a manual screenshot, ordered image set or PDF page, the visual object is
the source evidence. A failed analysis keeps the object and an unresolved
marker. The source is presented as incomplete/attention and is not silently
cleaned as though the evidence were optional.

A public-article reextract is one user-visible pipeline backed by separate
durable jobs:

    Firecrawl
      -> image downloads and grouped visual analysis
      -> enriched Markdown projection
      -> deterministic blocks
      -> passage cuts
      -> triage / refine / retriage
      -> clean Markdown artifact

The acquisition, visual and cleanup facts remain separately auditable. The UI
does not expose base or enriched Markdown as the final result for jobs stamped
with this pipeline contract. It reports the pipeline as ready only when the
cleanup job owns a succeeded canonical artifact, and the Markdown modal
resolves that artifact from the newest acquisition snapshot. Refreshes and
repeated queue actions reuse an active acquisition/image/cleanup chain rather
than creating a second paid chain.

Task generation is not part of this user action.

This decision supersedes ADR 0014 only for the unresolved-image retention and
whole-passage protection rules on incidental public-article images. ADR 0014
continues to govern atomic enriched images, element-preserving refinement and
the protection of unresolved primary manual evidence.

## Consequences

- A visual provider failure cannot keep article chrome or boilerplate alive.
- Article text and successfully analyzed sibling images continue through
  cleanup when one candidate fails.
- Auditability is retained without conflating failure records with canonical
  educational content.
- “Markdown ready” becomes a statement about the clean artifact, not merely a
  successful fetch.
- Manual evidence fails visibly and conservatively rather than disappearing.
