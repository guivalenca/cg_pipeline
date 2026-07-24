# 0001: Facts versus interpretations, two append-only ledgers

Date: 2026-07-23 (records the standing founding principle)
Status: accepted

## Context

The system depends on LLM judgments that will sometimes be wrong, and on
models, prompts, and understanding that will keep improving. Being wrong must
never corrupt accumulated knowledge.

## Decision

Every stored item is either a fact or an interpretation. Facts (what a source
said, what a student demonstrated, what a human curated) live in append-only
ledgers, are never edited, and never require an AI to be right. Interpretations
(groupings, digests, plans, mastery) are computed, versioned, and recomputable
on top of facts. There are two ledgers: the content ledger and the student
ledger; Knowledge Components are the joint where they meet.

Text is the only canonical data; vectors and verdicts are derived and
replayable. Every automated decision is stamped with the model and prompt
version that produced it. Human curation acts are facts.

## Consequences

- A wrong interpretation costs a recomputation, never a corrupted universe.
- Fact record schemas must be settled before building; interpretation
  mechanics (prompts, thresholds, aggregation) may be settled by iteration.
- New snapshots, artifacts, and readings are added beside old ones, never
  substituted destructively.
