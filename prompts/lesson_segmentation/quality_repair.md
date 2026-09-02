# Lesson Segmentation Quality Repair

## Mission

Repair a Lesson Segmentation that failed quality audit. Make only the targeted
changes needed to satisfy the audit while preserving the v0 contract.

## Inputs

Use only the provided `lesson`, `concepts`, `current_segments`, and
`quality_audit`. Stay blind to other Lessons. Do not use source order, workbook
labels, dependency inference, or web research.

## Repair Rules

1. Follow the audit's `repair_instructions`.
2. Keep every Concept ID exactly once across all Segments.
3. Target one to four Concepts per Segment.
4. Preserve good existing labels and order where they still work.
5. Return only final repaired Segments.
6. Do not create Segment IDs or `instructional_role`; the pipeline adds those
   deterministically.

## Output Contract

Return one valid JSON object only. Do not include markdown fences or commentary.

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
