# 0006: Syllabus versioning and unavailable sources

Date: 2026-07-23
Status: accepted

## Context

Sources referenced by a syllabus sometimes cannot be acquired (dead links,
placeholder links, blocked books). cg_pipeline handled this with metadata-only
and top-down extraction paths. In the universe, grains are fact-layer
records that require passage provenance, so a source with no snapshot cannot
honestly yield grains.

## Decision

The received syllabus is the first version. An acquisition failure is recorded
as a fact on the acquisition side (the source and snapshot records), signaled
to the founder, and an alternate fetch is attempted. The fix (a corrected
link, a replacement source, a manual exclusion, or any metadata correction)
authors the next Syllabus version as a curation act. The version with the dead
link remains in the ledger permanently.

There is no metadata-only and no top-down extraction path. The teacher signal
is preserved instead by the Syllabus itself: a syllabus reference with no
ingested source surfaces in the dashboard as a visible coverage gap, never as
a synthetic extraction.

## Consequences

- The honest record of what the institution assigned survives every fix.
- Coverage gaps are curation workload, visible and actionable, not silently
  papered over by weaker extraction.
- cg_pipeline's metadata-only machinery is not carried over.
