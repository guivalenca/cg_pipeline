# Pipeline defaults

Operational choices per stage, decided by eye on real results. Not
architecture (that lives in the ADRs); these change whenever a better
result changes our mind, and old runs remain in the ledger either way.

| stage | model preset | prompt | decided |
| - | - | - | - |
| passage-cuts (coarse candidate) | deepseek-v4-flash, thinking high | passage-cuts/v001 | 2026-07-26, identical cuts across 4 runs (r0017/r0019/r0021/r0023) |
| passage-cuts (granular candidate) | deepseek-v4-pro, thinking high | passage-cuts/v003 | 2026-07-26, r0034 materialized; both candidates stay until grain results pick one |
| passage-triage | deepseek-v4-flash, thinking high | passage-triage/v001 | 2026-07-26, r0043; zero unsure, zero disagreement with the pro thinking preset over 25 passages |

Retired along the way: passage-cuts/v002 (loses on both models),
deepseek-v4-pro without thinking for judgment stages (erratic in cuts
r0014 and the only dissenter in triage r0044).
