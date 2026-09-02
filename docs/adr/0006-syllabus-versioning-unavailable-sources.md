# 0006: Syllabus versioning and unavailable sources

Date: 2026-07-23
Status: accepted

## Context

Sources referenced by a syllabus sometimes cannot be acquired because of dead
links, placeholders, authentication, or provider restrictions. The failure
must stay visible without fabricating a publication.

## Decision

The received syllabus is the first version. An acquisition failure is recorded
as a fact on the acquisition side (the source and snapshot records), signaled
to the founder, and an alternate fetch is attempted. The fix (a corrected
link, a replacement source, a manual exclusion, or any metadata correction)
authors the next Syllabus version as a curation act. The version with the dead
link remains in the ledger permanently.

There is no metadata-only publication path. The institutional signal remains
in the Syllabus itself: a reference with no Source Publication appears as a
visible coverage gap, never as synthetic content.

## Consequences

- The honest record of what the institution assigned survives every fix.
- Coverage gaps are curation workload, visible and actionable, not silently
  papered over by weaker extraction.
- No unavailable Source can appear published.
