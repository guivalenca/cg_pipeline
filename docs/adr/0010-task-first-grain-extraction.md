# 0010: Task-first grain extraction over deterministic blocks

Date: 2026-07-26
Status: accepted, amended 2026-07-26 (see Amendments); stages 4–5 redefined
by 0011 (2026-08-02): grouping is directional pair judging + clique
snapshots, not embed-cluster-merge

## Context

The passage-segmentation experiment (runs r0003 to r0010) showed that no
model configuration reproduces its own cuts, and that the v001 prompt asked
for interpretation (title, teaches) inside what was meant to be the primary
fact unit. Literature research (now in the research archive at
`~/Desktop/concept-universe-research/`) then showed the classical
tradition never derives knowledge units from text segmentation: KC models are
defined as mappings from assessment tasks to knowledge, tasks-first beat
text-first when measured directly (Matsuda et al. 2022), grouping before
naming beats naming before deduplicating, imposing a controlled vocabulary
during generation degrades output, and single prompts fail at partitioning
long lists.

Grain definition adopted: the KLI Knowledge Component definition. A grain is
an acquired unit of cognitive function inferred from performance on related
tasks. A grain is admissible only if a task could test it.

## Decision

The path from artifact to grains runs in these stages, each stamped:

1. **Blocks** (deterministic code, no model): each artifact is split into
   the units markdown already delimits: paragraph, heading, code block, list
   item, image. Blocks are the atomic address unit and the only segmentation
   that is a fact.
2. **Passages** (model, not a fact): a call groups adjacent blocks into
   passages, output as block ranges, never copied text. The passage is a
   focus unit for extraction and a future retrieval unit for the tutor. It
   cannot be factually wrong, only better or worse, so instability is
   tolerable. Its id is derived from the artifact and block range. A separate
   stamped call writes one situating sentence per passage with the whole
   document in context; stored now, consumed by the tutor later.
3. **Task generation**: one call per passage, whole source as context plus
   the passage in focus, XML-tagged. The prompt is simple and natural: no
   taxonomy, no literature vocabulary, no requested phrasing style (evidence:
   Bloom alignment during generation degrades quality). Every task must be
   answerable from the source alone and cites the block(s) that answer it,
   which covers provenance and fidelity in one guardrail.
4. **Grouping**: tasks of a source are embedded and clustered; a judge
   merges or eliminates within and across neighborhoods, one judgment per
   call (ADR 0009). No single prompt partitions a long list. This embed-plus-
   judge consolidation is built as a reusable component: the same machinery
   later consolidates grains into KCs.
5. **Naming**: only after grouping, one call writes the grain phrase with
   its axes, inheriting the provenance of every task in the group.

Granularity of grains is a cut parameter of the clustering step, tunable in
code and re-runnable, not a prompt instruction.

Reliability is measured at the outcome: run the pipeline again on the same
source and compare final grains in embedding space. This replaces boundary
F1, which measured cut positions before any definition existed.

## Open to test

- Passage-focused generation versus one whole-source call (expectation:
  focus wins on predictability; cheap harness A/B).
- Whether the passage grouping needs a model at all or a mechanical window
  over blocks suffices.
- The clustering cut parameter.

## Consequences

- Stage 1 of ADR 0009 ("Model Reading extracts passages and candidate
  grains") is superseded by stages 1 to 5 above. The one-judgment-per-call
  principle and ADR 0009's downstream stages (sizing, blocking, membership,
  whole-set gate) are unchanged. (2026-08-02: no longer true of the last
  two — ADR 0011 replaced the membership judge and dropped the whole-set
  gate; see 0009's status note.)
- prompts/passage-segmentation/v001 is retired; the first real prompt to
  design is task generation.
- The fact ledger of ingestion (source, snapshot, artifact, blocks) contains
  no model output. Everything a model writes is stamped and re-runnable.

## Amendments (2026-07-26, after building stages 1 to 3)

Building and measuring the pipeline changed four things about the stage
list above. The as-built flow is:

blocks → passages → **passage-triage** → task generation →
**task-revision** → **task-triage** → grouping → naming

1. **Passage-triage gates generation.** A stamped judgment run marks each
   passage filler or not_filler; only passages every gating run judged
   not_filler get generation calls. Silence is not a verdict: an unjudged
   passage stops the run instead of slipping through.
2. **A task is a pair, not a question.** Each task carries two fields,
   task and answer, both in English whatever the source language. The
   answer is the model's short answer in its own words drawn from the
   source. It exists for three consumers: the grouping embedding (task
   plus answer is what gets embedded), the answerability check during
   generation, and as the anchor for revision. It is not tutor-facing.
3. **Block citation was dropped.** Stage 3 above says each task cites the
   block(s) that answer it; in practice provenance is taken at the passage
   level only (the run item already records it), and block-level citation
   stays in reserve. The "answerable from the source alone" guardrail
   survived as prompt wording, iterated empirically (see `experiments.md`
   in `~/Desktop/concept-universe-research/`).
4. **Two per-task stages exist between generation and grouping.**
   Task-revision judges each task blind, seeing only the task and its
   answer, the way the learner will meet it: a task that leans on a text
   it cannot show is rewritten minimally, anchored on the answer, or
   declared unfixable when even the answer cannot rebuild it. Task-triage
   then judges the revised text with the whole source in hand. The pairing
   is deliberate: revision rewrites blind and can invent a referent;
   triage holds the source and catches it. Unsupported and unfixable
   tasks are discarded, never patched: volume is free and rows are
   insert-only, so the cure for a bad task is its absence. Grouping
   consumes the revised, triaged set.

Operational choices per stage (which model, which prompt version, which
run is the reference) live in docs/pipeline-defaults.md, not here.
