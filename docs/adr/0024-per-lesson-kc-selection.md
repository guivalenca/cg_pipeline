# 0024: Per-lesson KC Selection and a selected-only Universe

Date: 2026-08-21
Status: accepted; the Lesson Purpose and the counterfactual survival
criterion are superseded by ADR 0026 (2026-08-22) — selection judges the
curricular record directly, as optimization.

## Context

Exhaustive extraction works: a lesson with a couple of sources yields 150–300
KC candidates. Consuming that in the Companion did not: the only path was an
LLM dividing and ordering candidate blobs into segment instructions, which
throws away the unit the whole pipeline exists to produce — the task with its
answer, statement, and axes. The founder rejected that loss and chose
strategic selection instead: a small core of candidates per lesson carries
most of the teaching value (Pareto as guiding intuition, not a target ratio —
no fixed percentage is part of this decision). A second pressure points the
same way: the judge stage is pairwise, so every unselected candidate that
reaches it multiplies cost quadratically for knowledge no lesson will teach.

## Decision

**Three checkpoints.** The interpretation pipeline now runs through three
explicit operator checkpoints, renamed for first-read legibility:

| Former name            | Name                    | Does                                     |
| ---------------------- | ----------------------- | ---------------------------------------- |
| Lesson Knowledge Build | KC Generation           | publications → KC Candidates (11 stages) |
| — (new)                | KC Selection            | candidates → selected core, per lesson   |
| Syllabus Knowledge Build | Universe Reconciliation | selected candidates → merged Universe (4 stages) |

KC Corpus Manifest is renamed **Reconciliation Scope**. CONTEXT.md carries
the definitions; code modules keep their former names until the rename
tickets land.

**KC Selection.** Judges each lesson's KC Candidates against that lesson's
**Lesson Purpose**. The survival criterion is counterfactual: a candidate is
selected when removing it would materially reduce what the student can
understand, explain, distinguish, or do relative to the purpose. Selection is
authorized to cut true, teachable, non-redundant knowledge — the distinction
is *useful somewhere* versus *worth teaching in this lesson*. No per-source
quotas, no caps, no percentage targets: the cut is judgment, not arithmetic.

**Selection is local; the Universe is the union.** An omitted candidate is a
curricular omission, never a deletion: it remains reusable knowledge of its
Source Publication and may be selected by another lesson. A candidate joins
the Universe when at least one active lesson selects it. The Reconciliation
Scope therefore freezes the union of selected candidates of one Syllabus
Version — no longer the publication set — and the four shared stages run only
over selected candidates. Two near-identical candidates selected by different
lessons still merge downstream; selection runs before identity, deliberately.

**Lesson Purpose.** Derived from curricular context only — title, description,
subjects — never from source content, so the purpose says why the lesson
exists rather than summarizing what the sources contain. Auto-generated when
selection is first requested; the operator may edit or approve it, or ignore
it and let the generated text stand. Draft and approved text are both ledger
facts. A purpose demanding something no source covers is a curricular gap
signal, not an error: selection only cuts, never invents.

**Zero-selected sources block.** A source whose candidates are all omitted
puts the lesson in an attention state. The lesson's selection is not complete
until the operator re-runs, adds sources, or explicitly accepts the lesson as
empty (a placeholder that cannot start a session). Acceptance is a recorded
operator action.

**Generations.** Re-selection (purpose changed, candidate pool changed, or a
better prompt/model) writes a new selection generation beside the old one;
consumers read the newest, history stays — the same pattern ADR 0011 set for
judge verdicts.

## Open, deliberately

- The selection mechanism — one verdict per candidate versus set-level batch
  selection, and what the judge sees per candidate — is decided by a bench
  (Linear DEV-23), not on paper. This ADR records the checkpoint, not the
  mechanism.
- The Companion seam (segments, sessions) stays out of scope until real
  selected cores exist to design against.

## Consequences

- Shared-stage cost drops to a fraction: embedding and pairwise judging touch
  only selected candidates.
- ADR 0011's merge rule is unchanged; its input becomes the selected set.
- ADR 0010's stage list gains a lesson-scoped stage between the local eleven
  and the shared four — a third orchestration scope beside publication and
  scope targets.
- The evaluator and any downstream consumer of a lesson version see only its
  selected KCs; noise reduction is the point, not a side effect.
- CONTEXT.md was updated with KC Candidate, Lesson Purpose, KC Generation,
  KC Selection, Universe Reconciliation, and Reconciliation Scope.
