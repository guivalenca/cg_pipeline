# Concept Graph Section 1 Implementation

This is the concrete implementation reference for Phases 1-4 of the Concept
Graph pipeline. It builds the reliable source-corpus half of the system before
deep graph synthesis starts.

Read [Concept Graph Project](concept-graph.md) and
[Autonomous Concept Graph Pipeline Plan](concept-graph-pipeline-plan.md) first.

## Goal

Section 1 takes a selected Course, Module, and Subject from a faculty XLSX and
produces extraction-grade source bundles:

```text
workbook_ir.json
acquisition_result.json per Self-study
source_manifest.json per Self-study
cleaned_source.md per Self-study
cleaning_report.json per Self-study
annotation.json per Self-study
resource_quality_report.md
```

Graph synthesis must not start until Section 1 passes source completeness,
quality, scope, provenance, and redaction gates.

## Implementation Checklist

1. Add `cg_pipeline/` skeleton and CLI entrypoint.
2. Add run manifest and local artifact store.
3. Add workbook parser and `workbook_ir.json` schema.
4. Add AI Assigned Scope normalization review inside the local dashboard.
5. Add fixture workbook tests.
6. Add deterministic acquisition interfaces and direct fetchers for normal
   articles/PDFs/video metadata/captions where permitted.
7. Add `acquisition_job.json`, `acquisition_result.json`, `source_manifest.json`,
   and `quality_report.json` schemas.
8. Add remote OpenClaw acquisition client stub using file contracts.
9. Add a fake OpenClaw-backed acquisition fixture to test resume/download.
10. Add AI Resource Cleaning work order, prompt, schema, and quality gate.
11. Add AI Resource Annotation work order, prompt, schema, and quality gate.
12. Add source completeness validation that blocks later graph synthesis.
13. Add a local dashboard command that can run the current pipeline, show the
    step timeline, present the source inventory and validation findings, and
    save human Assigned Scope corrections.
14. Add replay mode that runs from cached source bundles without network,
    browser, or OpenClaw.

## Phase 1: XLSX Ingestion

Phase 1 is deterministic except for Assigned Scope normalization, which may use
an LLM because workbook descriptions can contain complex page/exercise
instructions.

Inputs:

- Faculty XLSX such as `si_mod6.xlsx`.
- Selected Course, Module, and Subject.

Behavior:

- Read sheets such as `All`, `COM`, `MTF`, `NEG`, `UEX`, `LID`, and
  `Orientation`.
- For a selected Subject, read the matching Axis sheet such as `COM` as the
  authoritative ingestion surface when it exists. `All` may be used for fallback
  or validation, but must not cause unselected Subjects to be ingested.
- Normalize rows into Lessons and Self-studies.
- In the selected Axis sheet, `Type` must be either `Class` or `Self-study`.
  Unknown types are blocking workbook validation errors.
- Resolve Self-study membership only from `Parent class` plus `Class date`.
  Row adjacency is not authoritative for attaching Self-studies to Lessons.
  A Self-study whose parent key does not match a Lesson in the selected Axis
  sheet is a blocking workbook validation error with enough detail to correct
  the spreadsheet.
- Duplicate Lesson keys (`Title` plus `Date`) in the selected Axis sheet are
  blocking workbook validation errors that include the duplicate key and row
  numbers.
- For a Self-study, `Date` must equal `Class date`. Any mismatch is a blocking
  workbook validation error to correct before acquisition.
- Lesson rows must have blank `Parent class` and `Class date`; populated parent
  fields on a Lesson row are a blocking workbook validation error.
- Preserve date, week, sort, type, title, parent Lesson, professor, axis,
  related subjects, description, URL, resource code, required flag, grade
  weight, and assigned scope.
- Treat `Related subjects` as important lesson-framing input. Store it as a
  semicolon-split, trimmed list while preserving each item's wording exactly; do
  not store a duplicate raw string in `workbook_ir.json`.
- Preserve the `Required` field for traceability, but ignore it for pipeline
  behavior. `Required = no` Self-studies are still parsed, acquired, cleaned,
  annotated, explored deeply, and counted in source completeness gates.
- Normalize Assigned Scope with an LLM when the workbook description is too
  complex for deterministic extraction. The model receives the full Self-study
  description as data and returns only the extraction range, such as page ranges,
  exercises, chapters, sections, or timestamps.
- Require Assigned Scope review only for scope-sensitive sources: Sophia /
  Minha Biblioteca or other book-library URLs, PDFs/books where the workbook
  implies a page/chapter/section subset, and videos only when the description
  assigns timestamps or a partial segment. Normal articles and full-source videos
  use the linked source as their scope unless the workbook explicitly narrows
  coverage.
- Use the local dashboard as the single operator-facing Phase 1 workspace. It
  includes the full source inventory, workbook validation findings, run timeline,
  event log, and an Assigned Scope attention queue. For review items, before is
  the full workbook description and after is only the proposed extraction range.
  For book-library sources, render the after value as acquisition-oriented page
  ranges or page lists, such as `pages 25, 43, 51, 54`; include exercise labels
  only when needed to disambiguate the assigned pages. Graph acquisition must
  not continue while the dashboard still shows `needs_human_scope` items or
  blocking workbook validation findings.
- Produce stable Lesson IDs and Self-study IDs.
- Write `workbook_ir.json` as the persisted workbook state. The dashboard derives
  its inventory from that JSON and lists every selected Self-study, including
  Lesson, title, source kind, URL, resource code, full-source versus
  assigned-scope coverage, scope-review requirement, and workbook validation
  findings.
- `python3 -m cg_pipeline dashboard` starts a local-only control center. It can
  invoke the same workbook pipeline, poll structured run state, expose the step
  timeline, expose validation failures as first-class dashboard state, and save
  human Assigned Scope corrections for the next rerun.
- Do not support local/manual source attachment paths in v1. Workbook problems
  block early with clear correction instructions instead of being patched around
  during acquisition.
- Every selected Self-study must have a URL.
- For book-library sources, `Resource code` is mandatory even when URL is
  present. Generic library terminal URLs are not sufficient source identity.
- Use stable internal artifact IDs. Lesson IDs have the form
  `{course}.{module}.{subject}.{yyyy-mm-dd}.{lesson_slug}`. Self-study IDs have
  the form `{lesson_id}.self_study.{sort_padded}`. These IDs link pipeline
  artifacts, validation findings, replay state, and provenance; they are not
  student-facing labels.

Completion criteria:

- Every selected Self-study row appears exactly once in `workbook_ir.json`.
- Missing URL, required source identity, or required Assigned Scope issues are
  blocking workbook validation errors when they affect any selected Self-study.
- The operator has reviewed the dashboard before Phase 2 starts for any source
  whose coverage depends on a normalized Assigned Scope.
- Replay tests can parse fixture workbooks without network, browser, or model
  calls.

## Phase 2: Resource Acquisition

Phase 2 starts deterministic and escalates only when needed.

Deterministic local fetchers should handle:

- Normal web articles.
- Direct PDFs.
- Documentation pages.
- Video metadata and allowed caption/transcript retrieval.
- Existing cached source bundles by source hash.

Remote OpenClaw acquisition should handle:

- Sophia / Minha Biblioteca.
- Authenticated browser sessions.
- JavaScript-rendered pages when deterministic extraction fails.
- Browser-only PDFs or canvas viewers.
- Screenshot/page-image capture.
- Manual login, MFA, CAPTCHA, or blocker resume.

OpenClaw is called through a bounded acquisition contract, not asked to make
Concept decisions.

Minimum `acquisition_job.json`:

```json
{
  "run_id": "2026-05-08-si-mod6-computacao",
  "self_study_id": "si.mod6.computacao.2026-05-13.003",
  "lesson_id": "si.mod6.computacao.2026-05-13",
  "source_type_hint": "book_library",
  "title": "Self-study title from XLSX",
  "url": "https://philos.sophia.com.br/terminal/9418",
  "resource_code": "9780000000000",
  "coverage": {
    "mode": "assigned-scope",
    "scope": {
      "kind": "pages",
      "value": "123-135"
    }
  },
  "scope_provenance": {
    "source": "human_input",
    "reason": "model_could_not_determine_scope"
  },
  "required": "yes",
  "related_subjects": ["COM"]
}
```

Minimum `acquisition_result.json`:

```json
{
  "self_study_id": "si.mod6.computacao.2026-05-13.003",
  "status": "fetched_with_warnings",
  "resource_kind": "book_library",
  "final_url": "https://philos.sophia.com.br/terminal/9418",
  "source_identity": {
    "title": "Resolved source title",
    "authors": ["..."],
    "isbn_or_resource_code": "9780000000000"
  },
  "artifacts": {
    "source_manifest": "sources/.../source_manifest.json",
    "raw_bundle": "sources/.../raw/",
    "quality_report": "sources/.../quality_report.json"
  },
  "blocking_errors": [],
  "warnings": ["ocr_low_confidence_page_129"],
  "credential_fields_redacted": true
}
```

Allowed statuses:

- `fetched`
- `fetched_with_warnings`
- `blocked_access`
- `blocked_quality`
- `needs_manual`
- `failed_retriable`
- `failed_terminal`

Any blocking status prevents graph synthesis unless the operator records an
explicit exclusion with rationale in the run manifest.

Completion criteria:

- Every Self-study has one acquisition job and one acquisition result.
- Browser-required sources produce provenance bundles with source identity,
  access mode, screenshots/page evidence, hashes, and redaction confirmation.
- Book-library extraction proves it used only Assigned Scope as coverage.

## Phase 3: AI Resource Cleaning

Resource Cleaning is AI-assisted because high-quality cleanup requires judgment.
It should still be bounded by schemas and quality gates.

The Resource Cleaning Agent receives source text/artifacts as data, not
instructions. It must ignore prompt-injection text found inside sources.

Behavior by source type:

- Articles: remove menus, cookie banners, ads, repeated headers/footers,
  unrelated recommendations, and scraping artifacts.
- Videos: clean caption or STT artifacts while preserving timestamps when useful.
- Books: preserve page markers, exercise numbers, examples, headings, code
  blocks, assigned page boundaries, and important formatting.
- Documentation: preserve headings, warnings, examples, code blocks, API notes,
  and conceptual explanations.

Default rule: preserve and structure, do not summarize aggressively.

The cleaner writes:

- `cleaned_source.md`
- `cleaning_report.json`
- before/after quality stats
- warnings or reacquisition requests when the source bundle is incomplete

If the cleaner cannot produce extraction-grade text because the raw capture is
bad, LangGraph routes back to Phase 2 acquisition. If the capture is good but
cleaning is weak, LangGraph retries cleaning with a critic prompt before
blocking.

Completion criteria:

- Cleaned sources are extraction-grade.
- Assigned Scope boundaries are preserved.
- Credential-looking strings, cookies, auth headers, and browser profile paths
  are absent.
- Source text is not compressed into summaries before extraction.

## Phase 4: AI Resource Annotation

Resource Annotation adds interpretation around the cleaned source without
replacing it.

The Resource Annotation Agent writes:

- resource type
- assigned scope
- short source summary
- source outline
- extraction boundaries
- quality warnings
- source issues
- whether captions, STT, OCR, or browser capture were used
- which parts are coverage vs background/examples/marketing/navigation

For a book excerpt, annotation must state exactly which pages, exercises, or
sections are assigned.

For a video, annotation must state whether captions or STT were used and whether
the transcript passed quality gates.

For a broad article, annotation must distinguish teaching content from
background, examples, marketing, or unrelated navigation.

Completion criteria:

- Every cleaned source has an `annotation.json`.
- Concept Extractors receive cleaned full text plus annotation.
- Annotation never expands coverage beyond the assigned source.
- Graph synthesis is blocked until source completeness and provenance integrity
  pass.

## Source Quality Gates

Section 1 owns these hard gates before Concept extraction:

- Every XLSX Self-study row has an acquisition result.
- Access blockers are reported, not bypassed.
- Source identity matches the XLSX row.
- Book-library coverage is restricted to Assigned Scope.
- Text/OCR/transcript quality is extraction-grade.
- Browser acquisition proves it saw content, not only an app shell.
- Provenance bundles include raw artifact hashes, quality reports, and redaction
  confirmation.
- Source prompt injection is treated as inert source data.

## Section 1 Done Means

- The selected Subject has a complete source corpus.
- Missing, blocked, low-quality, or over-scoped assigned Self-studies block the
  run unless explicitly excluded with operator rationale.
- Replay mode can rerun cleaning/annotation from cached bundles without network,
  browser, or OpenClaw.
- Later graph synthesis receives only cleaned source text plus annotation, never
  browser sessions or open web access by default.
