# Concept Graph Implementation Open Issues

This document tracks unresolved decisions and build order. Read
[Concept Graph Project](concept-graph.md),
[Autonomous Concept Graph Pipeline Plan](concept-graph-pipeline-plan.md), and
[Concept Graph Section 1 Implementation](concept-graph-section-1-implementation.md)
first.

## Settled Decisions

- V1 generation is local-first inside this repository, likely under
  `cg_pipeline/`.
- `cg_pipeline/` is manually invoked tooling, not Companion runtime code.
- The pipeline may later be extracted into its own repository, but that is not
  necessary for V1.
- LangGraph can coordinate the full local run, including deterministic nodes,
  AI cleaning/annotation nodes, synthesis nodes, critic/repair loops, and remote
  OpenClaw acquisition nodes.
- Phase 1 XLSX ingestion is pure code.
- Phase 2 resource acquisition is deterministic-first, with remote OpenClaw
  fallback for browser/auth/manual cases.
- Phase 3 Resource Cleaning is AI-assisted because high-quality cleanup needs
  judgment.
- Phase 4 Resource Annotation is AI-assisted and schema-bound.
- OpenClaw should not make Concept decisions. It returns acquisition artifacts.
- Companion consumes only promoted graph artifacts at
  `reference/courses/{course}/{module}/{subject}/graph.json`.
- Promoted graphs require validation artifacts and human review before becoming
  runtime reference data.

## Open Issue 1: Local Directory Shape

Recommended starting shape:

```text
cg_pipeline/
  schemas/
  pipeline/
    __init__.py
    cli.py
    run_store.py
    workbook.py
    acquisition/
    cleaning/
    annotation/
    orchestration/
    validation/
  prompts/
  fixtures/
  tests/
```

Resolved / open questions:

- Resolved: run artifacts default to named directories under
  `cg_pipeline/runs/{run_id}/`, ignored by git.
- Should `cg_pipeline/` have its own dependency group/package metadata, or share
  the repo environment initially?
- Should graph schemas live only under `cg_pipeline/schemas/`, or should the
  final runtime graph schema be mirrored under Companion tests from day one?

Current recommendation:

- Use `cg_pipeline/runs/{run_id}/` for local development run artifacts.
- Keep pipeline dependencies isolated in a dependency group if the existing
  project toolchain supports it.
- Mirror only the final runtime graph schema when Companion runtime adapter work
  begins.

## Open Issue 2: Remote OpenClaw Access

OpenClaw currently runs on the VPS. The gateway was previously documented as
loopback-only on `127.0.0.1:18789`.

Viable access modes:

- SSH command plus file sync.
- SSH tunnel to the loopback gateway.
- Tailscale/private-network exposure with authentication.
- A narrow custom acquisition endpoint in front of OpenClaw.

Current recommendation:

- Start with file contracts over SSH/SFTP/rsync.
- Do not publicly expose the gateway without auth and network controls.
- Treat browser profiles and acquisition bundles as sensitive.

Needed:

- Define `OpenClawAcquisitionClient.acquire(job)`.
- Decide upload/download paths on the VPS.
- Add timeout, retry, cancellation, and resume behavior.
- Add redaction validation before local graph synthesis can consume returned
  bundles.

## Open Issue 3: Section 1 Work-Order Schemas

Needed schemas:

- `workbook_ir.json`
- `run_manifest.json`
- `acquisition_job.json`
- `acquisition_result.json`
- `source_manifest.json`
- `quality_report.json`
- `cleaning_report.json`
- `annotation.json`

Each schema should define:

- artifact paths
- source hashes
- allowed statuses
- blocking errors and warnings
- model/tool provenance where relevant
- redaction confirmation
- retryability

## Open Issue 4: Resource Cleaning Design

Resource Cleaning should be AI-assisted, but still testable.

Needed:

- Prompt contract for each source class: article, video, book/OCR, PDF,
  documentation.
- Output schema for `cleaned_source.md` plus `cleaning_report.json`.
- Quality gates for boilerplate removal, preservation of page markers,
  timestamp preservation, broken-token ratio, duplicate text ratio, code/table
  preservation, and assigned-scope boundaries.
- Reclean path when cleaning is weak.
- Reacquisition path when cleaning discovers source capture is incomplete.

Important rule:

The cleaner may structure and remove noise. It must not summarize aggressively
before Concept extraction.

## Open Issue 5: Library Acquisition Spike

We still need a real or mock Sophia / Minha Biblioteca spike.

Candidates:

- OpenClaw native browser with a dedicated `openclaw` profile and manual login.
- OpenClaw spawning Codex through ACP for one bounded acquisition job if Codex
  browser control is more reliable.
- Human-assisted browser capture that resumes the same job after `needs_manual`.

Acceptance criteria:

- Proves source identity by resource code plus visible metadata.
- Captures only Assigned Scope as coverage.
- Stores screenshots/page evidence.
- Produces extraction-grade text or `blocked_quality`.
- Redacts credentials, cookies, bearer tokens, auth headers, and browser profile
  paths.
- Fails clearly as `needs_manual`, `blocked_access`, or `blocked_quality`.

## Open Issue 6: Final V1 Runtime Graph Schema

The final `graph.json` schema must cover:

- Subject metadata.
- Lessons replacing old `day_presets`.
- Compatibility with existing `day_presets` readers.
- Self-studies linked to Lessons.
- Lesson Segments.
- Instructional Role.
- Concepts.
- Coverage Criteria as name + description.
- Common Misconceptions.
- Concept Dependencies schema compatibility, with v0 dependency lists empty.
- Lightweight Concept Provenance.
- Dependency short reason and source label reserved for future dependency work.
- Review confidence as `high`, `medium`, or `low`.

## Open Issue 7: Companion Runtime Bridge

Minimal Companion work after the graph schema stabilizes:

- Fix tutoring profile slicing so namespaced Concept Map entries are read
  correctly.
- Add compatibility for `lessons` while still accepting old `day_presets`.
- Enrich `summary_generator.py` with Concept descriptions, Coverage Criteria,
  Common Misconceptions, and Lesson Segment structure.
- Defer runtime prompt language for `blocking`, `hard`, and `soft` dependencies
  until dependency inference is reintroduced for exam-study or adaptive
  remediation.
- Keep runtime prompt text-first rather than raw JSON.

Do not block the pipeline on full Session Focus / Evidence Ledger runtime work.

## Section 1 Build Order

Build only Phases 1-4 first. The concrete checklist lives in
[Concept Graph Section 1 Implementation](concept-graph-section-1-implementation.md).

## Later Build Order

After Section 1:

1. Add primary Self-study extraction.
2. Add optional narrow-lens extraction.
3. Add top-down Lesson expectation.
4. Add reconciliation.
5. Add concept finalization.
6. Add dependency deferral with an explicit empty dependency artifact. Done in
   the creation prototype as `dependency_inference.json`.
7. Add lesson segmentation and ordering. Done in the creation prototype as
   per-Lesson `lesson_segments.json` artifacts with v0 roles fixed to `teach`.
8. Add deterministic graph validator.
9. Add critic fan-out.
10. Add conciliatory review and repair.
11. Add final graph assembly and release notes.
12. Add Companion runtime adapter updates.

## First COM PoC Slice

Likely input:

```text
/Users/guilhermevalenca/Desktop/si_mod6.xlsx
```

Likely scope:

- Course: `si`
- Module: `mod6`
- Subject: `computacao` / `COM`

Recommended first slice:

- One or two COM Lessons end-to-end through Section 1.
- Include one normal web article.
- Include one video Self-study.
- Include one Sophia / Minha Biblioteca source once remote OpenClaw acquisition
  is wired.
