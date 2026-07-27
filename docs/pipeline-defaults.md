# Pipeline defaults

Operational choices per stage, decided by eye on real results. Not
architecture (that lives in the ADRs); these change whenever a better
result changes our mind, and old runs remain in the ledger either way.

| stage | model preset | prompt | decided |
| - | - | - | - |
| passage-cuts (coarse candidate) | deepseek-v4-flash, thinking high | passage-cuts/v001 | 2026-07-26, identical cuts across 4 runs; r0017 is the reference |
| passage-cuts (granular candidate) | deepseek-v4-pro, thinking high | passage-cuts/v002 | 2026-07-26, steadiest granular behaviour (13 passages in 3 of 4 runs); r0031 is the reference |
| passage-triage | deepseek-v4-flash, thinking high | passage-triage/v001 | 2026-07-26, r0043; zero unsure, zero disagreement with the pro thinking preset over 25 passages |
| task-generation | deepseek-v4-pro, thinking high | task-generation/v004 | 2026-07-26, r0052; zero factual errors over four runs, deepest sets on dense passages, atomic tasks map one-to-one onto grains |
| task-revision | deepseek-v4-pro, thinking high | task-revision/v003 | 2026-07-26, r0063-r0065; verdict profile stable across three trials, rewrites answer-consistent, and pro alone kept the vacuous task unfixable (flash rescued it, r0066) |
| task-triage | deepseek-v4-pro, thinking high | task-triage/v001 | 2026-07-26, r0067; runs after revision via --revision-run, 31/31 supported, zero unsure |
| task-granularity | deepseek-v4-pro, thinking high | task-granularity/v004 | 2026-07-27, r0075; 22 single / 9 composite / 18 parts; the founder's target splits (T08, T18) land and enumerations stay single |
| task-revision (parts) | deepseek-v4-pro, thinking high | task-revision/v003, tool-v002 | 2026-07-27, r0076; decided to reuse v003 and tool-v002 unchanged over materialized parts |

Task generation runs over the coarse division (r0017). The granular division
(r0031) is retired for this stage: its stub passages (heading plus an input
array) produced memorization and counting trivia under every model and every
prompt tried. Deixis in task wording ("according to the passage") is accepted:
prompt wording cannot move the pro model on that axis, grouping reads task
plus answer so the shared prefix carries no discriminating weight, and
passage provenance resolves the reference anyway.

The task flow is generation, revision, triage, granularity (v004 splits packed
tasks; parts materialized as task rows with provenance in granularity run
item), second revision over parts, substance as pure discard gate over the
post-split set (surviving singles plus revised parts), then embedding.
Revision judges each task blind (task and answer only, no source): the answer
anchors the rewrite, and unfixable means even the answer cannot rebuild it.
Triage then holds the source, so a referent the revision invented is caught
there; the two stages cover each other's failure mode. The reference chain
is r0052 generation, r0065 revision, r0067 triage, r0075 granularity, r0076
parts-revision, r0079/r0080 substance.

Task generation takes provenance at the passage level only (the run_item
already records it); block-level citation stays in reserve if results ask
for it. A task carries two fields, task and answer, both in English whatever
the source language: the answer is the model's own words drawn from the
source, kept for the grouping embedding and as the answerability check, not
for the tutor. Only passages every gating triage run judged not_filler get
calls (universe.taskgen).

Retired along the way: passage-cuts/v003 (destabilizes flash badly, no
gain over v002 on pro), deepseek-v4-pro without thinking for judgment
stages (erratic in cuts r0014 and the only dissenter in triage r0044).
v002 was briefly retired by mistake and restored; the reference runs for
the next stage are r0017 and r0031.

The task-granularity tool file is `tool-v001.json`; its `unsure` verdict was
added in place.

Provider note (2026-07-26): runs up to r0067 went to the native DeepSeek
API; the pipeline now runs on OpenRouter. The model presets above map to
`deepseek/deepseek-v4-flash` and `deepseek/deepseek-v4-pro`, thinking
toggled per request. Payload shapes, usage field changes and caching
caveats are in docs/lab/experiments.md.
