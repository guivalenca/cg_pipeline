# 0010: Task-first grain extraction over deterministic blocks

Date: 2026-07-26
Status: accepted

## Context

The passage-segmentation experiment (runs r0003 to r0010) showed that no
model configuration reproduces its own cuts, and that the v001 prompt asked
for interpretation (title, teaches) inside what was meant to be the primary
fact unit. Literature research (docs/lab/research/) then showed the classical
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
  whole-set gate) are unchanged.
- prompts/passage-segmentation/v001 is retired; the first real prompt to
  design is task generation.
- The fact ledger of ingestion (source, snapshot, artifact, blocks) contains
  no model output. Everything a model writes is stamped and re-runnable.
