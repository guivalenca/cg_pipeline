# Knowledge Type Quality Repair

## Quick Start

Repair only the targeted Concept `knowledge_type` labels from the quality audit.

## Inputs

Use only the provided `target_concept_ids`, `current_classifications`,
`quality_audit`, and `taxonomy`.

The taxonomy definitions come from `prompts/system_prompt.txt`.

## Workflow

1. Read the repair plan and target Concept IDs.
2. Inspect only the target Concepts and their Segment evidence.
3. Choose one primary teaching mode per target Concept.
4. Preserve every target Concept ID exactly.
5. Return a short rationale that explains the deciding clue.

## Output Contract

Return one valid JSON object only. Do not include markdown fences or commentary.

```json
{
  "classifications": [
    {
      "concept_id": "target-concept-id",
      "knowledge_type": "procedural",
      "rationale": "Coverage requires executing a step-by-step API workflow.",
      "confidence": 0.9
    }
  ]
}
```

## Never

- Do not repair untargeted Concepts.
- Do not create new Concept IDs.
- Do not change Segment membership.
- Do not infer dependencies.
- Do not search the web.

## Self-Check

- Every target Concept is classified exactly once.
- No untargeted Concept appears in the output.
- Every `knowledge_type` is one of `conceptual`, `procedural`, `factual`, or
  `applied`.
- Every rationale addresses the audit reason directly.
