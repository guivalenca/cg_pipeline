# 0013: Manual evidence and the non-blocking article-image branch

Date: 2026-08-06
Status: accepted

## Context

A Syllabus reference can be valid even when its original URL cannot be
acquired: the page may require authentication, be an interactive document, be
blocked by the provider, or render the wrong material. In those cases the
founder may have the same source as a PDF, screenshots, scans, or photographs.
Treating that evidence as a replacement Source would break identity and
provenance. Silently inserting it into the current Syllabus Version would also
confuse acquisition with curricular editing.

Visual evidence has an additional requirement: its order is meaningful. A set
of page captures cannot be reconstructed faithfully if the upload boundary
forgets which image came first. The resulting Markdown must keep the images
available to a human reader, not reduce them to model-generated prose alone.

## Decision

Manual upload is a second acquisition path for the **existing Source**. It does
not create a Source, change the Syllabus, or erase an earlier failed attempt.
The operator explicitly queues exactly one of these mutually exclusive inputs:

- one PDF; or
- one to 50 ordered PNG, JPEG, or WebP images (screenshots, scans, or photos).

The combined upload is limited to 30 MB. MIME type, original safe filename,
SHA-256, byte size, kind, ordinal, and a `storage_key` are stored as immutable
`source_asset` facts before extraction begins. The binary body lives outside
Postgres: on a managed local filesystem in development and S3-compatible object
storage in deployed environments. Reordering is completed before submission;
the persisted ordinal is part of the evidence and determines the Markdown
order. A retry or a different upload creates a new acquisition job and new
assets beside the old ones.

A PDF is converted into ordered page text and page renders, then processed
through the page-aware path defined in ADR 0016. Born-digital, scanned and mixed
PDFs therefore share one evidence model. Each separately uploaded image is
preserved and processed through a forced structured
vision tool call. The generated Markdown embeds the immutable image and places
both a visual description and a transcription of meaningful visible text next
to it. Model, provider, prompt/tool version, usage, and timing remain stamped
in acquisition diagnostics.

Article images use the same immutable asset representation, but **not** the
same acquisition semantics as manual screenshots. Images discovered in an
article are an additional branch that begins alongside textual acquisition,
not a post-hoc scan and not a prerequisite for textual Markdown:

Model requests may transport a local raster as an inline `data:` URL, but that
transport payload is never durable state. The ledger stores only its transport
kind, source/reference IDs, hashes, model stamps, usage, and outcome; the bytes
remain exclusively in object storage.

1. collect image candidates with the source response;
2. apply a cheap metadata/URL/placement filter to discard only obvious logos,
   icons and exact duplicates;
3. download only the surviving candidates;
4. queue their structured visual readings independently so workers can run
   them concurrently with downstream textual work and with one another;
5. persist each successful image and its stamped reading in the asset ledger;
6. associate it with the Source and corresponding canonical Markdown.

Each candidate has its own state. A download or visual-reading failure becomes
an individual attention item with diagnostics; it never invalidates, delays,
or retries otherwise successful textual Markdown. A surviving relevant image
must still be preserved and referenced when its branch succeeds—model prose
alone is not a substitute for the image.

In the manual screenshot path, by contrast, the ordered images **are the
source material**. They collectively form the Markdown Artifact, so their
order and successful reconstruction are part of that acquisition's success.

Success creates a new immutable Source Snapshot and
`artifact(kind = 'markdown')`, exactly like any other acquisition Adapter.
The Markdown boundary from ADR 0012 remains in force: manual acquisition never
automatically creates Blocks, Passages, Tasks, statements, or KCs.

Postgres stores asset identity, order, hashes, metadata, lineage, and
`storage_key`, but not binary bodies. The local backend keeps files under
a dedicated application-managed directory. Railway uses Railway Buckets or
another S3-compatible object store. Canonical Markdown remains in Postgres and
the meaning of a Snapshot or Artifact does not change when the storage backend
changes.

## Consequences

- A failed URL and a successful manual capture remain two honest attempts for
  one Source.
- Humans can inspect the exact PDF or ordered images behind generated Markdown.
- Image prose is explicitly model output; it never replaces the original
  visual evidence.
- Scanned PDF pages use their derived renders as primary evidence (ADR 0016).
- The current 30 MB / 50-image limits bound storage growth and model cost.
- Railway deployment needs Poppler in the worker image and S3-compatible
  object storage configured from the start.
- Article images are independently observable enrichment: one image failure
  raises attention without turning successful textual Markdown into failure.
- Manual screenshots remain primary evidence and collectively form their
  acquisition's Markdown rather than acting as optional enrichment.
- KC generation remains an independent, explicit action.
