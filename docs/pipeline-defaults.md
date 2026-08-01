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
| task-revision | deepseek-v4-pro, thinking high | task-revision/v004, tool-v003 (brake variant) | 2026-07-28, r0090 originals bench: 27 stands / 4 rewritten / 1 unfixable, all four blocking defects fixed; r0087 parts bench: 18/18 stands, zero expansions |
| task-triage | deepseek-v4-pro, thinking high | task-triage/v001 | 2026-07-26, r0067; runs after revision via --revision-run, 31/31 supported, zero unsure |
| task-granularity | deepseek-v4-pro, thinking high | task-granularity/v004 | 2026-07-27, r0075; 22 single / 9 composite / 18 parts; the founder's target splits (T08, T18) land and enumerations stay single |
| task-revision (parts) | deepseek-v4-pro, thinking high | task-revision/v003, tool-v002 | retired 2026-07-28 by the new single-pass order |
| task-substance | deepseek-v4-pro, thinking high | task-substance/v004, tool-v004 (mandatory reason) | 2026-07-28, r0091; verdict-only pair gate, 5 does_not_work / 35 works; reasons legible one by one, protected simple-but-real tasks all kept |
| kc-statement | deepseek-v4-pro, thinking high | kc-statement/v005, tool-v007 | 2026-07-28; class-neutral knowledge identifier (declarative claim, procedures as rules, axes carry no trace in wording). Arc: v001 learner-objectives (r0102) -> v002 one-demand (r0121) -> v003 retired (grammar cast axis votes) -> v004 A/B (prohibition vs destination framing; differences at the run noise floor) -> v005 = destination base + one targeted anti-command clause -> v006 (scope clause against compound/over-general statements) benched 3x (r0131-r0133) and retired: missed its target (t08 altitude) and anchored function names/ordinals 3-of-3. Reference run r0130 (33 stated, 0 unsure); see prompts/kc-statement/README.md. The chain requires --passages-from r0017: r0052 also generated over the retired granular division (r0031), and without the filter those unjudged tasks trip the silence guard. passages_from is now stamped in run params (it was not, which hid the flag from r0121's record). Stable defect classes fixed structurally; invented terms/source echoes/code names flicker at 2-3 per 33 per run (model noise floor; majority-of-N is the known remedy if grouping suffers). |
| task-modality | majority of 3: pro thinking + pro non-thinking + flash thinking | task-modality/v002, tool-v001 | 2026-07-28, r0124+r0125+r0126 under universe.task_axes; v002 draws the line at apply-to-a-case vs put-into-words (Merrill use/remember, KLI new-instance), so retrieval-shaped "Name X" tasks are explain; 31/33 unanimous. v001 (r0109-r0111) retired with the fact scoping |
| task-knowledge | majority of 3: pro thinking + pro non-thinking + flash thinking | task-knowledge/v003, tool-v002 (two-way: concept/procedure) | 2026-07-28, r0113+r0114+r0115 under universe.task_axes; flash non-thinking excluded (27% miss, concept flattening); 2-1 splits flagged as the working unsure. 2026-07-28: fact dropped as a class — five prompt attempts could not detect it reliably (best: 2 hits + 4 false positives), and fact misclassifications blocked the strongest true pairs in grouping; any fact is learnable phrased as a concept. Reference runs r0127+r0128+r0129 (30/33 unanimous). Our concept deliberately folds in principles (A&K's sense, not Merrill/KLI's narrow category sense). |
| task-fact | retired 2026-07-28 | task-fact/v001-v003 | binary fact detector benched in r0120/r0122/r0123; retired with the fact class. Ledger keeps the runs. |
| kc-judge (directional mastery) | deepseek-v4-pro, thinking high | kc-judge/v001-surmise, tool-v001 (4-level verdict) | 2026-08-01, scratch bench over the r0130 corpus (reports/deepseek-judge-v001-surmise.json; report reports/kc-judge-bench-v001.md). Theory-framed prompt beat the lean control (v001-transfer): 6 composite KCs vs 3, Opus siding with surmise on all 3 disputed groups; lean prompt failed by literalism (task-wording accidents read as knowledge demands). Candidate set: generator union (semantic floor 0.70 cap 15 + lexical BM25 top-5 + closure), floor confirmed by yield curve — duplas exist down to 0.72, none below. Middle-level hedging low (10.6%). Known weakness: contested "likely" yeses lean wrong (reports/opus-vs-deepseek-r0130.md); planned remedy is likely-gated escalation to Opus via subscription workflow, never paid API. OpenRouter routing for future runs: exclude fp4 providers, sort by throughput; provider stamped per call since 2026-08-01. |

Grouping input (decided 2026-07-28): the embedding for grouping encodes
the kc-statement text, not task+answer — the statement is the grouping
key, class-neutral by design; the voted axes partition each proximity
group into grains, and the canonical per-grain phrasing at the end
re-introduces the axis deliberately. The task-embedding stage still
renders task+answer and needs a statement-input template before the next
ledger embedding run. First statement embedding (scratch, v005 bench,
qwen3-embedding-8b): median unrelated-pair cosine 0.57, known
same-knowledge pairs at 0.84-0.90 — clean separation; data in
reports/explorer-data.json, tool in reports/embedding-explorer.html.

Task generation runs over the coarse division (r0017). The granular division
(r0031) is retired for this stage: its stub passages (heading plus an input
array) produced memorization and counting trivia under every model and every
prompt tried. Deixis in task wording ("according to the passage") is accepted:
prompt wording cannot move the pro model on that axis, grouping reads task
plus answer so the shared prefix carries no discriminating weight, and
passage provenance resolves the reference anyway.

The canonical task order (decided 2026-07-28): generation, granularity
(splits packed tasks; parts materialized as task rows with provenance in
the granularity run item), one revision pass over the whole post-split set,
triage with the source over the final text, substance as the last gate,
then embedding. Each stage runs exactly once, and everything that creates
or transforms text happens before the gates: a generative act after a gate
would invalidate that gate's guarantee, which is what kept happening under
the old interleaved order.
Revision judges each task blind (task and answer only, no source); unfixable
means even the answer cannot rebuild it. Triage then holds the source, so a
referent the revision invented is caught there; the two stages cover each
other's failure mode. Substance judges the pair as evidence of learning and
only discards, with a mandatory one-sentence reason per verdict.
Stage references: r0052 generation, r0075 granularity, r0090 revision
(originals bench), r0087 (parts bench), r0067 triage, r0091 substance.
Pending before the order is fully proven: granularity has not yet been run
over raw unrevised tasks (r0075 judged revised text), and triage has not
yet been rerun in its new position over the post-split revised set.

The accepted cost is that decorative deixis ("according to the passage"-style
garnish) now survives revision by design; revisit this if it pollutes embeddings.

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
