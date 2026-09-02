# Lesson Segmentation Quality Audit

## Mission

Audit the proposed Lesson Segments for exactly one Lesson. Decide whether the
segmentation is good enough for the Companion to teach from, or whether it needs
a targeted repair.

## Inputs

Use only the provided `lesson`, `concepts`, and `segments`. Stay blind to other
Lessons. Do not reopen source analysis, dependency inference, workbook labels,
or web research.

## Audit Criteria

Score each field from 0 to 3:

- `segment_coherence`: Concepts grouped into natural teaching chunks.
- `segment_order`: Segments form a coherent lesson-local teaching flow.
- `concept_order`: Concepts inside each Segment are ordered naturally.
- `label_quality`: labels are short, accurate, and useful.
- `focus_window_size`: Segments target one to four Concepts; five or more is
  usually too broad.

Use `repair_required` only for changes that materially improve teaching flow.
Do not nitpick stylistic preferences.

## Output Contract

Return one valid JSON object only. Do not include markdown fences or commentary.

```json
{
  "scores": {
    "segment_coherence": 3,
    "segment_order": 3,
    "concept_order": 3,
    "label_quality": 3,
    "focus_window_size": 3
  },
  "reliability": "reliable",
  "findings": [],
  "repair_instructions": []
}
```

When `reliability` is `repair_required`, include targeted
`repair_instructions`.

## Idioma obrigatório da saída

Escreva nomes e descrições de Conceitos, Critérios de Cobertura e conteúdo de Segmentos de Aula em português brasileiro (pt-BR). Preserve código, notação matemática, nomes próprios e identificadores exatos no idioma e formato originais.
