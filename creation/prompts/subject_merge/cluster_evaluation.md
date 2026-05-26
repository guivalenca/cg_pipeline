# Subject Merge Cluster Evaluation

## Quick Start

Decide whether one tight candidate cluster represents one subject concept or multiple standalone subject concepts. Use only the provided candidate cards.

## Identity Standard

Same concept means the same teachable idea at the same level, testable with the same question.

Different concept means one candidate adds materially different student behavior: implementation, math, limitation, application, deeper mechanism, tool-specific behavior, or a broader/narrower action.

Merge same-level duplicates even when wording, lesson title, or language differs. Keep deepenings separate even when they reuse the same topic name.

## Output

Return one JSON object only:

```json
{
  "accepted_concepts": [
    {
      "id": "sm001",
      "label": "Specific subject-level teachable idea",
      "description": "Canonical understanding represented by this concept.",
      "coverage_criteria": ["Observable check across merged lesson candidates."],
      "source_candidate_ids": ["candidate-id"],
      "merge_rationale": "Why these candidates are the same subject concept or must stand alone."
    }
  ],
  "candidate_assignments": [
    {
      "candidate_id": "candidate-id",
      "status": "used_in",
      "accepted_ids": ["sm001"]
    },
    {
      "candidate_id": "represented-candidate-id",
      "status": "merged_into",
      "merged_into": "sm001",
      "explanation": "Why it is represented by sm001."
    }
  ]
}
```

Allowed statuses are exactly `used_in` and `merged_into`. A standalone concept uses `used_in` pointing to its own accepted concept.

## Never

- Never use `review`.
- Never use `pruned`.
- Never create dependency edges.
- Never emit final graph concept IDs.
- Never split one lesson-local candidate into smaller atoms.
- Never use web search or external knowledge.

## Self-Check

- Every input candidate ID appears exactly once in `candidate_assignments`.
- Every `used_in` or `merged_into` reference points to an accepted concept that lists that candidate in `source_candidate_ids`.
- Same-level duplicates were merged despite wording or language differences.
- Different levels or behaviors remained separate.
