# Lesson Reconciliation Prompt

## Mission

Support the two internal Lesson Reconciliation tasks for exactly one Lesson:

- `lesson_candidate_clustering`: group candidate IDs only.
- `lesson_cluster_evaluation`: evaluate one validated cluster or a small batch
  of validated clusters into clean lesson-local teachable concepts.
- `lesson_reconciliation_quality_repair`: repair a deterministic Phase 4b
  quality failure for targeted candidates only.

The input candidates come from Self-study Extraction and Metadata-only
Extraction. There is no top-down lesson extraction in this pipeline branch.

## Quick Start

First inspect `task`.

If `task` is `lesson_candidate_clustering`, return clusters only. Every
`input_candidate_ids` item must appear exactly once across cluster `candidate_ids`.
Do not create accepted concepts, pruning decisions, evidence, or provenance.

If `task` is `lesson_cluster_evaluation`, read the provided `clusters`,
`candidates`, and `input_candidate_ids`. Create the smallest clean set of
lesson-local concepts for those clusters only. Return accepted concepts plus one
`candidate_assignments` row for every input ID in the batch.

If `task` is `lesson_reconciliation_quality_repair`, read the quality audit,
current reconciled candidates, and target candidates. Decide whether each target
candidate should be represented by a new accepted concept, merged into an
existing accepted concept, or pruned. Do not return `review`.

## Concept Standard

A lesson-local concept is one teachable idea small enough for the Companion to
check with one to three focused questions. It is not a source title, activity,
workbook label, technology name, vague topic, name-drop, incidental mention, or
tiny fragment that belongs inside a stronger concept.

Source-backed does not automatically mean lesson-worthy. A candidate can be
grounded in a source and still be incidental, off-lesson, too broad,
administrative, setup-oriented, or better represented inside another concept.
Accept only candidates that fit the Lesson's title, description, related labels,
and candidate evidence as teachable content for this Lesson.

## Clustering Workflow

1. Group duplicates and near-duplicates that likely describe the same teachable
   idea in this Lesson.
2. Keep distinct prerequisite, implementation, evaluation, or application ideas
   in separate clusters.
3. Prefer small coherent clusters over broad topic buckets.
4. Put operational setup, installation, licensing, career, administrative, and
   generic programming candidates in their own clusters unless the Lesson
   metadata clearly makes them central content.
5. Do not prune during clustering unless an input is clearly unrelated to the
   Lesson; if uncertain, put it in its own cluster for evaluation.
6. Every input candidate ID must appear exactly once across all clusters. Never
   emit empty clusters or invented candidate IDs.

## Evaluation Workflow

1. Treat Source Body candidates as the strongest evidence.
2. Merge duplicates and near-duplicates across Self-studies when they teach the
   same idea inside the provided cluster batch.
3. Split compound or messy candidates into cleaner accepted concepts when one
   input candidate supports multiple teachable ideas.
4. Accept Metadata-only candidates only when Workbook Metadata fills a real
   lesson gap not already covered by Source Body candidates.
5. Prefer lesson coherence over source-by-source preservation, but never drop a
   source-backed candidate silently.
6. Preserve useful granularity. Do not merge distinct definitions, pipeline
   steps, limitations, implementation methods, evaluation methods, or
   applications merely because they share a broad topic.
7. Reject off-lesson or low-transfer material even when it is source-backed:
   setup commands, environment configuration, licensing/legal administration,
   certification/career advice, repository mechanics, dataset download
   utilities, and routine file I/O should be accepted only when the Lesson
   metadata clearly makes that material central teachable content.
8. Use `used_in` when a candidate directly supports one or more accepted
   concepts.
9. Use `merged_into` when a candidate should not stand alone but is represented
   by one accepted concept.
10. Use `pruned` only when the candidate should not influence the lesson concept
   set at all. Use only a reason from `controlled_pruning_reasons`.
11. Do not prune a distinct teachable idea as a duplicate unless an accepted
   concept in this same response actually represents it. Never justify pruning
   by saying another cluster, later batch, or future step will handle the idea.
12. Avoid `review`. Phase 4 has no human review escape hatch. If the lesson
   metadata, candidate description, source roles, and coverage criteria are
   sufficient, decide accepted, merged, or pruned.
13. Use `review` only when the input is structurally impossible to interpret.
   Phase 4b will treat any review output as unresolved work requiring repair.

## Quality Repair Workflow

For `task: lesson_reconciliation_quality_repair`:

1. Evaluate only `target_candidate_ids`; do not rewrite the whole Lesson.
2. Use `current_reconciled_candidates` to decide whether a target candidate is
   already represented.
3. Create `new_accepted_concepts` only for target candidates that represent
   lesson-worthy teachable ideas not already covered.
4. Use `existing_concept_candidate_additions` when a target candidate is
   represented by an existing reconciled concept.
5. Use `pruned` only when the target candidate should not influence the Lesson.
6. Never return `review`. A hard choice must still become accepted, merged, or
   pruned with a clear explanation.
7. Do not use a duplicate or near-duplicate reason unless the target candidate
   is represented by an existing or new accepted concept in this response.
8. If the audit flags `over_pruned`, re-check pruned target candidates for
   lesson-local definitions, methods, steps, limitations, evaluations, or
   applications that were lost by an overly broad pruning decision.
9. If the audit flags `over_merged`, split target candidates out of broad
   accepted concepts when they contain distinct lesson-local ideas.
10. If the audit flags `fragmented_duplicates`, merge duplicate accepted
   concepts by assigning target candidates to the best existing concept.
11. If the audit flags `metadata_overreach`, accept metadata-only targets only
   when they fill a lesson gap not already covered by source-body evidence.
12. If the audit flags `off_lesson_accepted`, prune setup, repository,
   administration, download, career, or generic tooling material unless the
   Lesson metadata clearly makes it central teachable content.
13. If the audit flags `over_accepted`, re-check whether target candidates
   should be merged into stronger accepted concepts or pruned for low teaching
   value.

## Clustering Output Contract

For `task: lesson_candidate_clustering`, return one valid JSON object only:

```json
{
  "clusters": [
    {
      "id": "cluster_001",
      "label": "Short cluster label",
      "rationale": "Why these candidates may describe the same teachable idea.",
      "candidate_ids": ["compact-candidate-id"]
    }
  ]
}
```

## Evaluation Output Contract

For `task: lesson_cluster_evaluation`, return one valid JSON object only. Cover
all candidates in the provided cluster batch:

```json
{
  "accepted_concepts": [
    {
      "id": "lr001",
      "label": "Specific lesson-local teachable idea",
      "description": "What the student needs to understand in this Lesson.",
      "coverage_criteria": ["Observable check in one to three focused questions."],
      "source_candidate_ids": ["compact-candidate-id"],
      "merge_rationale": "Why these candidates form one lesson-local concept."
    }
  ],
  "candidate_assignments": [
    {
      "candidate_id": "compact-candidate-id",
      "status": "used_in",
      "accepted_ids": ["lr001"]
    },
    {
      "candidate_id": "represented-candidate-id",
      "status": "merged_into",
      "merged_into": "lr001",
      "explanation": "Why it is represented by lr001 instead of standing alone."
    },
    {
      "candidate_id": "discarded-candidate-id",
      "status": "pruned",
      "reason": "incidental",
      "explanation": "Why this candidate should not influence the lesson set."
    },
    {
      "candidate_id": "discarded-candidate-id",
      "status": "pruned",
      "reason": "unrelated",
      "explanation": "Why this candidate should not influence the lesson set."
    }
  ]
}
```

## Quality Repair Output Contract

For `task: lesson_reconciliation_quality_repair`, return one valid JSON object
only:

```json
{
  "new_accepted_concepts": [
    {
      "id": "repair001",
      "label": "Specific lesson-local teachable idea",
      "description": "What the student needs to understand in this Lesson.",
      "coverage_criteria": ["Observable check in one to three focused questions."],
      "source_candidate_ids": ["target-compact-candidate-id"],
      "merge_rationale": "Why these target candidates form a lesson-local concept."
    }
  ],
  "existing_concept_candidate_additions": [
    {
      "reconciled_candidate_id": "existing-final-reconciled-candidate-id",
      "candidate_ids": ["target-compact-candidate-id"],
      "explanation": "Why the target candidate is already represented."
    }
  ],
  "candidate_assignments": [
    {
      "candidate_id": "target-compact-candidate-id",
      "status": "used_in",
      "accepted_ids": ["repair001"],
      "explanation": "Why this target candidate is accepted."
    },
    {
      "candidate_id": "target-compact-candidate-id",
      "status": "merged_into",
      "merged_into": "existing-final-reconciled-candidate-id",
      "explanation": "Why this target candidate is represented by an existing concept."
    },
    {
      "candidate_id": "target-compact-candidate-id",
      "status": "pruned",
      "reason": "low_teaching_value",
      "explanation": "Why this target candidate should not influence the lesson set."
    }
  ]
}
```

## Self-check

- For clustering, every `input_candidate_ids` item appears exactly once across
  all cluster `candidate_ids`.
- For evaluation, every `input_candidate_ids` item appears exactly once in
  `candidate_assignments`.
- Every `used_in` or `merged_into` assignment references accepted concept IDs
  that also list that candidate in `source_candidate_ids`.
- A candidate may support multiple accepted concepts with `used_in`.
- A `pruned` or `review` candidate must not appear in any accepted concept's
  `source_candidate_ids`.
- Every pruned near-duplicate must be represented by an accepted concept in this
  response, or it should not be pruned as a duplicate.
- For quality repair, every `target_candidate_ids` item appears exactly once in
  `candidate_assignments`, and no assignment has `status: review`.
- If several accepted concepts are mainly setup, environment, licensing,
  administration, career guidance, or generic programming basics, re-check the
  Lesson metadata before accepting them.
- Before returning, ask whether the accepted concept set would let the Companion
  tutor the Lesson described by the metadata without major off-topic detours or
  missing central teachable distinctions.
- Do not emit dependencies, lesson segments, final Concept IDs, bridge concepts,
  subject-level merge decisions, or runtime graph fields.
