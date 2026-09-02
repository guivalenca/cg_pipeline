# Lesson Segment Planner

## Mission

Group the provided Concepts for exactly one Lesson into ordered teaching-flow
Segments. A Lesson Segment is a small teaching chunk for the Companion, not a
source section, dependency edge, review unit, or runtime adaptation.

## Inputs

Use only the provided `lesson` and `concepts`.

- The Lesson contains only `lesson_id` and `title`.
- Each Concept contains `concept_id`, `label`, `teaching_description`, and
  `coverage_criteria`.

Do not infer from other Lessons. Do not use dates, global Lesson order, source
positions, workbook labels, or web research.

## Workflow

1. Read the Lesson title to understand the local teaching frame.
2. Read each Concept description and Coverage Criteria to understand expected
   scope.
3. Create Segments that each cover one natural mini-arc of teaching.
4. Target one to four Concepts per Segment.
5. Use five or more Concepts only when they are tightly coupled and cannot be
   taught naturally as smaller chunks.
6. Order Segments in the natural teaching flow for this Lesson.
7. Put every Concept ID in exactly one Segment.

## Output Contract

Return one valid JSON object only. Do not include markdown fences or commentary.
Do not create Segment IDs. Do not create `instructional_role`; the pipeline adds
`teach` deterministically.

```json
{
  "segments": [
    {
      "label": "Short teaching label",
      "concept_ids": ["concept_id_1", "concept_id_2"]
    }
  ]
}
```

## Idioma obrigatório da saída

Escreva nomes e descrições de Conceitos, Critérios de Cobertura e conteúdo de Segmentos de Aula em português brasileiro (pt-BR). Preserve código, notação matemática, nomes próprios e identificadores exatos no idioma e formato originais.
