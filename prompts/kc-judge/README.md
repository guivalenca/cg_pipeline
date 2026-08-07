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
| v002-surmise-pair (retired) | The surmise framing carried over from v001, restructured to judge both directions in one call: the pair is presented once, the two directional questions answered in a single record_verdicts call. Halves the calls per pair and lets the judge see the pair whole while the tool still forces a separate verdict per direction. | **Benched 2026-08-02 over the 100-pair reference corpus (report: `reports/kc-judge-bench-v002.md`); adopted as default with deepseek-v4-pro, decided by founder over flash.** Pro: $0.40/source, 6 merge-grade doubles found; flash: $0.08, 3 doubles, a strict subset of pro's. One-call vs two-call binary agreement 88%. Superseded by v003. |
| v001-transfer / v001-surmise (A/B, retired 2026-08-02) | Same structure, same tool; the variable was how much theory the model is given — transfer the lean control, surmise with the literature framing (knowledge component and surmise relation named and defined). One direction per call, two calls per pair. | Benched 2026-08-01 over 279 pairs each; surmise promoted, transfer retired: the lean prompt was too literal, treating task-wording accidents as knowledge demands and vetoing real merges. Surmise sat closer to Opus (90.2% vs 86.2%) with no hedging pathology. Superseded by v002-surmise-pair; the v001 prompt files and raw runs were removed in the 2026-08-02 repo cleanup. Known weakness (unchanged in v002): contested "likely" yeses tend to be wrong — remedy open; the level-gated escalation idea was dropped by founder decision 2026-08-01 (analysis: `opus-vs-deepseek-r0130.md` in the research archive). |

## Tools

| file | idea |
| - | - |
| tool-v002.json (current) | record_verdicts with one 4-level verdict per direction (verdict_a_to_b / verdict_b_to_a) plus a reason each. Level semantics live in the tool; the two clear levels are anchored to what the reason can demonstrate or name, the middle levels defined as genuine uncertainty ("not caution") to resist middle-dumping. |

## Candidates (per ADR 0011)

Semantic neighbors at cosine floor 0.70 capped at 6, plus lexical BM25
top-5; the axis-compatibility filter applies AFTER the cap (an
axis-incompatible neighbor spends a slot and is then dropped — founder
accepted the trade). Legacy and dense generators are off. Runner:
`src/universe/kc_judge_bench.py` (scratch bench over a JSON corpus, no
database; pair mode auto-detected from the tool schema).
