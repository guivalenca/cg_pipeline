# 0003: Phase 1 is the universe, phase 2 is the student ledger

Date: 2026-07-23
Status: accepted

## Context

The full vision spans content ingestion through student mastery. The two
ledgers meet only at KC identity: everything student-side consumes KCs by
reference, and nothing content-side reads the student ledger. The hard
unsolved design questions concentrate on the content side.

## Decision

Phase 1 builds the universe itself: content ledger, extraction, Knowledge
Components, Concepts, and lesson plans. Phase 2 builds the student ledger and
computed mastery. During phase 1 the Companion's current evaluation pipeline
and Concept Map continue operating unchanged, and the student data they
accumulate is left as-is; it will be reprocessed when phase 2 lands.

KC id durability is the contract phase 2 depends on and is guaranteed from
phase 1 (see ADR 0008). Expected answers on grains, teacher importance
ranking, evaluation flow, and the "seen" trigger move wholesale to phase 2.

## Consequences

- Phase-1 student data stays in the old mutable Concept Map form; at best it
  backfills coarsely later. Accepted price, decided consciously.
- Phase 1 effort concentrates on the keystone open questions (KC membership,
  sizing, aggregation) instead of spreading across the whole vision.
- Eventually this becomes one integrated system; that integration is an
  afterthought by design, not a phase-1 constraint.
