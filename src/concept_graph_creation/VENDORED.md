# Vendored Lesson creation stages

The creation runtime and retained stage implementations were lifted from
`claude/improvements` at commit `17ab9d93c`.

Retained stages:

- source-local Candidate Concept extraction;
- Lesson Reconciliation;
- Dependency Deferral;
- Lesson Segmentation;
- knowledge-type classification;
- Final Assembly.

`source_ledger.py` supplies compatibility path helpers. The
`metadata_only_extraction.py` compatibility module contains only the legacy
artifact validator required by Lesson Reconciliation; its generation stage and
prompt are omitted. Neither support module is registered as a Lesson Build
stage. Subject Merge is not vendored;
`lesson_reconciliation_passthrough.py` supplies its deterministic single-Lesson
output shape until cross-Lesson merging is introduced.

Intentional changes from the source commit are limited to:

- stable Lesson identity in generated Concept IDs;
- per-Lesson ledger slicing and fingerprints;
- deterministic reconciliation passthrough;
- explicit missing/unsupported knowledge-type failures;
- prompt file hashes in execution identity; and
- Brazilian Portuguese prose-output instructions.

The worker import guard accepts `concept_graph_creation.stages.*` so the stage
files keep their original package namespace.
