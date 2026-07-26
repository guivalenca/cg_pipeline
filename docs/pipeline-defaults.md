# Pipeline defaults

Operational choices per stage, decided by eye on real results. Not
architecture (that lives in the ADRs); these change whenever a better
result changes our mind, and old runs remain in the ledger either way.

| stage | model preset | prompt | decided |
| - | - | - | - |
| passage-cuts (coarse candidate) | deepseek-v4-flash, thinking high | passage-cuts/v001 | 2026-07-26, identical cuts across 4 runs; r0017 is the reference |
| passage-cuts (granular candidate) | deepseek-v4-pro, thinking high | passage-cuts/v002 | 2026-07-26, steadiest granular behaviour (13 passages in 3 of 4 runs); r0031 is the reference |
| passage-triage | deepseek-v4-flash, thinking high | passage-triage/v001 | 2026-07-26, r0043; zero unsure, zero disagreement with the pro thinking preset over 25 passages |

Task generation takes provenance at the passage level only (the run_item
already records it); block-level citation stays in reserve if results ask
for it.

Retired along the way: passage-cuts/v003 (destabilizes flash badly, no
gain over v002 on pro), deepseek-v4-pro without thinking for judgment
stages (erratic in cuts r0014 and the only dissenter in triage r0044).
v002 was briefly retired by mistake and restored; the reference runs for
the next stage are r0017 and r0031.
