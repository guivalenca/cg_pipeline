# 0011: V1 identity by mutual clear surmise over perfect cliques

Date: 2026-08-02
Status: accepted

## Context

The directed precedence graph design
(`directed-precedence-graph.md`, kept in the research archive at
`~/Desktop/concept-universe-research/`) replaced similarity-threshold
grouping after the blind review of r0130 showed statement-wording proximity
cannot define knowledge identity. Its identity core — two units are the same
knowledge exactly when mastery of each implies mastery of the other — was
validated by the kc-judge benches. But the machinery around it (k-plex
tolerance, tension objects, node-health flags, a diagnostic exam menu,
pendência states, weighted tiebreaks) grew past what the founder can own,
audit, and afford for a v1: it defends against wrong merges with apparatus,
when the cheap defense is to not merge. On 2026-08-01 the founder ordered a
simplification pivot: v1 must be fully understandable by him, ship inside
the deadline, and hold near a $40/module model-cost ceiling.

## Decision

**Identity primitive.** One judge call per candidate pair asks the mastery
implication in both directions ("does mastering A imply mastering B?", and
the reverse), each answered on the 4-level scale (clear_yes / likely /
unlikely / clear_no). Prompt `kc-judge/v002-surmise-pair` + `tool-v002`.
Benched 2026-08-02 against the two-call v001 run: 87.5% per-direction binary
agreement, identical clear-duplicate core, 2.7x cheaper ($0.40/source,
measured on 100 pairs).

**Merge rule, the whole of it.** Two unitary KCs are the same KC only when
both directions are clear_yes, and a group commits only when every pair
inside it is such a double — a perfect clique, at any size. Anything weaker
(a likely, a failed triangle) stays unmerged. The governing asymmetry: an
uncommitted duplicate costs a redundant dashboard entry; a wrong merge
corrupts measurement. When in doubt, don't merge.

**Candidates.** Per new statement: semantic neighbors above cosine 0.70,
top 6; plus lexical (BM25) top 5. Union, deduplicated pairwise. The axis
filter applies after the cap (an axis-incompatible neighbor spends a slot
and is dropped — accepted trade), so only same-modality, same-knowledge
pairs are judged. No per-node minimum, no legacy/dense generators.

**Axes.** Majority-of-3 voting is retired; each axis is one call. Axes no
longer guard identity — the judge tests transfer directly, which is what
the axes proxied. Their v1 jobs: filtering judge candidates and carrying
the instructional signal downstream (segment/tutor consumption). Wrong-axis
noise therefore costs a missed merge candidate or a teaching-style hint,
never corrupted identity, and axes remain recomputable interpretations.

**Judge default: deepseek-v4-pro, thinking high.** Founder decision
2026-08-02, chosen over flash (5x cheaper, zero false merges in the bench,
but only 3 of 8 mutual flags surfaced). Reasoning: flags are information
about the corpus; a judge that surfaces more of them is worth the cost.

**Ledger.** Every verdict — both directions, full 4-level grade, one-way
arrows included — is a stamped permanent fact, judged once per pair and
never re-asked. V1 consumes only the clear mutual doubles. Runner defaults:
16 workers; OpenRouter routing sorted by throughput with low-bit quantized
providers excluded, wired into the request defaults.

## Deferred, not deleted

The graph machinery of the research memo — k-plex tolerance and tension,
node-health flags, the diagnostic exam menu, the whole-set veto gate,
pendência objects, weighted disagreement tiebreaks, floor recalibration,
and all consumption of single arrows (the precedence map) — is deferred.
The edge ledger this ADR mandates is exactly what makes every one of those
buildable later without re-spending a judge call.

## Consequences

- ADR 0007 (canonical anchor + whole-set gate) is superseded: membership by
  mutual surmise cliques replaces the anchor; the multi-match quarantine
  becomes simple non-merging; the whole-set gate is dropped in v1.
- ADR 0010 stages 4–5 are redefined: grouping is candidate generation +
  pair judging + clique snapshots over the edge ledger; naming will attach
  to composite KC snapshots.
- ADR 0008 is reinforced: unitary KCs are the permanent id-bearing layer;
  composite KC snapshots are derived and re-mintable.
- Ingesting a source is incremental by construction: only the new
  statements' candidate pairs are judged; nothing global re-runs.
- Bench record: `reports/kc-judge-bench-v002.md`; stage defaults in
  `docs/pipeline-defaults.md`.
