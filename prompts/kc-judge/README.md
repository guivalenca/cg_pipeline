# kc-judge — the directional mastery judge

The judging stage of the precedence graph
(docs/research/directed-precedence-graph.md): for each candidate pair of
unitary KCs, two blind calls — one per direction — each answering "does
mastery of A imply mastery of B?" on the 4-level scale adopted 2026-08-01
(clear_yes / likely / unlikely / clear_no; structure collapses to binary
underneath, the level stays on the edge as evidence).

Arrow convention (fixed system-wide): A→B means "mastery of A implies
mastery of B" — the arrow points from advanced to basic. The runner
renders the pair so the judged direction is always A→B; the reverse call
swaps which item appears as A.

The judge never sees which generator proposed the pair, similarity
scores, or the other direction's verdict.

## Prompts

| version | idea | result |
| - | - | - |
| v001-transfer / v001-surmise (A/B) | Same structure, same tool; the variable is how much theory the model is given. **transfer** is the lean variant: the operative question and rule only — mastery defined inline as answering fair questions of the task's kind, the covers-only-when-B's-demand-lives-inside-A rule, nothing else. **surmise** carries the literature framing the memo's open question 5 called for: knowledge component and surmise relation named and defined, the not-a-curriculum-claim caveat explicit. First drafts of both carried pipeline machinery ("one judge inside a pipeline", "per call", "your verdict becomes one directed edge", "a judge who does not see your answer") — cut by founder review 2026-08-01: that text is context for the pipeline's authors, not the judge, and this stage differs from prior stages in that we know exactly what we want for every case, so the open question is precisely whether added framing helps or just adds weight. Direction isolation survives in both, rephrased as a task instruction ("the reverse question is a different question; answer only this one"). Both name record_verdict directly, v005-style. Level definitions live in the tool alone. | **Benched 2026-08-01 over 279 pairs each (runs in reports/deepseek-judge-v001-*.json); surmise promoted default, transfer retired as the lean control.** The variants agree on 91.8% of directional calls, but the resolver doubles the visible gap: transfer commits 3 composite KCs, surmise 6 — and on all 3 disputed groups Opus (the trusted reference) sides with surmise. Failure pattern of the lean prompt: too literal — it treats task-wording accidents ("the second main limitation discussed") as knowledge demands and vetoes real merges. The theory framing is load-bearing: naming the pool-of-questions identity keeps the judge on the knowledge behind the task. Surmise also sits closer to Opus overall (90.2% vs 86.2%) with no hedging pathology (middle levels 10.6% of calls). Known weakness (reports/opus-vs-deepseek-r0130.md): contested "likely" yeses tend to be wrong — planned remedy is level-gated escalation: likely verdicts get a second opinion from Opus via subscription workflow (never paid API; founder decision 2026-08-01 — Opus is reference/escalation tier only, too expensive to be a recurrent judge). |

## Tools

| file | idea |
| - | - |
| tool-v001.json | record_verdict with the 4-level enum. Level semantics live here, shared by both variants, so the A/B isolates framing. The two clear levels are anchored to what the reason can demonstrate or name; the middle levels are defined as genuine uncertainty ("not caution") to resist middle-dumping, the hedge risk the memo flags. |

## Bench plan (first run)

Model: deepseek/deepseek-v4-pro, thinking high, via OpenRouter — both
variants in parallel over the same pair set. Pair set: the full superset
over the r0130 corpus (reports/grouping-data.json) — semantic floor 0.70
cap 15 ∪ lexical BM25 top-5 ∪ legacy top-5 (the Opus 128) ∪ dense pairs
sim ≥ 0.75 — plus iterative triangle closure; 279 base pairs ≈ 558
directional calls per variant. Every pair records which generator(s)
proposed it, feeding the per-generator audit. Reference: the Opus 5 run
(binary, trusted per the 2026-08-01 decision — no human gold standard);
comparison is informal, by collapse, and disagreement locates pairs worth
examining rather than scoring either judge.
