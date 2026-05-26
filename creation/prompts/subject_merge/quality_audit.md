# Subject Merge Quality Audit

## Quick Start

Judge whether the current subject-level concepts are reliable enough to continue. Use the provided candidate context, current concepts, merge attempts, and review signals. Prefer under-merging over over-merging: flag a missed merge only when the candidates are clearly the same teachable idea at the same level.

## Audit Rules

- Preserve granularity over reducing the concept count.
- Treat source candidate IDs as the ground truth for coverage and provenance.
- Do not call two concepts duplicates just because one mentions another as a contrast, prerequisite, limitation, example, or related tool.
- Keep definitions separate from implementation, math, limitations, applications, deeper mechanisms, and tool-specific behavior unless the same student action would assess both.
- Use merge-attempt history as context, not as an instruction to agree with earlier stages.
- Use review signals only as leads to inspect; they are not findings by themselves.
- If a hard integrity guardrail reports missing assignments or provenance loss, include it in the audit and repair plan.
- If a possible missed merge is real but not obvious, leave it unflagged.

## Output

Return one JSON object only:

```json
{
  "scores": {
    "identity_correctness": 3,
    "granularity_preservation": 3,
    "provenance_preservation": 3,
    "assignment_completeness": 3,
    "overlap_reduction": 3,
    "subject_coherence": 3,
    "net_phase5_benefit": 3
  },
  "reliability": "reliable",
  "flags": [],
  "repair_plan": [],
  "missed_merge_candidates": [
    {
      "candidate_ids": ["candidate-a", "candidate-b"],
      "confidence": "high",
      "explanation": "Why these are obviously the same teachable idea."
    }
  ]
}
```

Use `repair_required` only when at least one flag needs repair.

Allowed flags are:

- `assignment_incomplete`
- `provenance_loss`
- `over_merged_group`
- `granularity_violation`
- `residual_duplicate`
- `missed_obvious_merge`

Allowed repair reasons are:

- `assignment_incomplete`
- `provenance_loss`
- `over_merged_group`
- `residual_duplicate`
- `missed_obvious_merge`

## Self-Check

- Every repair-plan item has candidate IDs and a concrete explanation.
- Every flagged missed merge is same idea, same level, and high confidence.
- No repair asks to merge related-but-different concepts.
- No web search or outside knowledge.
