# Subject Merge Quality Repair

## Quick Start

Repair only the flagged target candidates from a Phase 5 quality audit. Use the current subject concepts as context, but do not reconsider unrelated candidates.

## Repair Rules

- If the audit flags an over-merge, split only the target candidates that represent different teachable ideas.
- If the audit flags residual duplicates, merge only target candidates that are the same teachable idea at the same level.
- If the audit flags a missed obvious merge, merge only target candidates that are clearly the same teachable idea at the same level; otherwise keep them standalone.
- Preserve lesson-local candidate IDs in `source_candidate_ids`.
- Keep implementation, math, limitation, application, deeper mechanism, and tool-specific behavior separate from definitions unless the target cards truly ask for the same student action.
- If a target candidate is uncertain, accept it as a standalone concept rather than using review or pruning.

## Output

Return one JSON object only:

```json
{
  "accepted_concepts": [
    {
      "id": "repair001",
      "label": "Specific subject-level teachable idea",
      "description": "Canonical understanding represented by this repaired concept.",
      "coverage_criteria": ["Observable check across repaired candidates."],
      "source_candidate_ids": ["target-candidate-id"],
      "merge_rationale": "Why these target candidates are the same concept or must stand alone."
    }
  ],
  "candidate_assignments": [
    {
      "candidate_id": "target-candidate-id",
      "status": "used_in",
      "accepted_ids": ["repair001"]
    },
    {
      "candidate_id": "represented-target-candidate-id",
      "status": "merged_into",
      "merged_into": "repair001",
      "explanation": "Why it is represented by repair001."
    }
  ]
}
```

## Self-Check

- Every target candidate ID appears exactly once in `candidate_assignments`.
- No unrelated candidate was added, removed, merged, or split.
- The repair addresses the audit reason directly.
- No `review`, `pruned`, dependency edges, final graph IDs, web search, or external knowledge.
