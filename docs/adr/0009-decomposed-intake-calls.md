# 0009: Grain intake runs as decomposed focused calls

Date: 2026-07-24
Status: accepted

## Context

The intake path from a source artifact to KC membership involves several
different judgments. A single omnibus prompt doing extraction and grouping
together cannot be audited, compared, or improved per judgment, and its
output cannot be stored as distinct facts.

## Decision

Intake runs as separate focused calls, each output a stamped fact:

1. **Model Reading**: extracts passages and candidate grains from an
   artifact.
2. **Sizing gate**: per candidate grain, pass, split, or drop, writing the
   axes (condition→response form, knowledge type, do versus explain) as it
   rules. Working criterion: one focused question could test it; final
   confirmation pending inspection of real extraction outputs.
3. **Blocking** (deterministic): pgvector shortlist of candidate KCs.
4. **Membership judge**: the new grain against each candidate KC's canonical
   phrasing and exemplar questions, never against member grains. Verdicts:
   match, no-match, contains, contained-by, uncertain. An axis mismatch is an
   automatic no-match. Containment verdicts are stored as KC-to-KC edges and
   consumed by nothing in v1. The membership criterion the judge applies
   (leading candidate: question-pool interchangeability) is decided at the
   KC-stage build via the hand experiment.
5. **Whole-set gate**: before a non-trivial commit, one judge reads the
   entire resulting KC and confirms it is one skill.

Stages may be subdivided into further focused calls during execution; the
principle is one judgment per call, never several.

## Consequences

- Each stage is independently promptable, auditable in the dashboard, and
  comparable in the harness's run-comparison view.
- Every judgment lands in the ledger with model and prompt stamps, so any
  stage can be replayed or improved in isolation.
- More calls per grain than an omnibus prompt, accepted: calls are small,
  cacheable, and parallelizable per grain.
