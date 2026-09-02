# Knowledge Type Quality Audit

## Quick Start

Audit whether the current Concept `knowledge_type` classifications are reliable
enough for final graph export.

## Inputs

Use only the provided `current_classifications`, `conflicts`, `distribution`,
and `taxonomy`.

The taxonomy definitions come from `creation/prompts/knowledge_type_classification/taxonomy_source.txt`.

## Audit Criteria

Score each field from 0 to 3:

- `taxonomy_fit`: labels match the taxonomy definitions.
- `teaching_mode_alignment`: rationales fit the Concept's likely teaching mode.
- `segment_consistency`: repeated Concepts are resolved consistently.
- `factual_boundary`: pure recall is factual, but reasoning-heavy concepts are
  not over-labeled factual.
- `applied_boundary`: applied is used for scenario judgment and trade-offs, not
  for every practical-sounding topic.

Flag real issues only. Do not repair harmless wording differences.

Look specifically for:

- definitions marked procedural,
- API/tool execution Concepts marked conceptual,
- historical/name-only Concepts marked applied,
- suspicious underuse of applied,
- suspicious absence of factual,
- Segment-internal inconsistencies,
- cross-Segment conflicts for repeated Concepts.

## Output Contract

Return one valid JSON object only. Do not include markdown fences or commentary.

```json
{
  "scores": {
    "taxonomy_fit": 3,
    "teaching_mode_alignment": 3,
    "segment_consistency": 3,
    "factual_boundary": 3,
    "applied_boundary": 3
  },
  "reliability": "reliable",
  "flags": [],
  "findings": [],
  "repair_plan": []
}
```

When `reliability` is `repair_required`, include a targeted `repair_plan` with
Concept IDs, a repair reason, and a concrete explanation.

Allowed repair reasons:

- `cross_segment_conflict`
- `taxonomy_mismatch`
- `definition_as_procedural`
- `tool_execution_as_conceptual`
- `historical_name_as_applied`
- `applied_underuse`
- `factual_absence`
- `segment_inconsistency`

## Never

- Do not search the web.
- Do not add, remove, or rename Concepts.
- Do not change Segment membership.
- Do not request broad taxonomy redesign.

## Self-Check

- Use `repair_required` only when a targeted repair would improve teaching.
- Every repair-plan item has Concept IDs and a concrete explanation.
- Cross-Segment conflicts must be repaired.
