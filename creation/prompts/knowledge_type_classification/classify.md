# Knowledge Type Classification

## Quick Start

Assign the primary teaching mode for each Concept in one Lesson Segment.

## Inputs

Use only the provided `lesson`, `segment`, `concepts`, and `taxonomy`.

- The Lesson contains `lesson_id` and `title`.
- The Segment contains `segment_id`, `label`, and `concept_ids`.
- Each Concept contains `concept_id`, `label`, `teaching_description`,
  `coverage_criteria`, and optional `source_candidate_ids`.
- The taxonomy definitions come from `prompts/system_prompt.txt`.

Do not use existing `knowledge_type` values, source depth, dependency guesses,
other Lessons, or web research.

## Taxonomy

- `conceptual`: principles, relationships, why questions.
- `procedural`: algorithms, step-by-step processes, how questions.
- `factual`: definitions, dates, terminology, what questions.
- `applied`: real-world scenarios, design decisions, when-to-use judgment.

## Workflow

1. Read the Segment label for local teaching context.
2. Read each Concept label, teaching description, and Coverage Criteria.
3. Decide which teaching mode is primary for assessing that Concept.
4. Use `procedural` for execution steps, API/library usage, algorithms, or
   calculations performed step by step.
5. Use `conceptual` for principles, relationships, distinctions, mental models,
   and why-oriented understanding.
6. Use `factual` only for direct recall of definitions, names, dates, or terms
   with low reasoning.
7. Use `applied` for scenario judgment, design decisions, trade-offs, and
   choosing when to use an idea in context.

## Output Contract

Return one valid JSON object only. Do not include markdown fences or commentary.

```json
{
  "classifications": [
    {
      "concept_id": "input-concept-id",
      "knowledge_type": "conceptual",
      "rationale": "Short reason citing the deciding clue.",
      "confidence": 0.87
    }
  ]
}
```

## Never

- Do not search the web.
- Do not infer dependencies.
- Do not edit Segments.
- Do not rewrite Concepts.
- Do not create new Concept IDs.
- Do not omit, duplicate, or rename Concept IDs.

## Self-Check

- Every input Concept is classified exactly once.
- Every `knowledge_type` is one of `conceptual`, `procedural`, `factual`, or
  `applied`.
- Every rationale cites the clue that decided the label.
- When a Concept mixes modes, choose the primary teaching mode required by the
  Coverage Criteria.
