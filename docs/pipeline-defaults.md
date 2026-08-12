# Pipeline defaults

Operational choices per stage, decided by eye on real results. Not
architecture (that lives in the ADRs); these change whenever a better
result changes our mind, and old runs remain in the ledger either way.

| stage | model preset | prompt | decided |
| - | - | - | - |
| ordered-reconstruction | lossless PNG normalization + `img2pdf`; Firecrawl `/v2/parse` PDF `ocr` mode | ordered-document-reconstruction.v1 | 2026-08-11: manual screenshots and Browserbase book pages are ordered document evidence, not independent images. One audit-only image PDF enters the existing structural PDF Interface; original page assets supply the all-page figure-placement renders and are never published whole. Reader accessibility text is immutable supporting evidence, not a universal formula authority. |
| pdf-parse | Firecrawl `/v2/parse`, PDF `auto` mode, `markdown` + `images` | firecrawl-v2-parse.v1 | 2026-08-10: Firecrawl Markdown is canonical so tables remain tables and reading order is provider-owned. Extracted figures become local `pdf_figure` assets. Poppler text and 144 dpi page renders remain audit-only; renders are sent only to the separate figure-localization Module and are never published as full pages. |
| pdf-figure-localization | gemini-2.5-flash via OpenRouter, every rendered page in batches of at most 8 | pdf-figure-localization/v004, named bounding-box + Markdown-anchor tool | 2026-08-10: v004 inventories zero/one/multiple informative regions on every page even when Firecrawl returned images. The eight-page technical cap fixed a real 24-image call that described the page-8 workflow but returned page 4 and cropped prose. A local visible-text/page consistency guard prevents strong cross-page mix-ups from publishing. Deterministic crop polish adds side/bottom safety margin; on multi-region pages, ordered Poppler prose gaps replace Gemini's drifting vertical coordinates. Each crop is inserted beside a stable Markdown Block; only unmatched regions use the explicit unanchored fallback. |
| source-image-analysis | gemini-2.5-flash via OpenRouter, one grouped call per source | source-image-analysis/v003, tool-v001 | 2026-08-11: v003 is shared by article images and caption/STT video frames. It judges the complete visual set in source context, keeps distinct teachable visual evidence even when prose names the same topic, and removes repeated frames by choosing the clearest representative. Initial v001 rollout: 29 candidates, 23 analyzed in one call, 12 retained, 11 omitted, 6 technical failures preserved unresolved; US$0.0156393. |
| passage-cleanup triage | deepseek-v4-flash, thinking high; Gemini fallback; 90 s per attempt | passage-triage/v005, tool-v003 (tool-v003-atomic for one-element passages) | 2026-08-10: v005 keeps v004's citation-only bibliography rule but removes PDF-specific image immunity. Enriched figures are judged and may be dropped/refined like other teaching elements; unresolved images retain their safety rule. The per-attempt timeout starts the independent fallback promptly instead of leaving the UI apparently stuck on a slow provider. |
| passage-cleanup refine | deepseek-v4-flash, thinking high | passage-refine/v002, tool-v002 | 2026-08-07 initial rollout; local syllabus run r0003 applied two element-addressed revisions and retriaged both without rewriting source text |
| task-generation (cleanup input) | deepseek-v4-pro, thinking high | task-generation/v005, tool-v002 | 2026-08-07 initial rollout; local syllabus run r0005 reported 46 tasks and exercised the empty-array outcome on two preserved passages; report at reports/task-generation-r0005-of-r0001.md |
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
| kc-canonical-statement | deepseek-v4-pro, thinking high | kc-canonical-statement/v001, tool-v001 | One focused call per committed composite, attached to its exact grouping snapshot. It writes a shared statement from member tasks and answers only. Membership remains the pairwise judge's decision; `unsure` leaves the composite valid and unnamed. Accepted on `g0003`: runs r0164-r0165, 24/24 usable, 12/12 semantic agreement; see `reports/kc-canonical-statement-v001.md`. |
| task-modality | deepseek-v4-pro, reasoning disabled, single call | task-modality/v003, tool-v001 | 2026-08-06: v003 promoted after a frozen 18-task comparison against v002. It judges where correctness comes from (operating on supplied particulars vs articulating carried knowledge), not response grammar. Accuracy rose 83.3% → 94.4%; the two critical construction cases rose 50% → 100%; repeated critical cases were 100% consistent. Prior record: 2026-08-02 voting retired by the v1 simplification; one call per axis going forward. Identity no longer rides on axes; axes filter judge candidates and inform teaching style. v002 drew the line at apply-to-a-case vs put-into-words; r0124+r0125+r0126 were 31/33 unanimous. v001 retired with fact scoping. |
| task-knowledge | deepseek-v4-pro, thinking high, single call (majority-of-3 retired 2026-08-02) | task-knowledge/v003, tool-v002 (two-way: concept/procedure) | 2026-08-02: voting retired by the v1 simplification, same rationale and same no-re-run terms as task-modality. Prior record: 2026-07-28, r0113+r0114+r0115 under universe.task_axes; flash non-thinking excluded (27% miss, concept flattening); 2-1 splits flagged as the working unsure. 2026-07-28: fact dropped as a class — five prompt attempts could not detect it reliably (best: 2 hits + 4 false positives), and fact misclassifications blocked the strongest true pairs in grouping; any fact is learnable phrased as a concept. Reference runs r0127+r0128+r0129 (30/33 unanimous). Our concept deliberately folds in principles (A&K's sense, not Merrill/KLI's narrow category sense). |
| task-fact | retired 2026-07-28 | task-fact/v001-v003 | binary fact detector benched in r0120/r0122/r0123; retired with the fact class. Ledger keeps the runs. |
| task-embedding (statement input) | qwen3-embedding-8b | task-embedding/v002 (renders the statement only) | 2026-08-03, r0153: the statement-input template decided 2026-07-28 (Grouping input note below) is built — `--statements-from` embeds each task's newest usable kc-statement across the given kc-statement runs; r0153 covers r0130+r0147 (145 statements, 4096 dims) and is the judge's reference vector space. v001 (task+answer render) remains in the ledger for its historical runs. |
| kc-judge (directional mastery) | deepseek-v4-flash-0731, reasoning low, 16 workers | kc-judge/v003-surmise-pair, tool-v002 (both directions in one call, 4-level per direction) | 2026-08-07: Flash-low became the v1 default after a blind 60-pair test: it agreed with a valid Pro-high baseline on 59/60 merge decisions, scored 56/60 vs 57/60 under the deliberately conservative review, and cost $0.0228 vs $0.1405. The sole extra merge was accepted as harmless for v1. This decision applies only to the judge; canonicalization stays Pro-high. v003 itself was promoted 2026-08-06 for its explicit counterexample/falsification pass; candidate generation remains floor 0.70, cap 6, lexical top-5, axis filter after the cap, and clear_yes in both directions required to merge. |

Grouping input (decided 2026-07-28): the embedding for grouping encodes
the kc-statement text, not task+answer — the statement is the grouping
key, class-neutral by design; the voted axes partition each proximity
group into grains, and the canonical per-grain phrasing at the end
re-introduces the axis deliberately. The task-embedding stage still
renders task+answer and needs a statement-input template before the next
ledger embedding run. First statement embedding (scratch, v005 bench,
qwen3-embedding-8b): median unrelated-pair cosine 0.57, known
same-knowledge pairs at 0.84-0.90 — clean separation (the explorer tool
and its data were removed in the 2026-08-02 repo cleanup; regenerable
from the database).

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
caveats are in experiments.md in the research archive
(~/Desktop/concept-universe-research/).
