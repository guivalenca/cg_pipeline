# kc-statement prompt versions

The stage reads one task with its expected answer (never the source) and
states the knowledge behind the task. The statement is what the embedding
stage encodes, so its wording is the grouping key: same knowledge should
yield near-identical statements, and the axes (modality, knowledge class)
should leave no trace in the wording — they are judged by their own
majority-of-3 stages and reattached at grouping.

## Prompts

| version | framing | verdict |
| - | - | - |
| v001 | "what answering well shows about what the learner now knows or can do" | Produced learning objectives ("The learner can explain that…", 33/33). That is an assessment claim about a learner, not a knowledge component; the verb wrapper duplicated the task-modality axis inside the text and the verb choice was model variance. Reference run r0102 (five-preset bench r0102-r0106). Retired. |
| v002 | "behind it sits one thing a person must know or be able to do" | The ontology fix: statements name content, not learners. Run r0121 with tool-v004. Wrapper dropped 33→5 but form went uncontrolled: knowing-verb relapses, one bare topic label, one tautology ("Tokenization splits text into tokens"), one invented term ("subword" for the source's "phrases"). |
| v003 | v002 plus two legal shapes (claim or instruction) and a reader test ("someone who does not know would learn something") | Scratch-benched on the same 33 tasks (no ledger run). Wrapper 5→0, topic label fixed, tautology improved — but the instruction clause let grammar cast an implicit axis vote that contradicted the voted axes both times it fired, and the reader test traded tautology for invention ("high-frequency… semantic value" imported from outside the pair). Kept as the record of why shape and informativeness rules belong elsewhere. |
| v004-rules / v004-index (A/B, scratch) | Two class-neutral candidates: declarative statements only, procedures stated as rules of how it is done, axes carried solely by the axis stages. "rules": explicit prohibition list plus a teach-test. "index": destination framing ("a sentence that could sit in an index of knowledge") with no bans. | Benched head-to-head over the same 33 tasks (scratch, no ledger runs). Both fixed every v001-v003 defect class. Residual differences were small: rules imported one rationale the source never gave (its teach-test) and anchored two statements to source function names; index produced one command-form statement and runs longer (mean 24 words vs 20). The founder judged index's parentheses and pair-sourced code all acceptable. |
| v005 | index base + the founder's single targeted anti-command line ("never as a command to the reader") added to the tool's how-it-is-done clause | The one place a specific, targeted "never" beat destination framing in the A/B: rules had zero command-form statements, index had one. v005 tests that line on the index base. |
| v006 | v005 base + one scope clause in the tool's statement description: "The statement carries exactly one claim; what the task does not test stays out of it." | **Tested 3× and retired (2026-08-01; runs r0131-r0133 vs baseline r0130).** The first revision motivated by a graph symptom rather than a wording defect: the frozen 6-node region of the r0130 judge run orbits the compound t01 and the hub t08, whose statement generalized past its tested instance. Three runs so pattern separates from noise. What held 3/3: double-demand halved (~5-6 → ~2 per run), stable classes stayed at zero, and the feared hollowing appeared in exactly one acceptable case (sparse-vector definition lost its cause). What failed: the motivating target — t08 kept the general BOW invariant in all three runs; the model read "what the task does not test stays out" as a content restriction, not an altitude restriction. And the clause caused two consistent regressions the baseline did not have: function names anchored statements (generate_bow 3/3, word_extraction 2/3, literal NLTK code 2/3) and a source ordinal ("the second main limitation", 3/3) — pulling the statement toward the task's text pulls the task's debris in with it. Verdict: the standalone-ness cost outweighs the double-demand gain; v005 stays default. Deeper lesson: on close reading, two of the three "culprits" were legitimate (t01's order clause is tested by its answer; t08's generality is the knowledge the task actually requires — a legitimate foundational hub, per the memo's hub taxonomy). The frozen region is not a prompt defect to fix upstream; it is what the 4-level verdict scale (weighted tiebreak) and the compound/vagueness exams exist for. |

## Tools

| file | change | used by |
| - | - | - |
| tool-v001.json | verdict stated/unsure, statement, reason | v001 (r0102) |
| tool-v002.json | "shows" → "requires" in the verdict description | v002 drafts |
| tool-v003.json | statement described as "the one thing, in one short line" | v002 drafts |
| tool-v004.json | adds the discipline block: one demand only, built only from task+answer, no examples/parentheses/code, no mention of task or passage | v002 (r0121) |
| tool-v005.json | adds the two-shape rule (claim or imperative) and the named-verb ban (no know/understand/recognize/be able to/how to) | v003 (scratch) |

| tool-v006-rules.json | prohibition-style statement description (ban list, "never a command… no examples… no ordering borrowed from the source") | v004-rules (scratch A/B) |
| tool-v006-index.json | destination-style statement description ("one claim of fact… shortened, not hollowed… reads the same without the task, the source, or the source's ordering"), no bans | v004-index (scratch A/B) |
| tool-v007.json | tool-v006-index plus one targeted clause: "…states how it is done, never as a command to the reader" | v005 |
| tool-v008.json | tool-v007 plus one scope clause: "The statement carries exactly one claim; what the task does not test stays out of it." | v006 (retired) |

Chosen positions worth remembering: the stage is blind (task and answer
only) and must stay neutral to both axes; prohibition lists bias the
model and resist auditing, so constraints should describe the destination
of the statement and stay mechanically checkable; informativeness tests
push the model to import content from outside the pair.

Looking ahead (revised by the v1 simplification, ADR 0011): the
graph-driven audit plan that once lived here — watching connection
patterns after each judge run and driving dedicated compound/vagueness
exam prompts from them, per the diagnostic menu in
`directed-precedence-graph.md` §5 (research archive,
`~/Desktop/concept-universe-research/`) — is deferred along with all
graph machinery. What survived from that episode is the division of
labor it settled: this stage's prompt owns wording defects; connection
patterns belong to the deferred graph side, because a graph symptom is
not always a statement defect — t08's hub status turned out to be
legitimate foundational knowledge. Accepted residual: the double-demand
flicker (~1-2 per 33) stays in the pipeline; majority-of-N remains the
known remedy if it ever blocks grouping.
