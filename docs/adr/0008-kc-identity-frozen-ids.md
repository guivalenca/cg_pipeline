# 0008: KC ids are minted once and frozen

Date: 2026-07-23
Status: accepted

## Context

KC ids are the durable handles everything anchors to: future student evidence,
exports to the Companion, curation records. A content-hash id (hashing the
member grains) was considered and rejected: it would change on every
addition, breaking every external reference exactly when the KC is doing its
job of growing.

## Decision

A KC id is minted once when the KC is born, as a readable slug plus a short
suffix derived from the initial canonical phrasing, and never changes
afterwards, regardless of how membership or the canonical phrasing evolve.

The audit trail lives in records, not in id churn: every membership change
appends to a permanent membership log (grain, date, verdict, and the model
and prompt or the human curator behind it). A merge retires one id with a
permanent redirect to the survivor. A split keeps the id on the descendant
retaining the most grains and mints new ids, with pointers, for the rest.

Merges are expected in normal operation, not only on full recreation: blocking
is recall-oriented but imperfect, so the same skill occasionally enters twice
under different vocabulary and lives as two KCs until a bridging grain
matches both canonicals and the quarantine resolves as a merge.

## Consequences

- External systems may reference KC ids safely across growth, merges, and
  splits.
- Any membership state can be reconstructed, and any merge undone, from the
  log.
- Id reconciliation for full reruns (rebuilding the interpretation layer with
  a new model or prompt while preserving ids) is a separate deferred design.
