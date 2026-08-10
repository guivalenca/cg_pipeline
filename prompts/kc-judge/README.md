# kc-judge — the directional mastery judge

The identity judge of ADR 0011 (its graph ancestry is in
`directed-precedence-graph.md`, research archive at
`~/Desktop/concept-universe-research/`): for each candidate pair of
unitary KCs, one call judges both directions of "does mastery of A imply
mastery of B?" on the 4-level scale adopted 2026-08-01 (clear_yes /
likely / unlikely / clear_no). Two KCs merge only on clear_yes in BOTH
directions; groups form only as perfect cliques of such pairs (ADR 0011).
One-way arrows are stored as edges and consumed by nothing in v1.

Arrow convention (fixed system-wide): A→B means "mastery of A implies
mastery of B" — the arrow points from advanced to basic.

The judge never sees which generator proposed the pair or any similarity
scores.

## Prompts

| version | idea | result |
| - | - | - |
| v003-surmise-pair (current) | Keeps the paired surmise judgment and asks the model to test a concrete counterexample before each directional verdict. | Promoted 2026-08-06. On 2026-08-07, a blind 60-pair comparison made deepseek-v4-flash-0731 at reasoning low the judge default: 59/60 merge agreement with a valid Pro-high baseline at about one sixth of its cost. Canonicalization remains Pro-high. |

Retired prompt generations, raw model responses, evaluations, notebooks,
and their one-off runners live outside the product repository at
`~/Desktop/concept-universe-research/judge-research-2026-08/`.

## Tools

| file | idea |
| - | - |
| tool-v002.json (current) | record_verdicts with one 4-level verdict per direction (verdict_a_to_b / verdict_b_to_a) plus a reason each. Level semantics live in the tool; the two clear levels are anchored to what the reason can demonstrate or name, the middle levels defined as genuine uncertainty ("not caution") to resist middle-dumping. |

## Candidates (per ADR 0011)

Semantic neighbors at cosine floor 0.70 capped at 6, plus lexical BM25
top-5; the axis-compatibility filter applies AFTER the cap (an
axis-incompatible neighbor spends a slot and is then dropped — founder
accepted the trade). Legacy and dense generators are off. Runner:
`src/universe/kc_judge.py` (production ledger runner). Historical scratch
bench runners are kept with the research archive.
