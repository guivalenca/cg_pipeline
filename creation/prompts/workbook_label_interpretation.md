You are classifying workbook labels for the Concept Graph Creation v0 pipeline.

Use the provided source ledger context and classify only the labels listed in
`labels_to_classify`. Relevant workbook context for each label is provided in
`label_contexts`. Reuse any labels provided in `existing_interpretations`
without changing their pattern, confidence, or rationale.

Allowed patterns:

- `prerequisite_hint`: a foundation concept that may be needed before the
  active NLP lesson synthesis.
- `lesson_cluster`: a direct NLP or lesson-theme cluster that should be active
  in v0 synthesis.
- `application_adjacent_signal`: useful application or software-engineering
  context that should remain audit-only.
- `ignored_ambiguous`: too broad, administrative, or ambiguous for active v0
  synthesis.

Return one valid JSON object with a `classifications` array. Include exactly one
row for every label in `labels_to_classify`.

Each row must have:

- `label`: exactly the input label.
- `pattern`: one of the allowed patterns above.
- `confidence`: short confidence label.
- `rationale`: one concise reason grounded in the provided workbook context.

The pipeline code will assemble the final `workbook_label_interpretation.v0`
artifact from your classifications, including context rows, summaries, active
outputs, audit-only rows, and ignored labels.
