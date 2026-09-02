# 0001: Facts versus interpretations in the source ledger

Date: 2026-07-23 (records the standing founding principle)
Status: accepted

## Context

The system depends on LLM judgments that will sometimes be wrong, and on
models, prompts, and understanding that will keep improving. Being wrong must
never corrupt accumulated knowledge.

## Decision

Every stored item is either a fact or an interpretation. Facts—what an
institution supplied, what a Source contained, and what an operator curated—
are append-only and never require a model to be right. Cleanup and visual
readings are versioned, stamped interpretations over those facts.

Canonical Source Markdown is reproducible from immutable evidence and recorded
decisions. Every automated decision is stamped with its model, prompt or tool
version, inputs, and usage. Human curation acts are facts.

## Consequences

- A wrong interpretation costs a recomputation, never corrupted evidence.
- Fact record schemas must be settled before building; interpretation
  mechanics (prompts, thresholds, aggregation) may be settled by iteration.
- New snapshots, artifacts, and readings are added beside old ones, never
  substituted destructively.
