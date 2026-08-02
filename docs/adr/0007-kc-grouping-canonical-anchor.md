# 0007: KC grouping by canonical anchor with a whole-set gate

Date: 2026-07-23
Status: superseded by 0011 (2026-08-02) — membership is now mutual clear
surmise over perfect cliques; the multi-match quarantine became simple
non-merging, and the whole-set gate was dropped for v1

## Context

Grouping grains into KCs is incremental entity resolution from pairwise
LLM verdicts. Pairwise verdicts chain: naive transitive merging is the
worst-precision clustering policy in standard benchmarks (0.101 versus ~0.6
for chain-guarding policies at equal cost), and one vague grain can weld
two distinct skills into one KC. Survey and citations:
`docs/research/entity-resolution-grouping.md`.

## Decision

Membership follows the canonical-anchor policy. A new grain is judged only
against candidate KCs' canonical phrasings, never against individual member
grains, so match chains are structurally impossible. Outcomes:

- Match exactly one KC: the grain joins it, after a whole-set gate in
  which a judge reads the entire resulting KC and confirms it is one skill.
- Match none: a new KC is created.
- Match multiple: the grain is quarantined for human review. Identity is
  transitive, so a real double match means the grain is too coarse and
  must split into two grains, or the two KCs are duplicates and must
  merge, or a verdict is wrong. The human decides which.

A grain belongs to exactly one KC. Conflicts require a human decision;
recurring conflicts are a signal to improve the system, not to automate the
disputes away. Occasional bad joins are accepted: they cost optimization, not
corruption, and correction stays cheap because membership is a log over
permanent grains.

A triggered local repair pass (re-solving one messy neighborhood with all
stored verdicts at once) is deferred: guivalenca/companion#72.

## Consequences

- Vague grains become visible curation workload instead of silent welds.
- The canonical phrasing serves both blocking and membership, one mechanism
  for both jobs.
- All verdicts are stored as stamped facts, which is the only prerequisite the
  deferred repair pass needs.
