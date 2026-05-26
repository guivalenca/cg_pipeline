# Concept Graph Creation

This package owns the local, manually invoked creation pipeline for Concept
Graph build artifacts. It is isolated from the Companion runtime.

Source code lives in `src/concept_graph_creation`:

- `runtime/`: shared execution infrastructure such as stage contracts, model
  routing, and model clients.
- `stages/`: concrete pipeline stages such as Source Ledger and Workbook Label
  Interpretation.

Named run outputs live outside this package:

```text
cg_pipeline/runs/{run_id}/
  source_ledger.json
  workbook_label_interpretation.json
  lessons/{lesson_id}/self_studies/{self_study_id}/
    extraction_passes/pro-thinking/self_study_extraction.json
    self_study_extraction_set.json
  self_study_extraction_summary.json
  metadata_only_extraction_summary.json
  lessons/{lesson_id}/self_studies/{self_study_id}/metadata_only_extraction.json
  lessons/{lesson_id}/semantic_reduce_candidate_registry.json
  lessons/{lesson_id}/lesson_reconciliation_input.json
  lessons/{lesson_id}/lesson_reconciliation_decision.json
  lessons/{lesson_id}/lesson_reconciliation.json
  lesson_reconciliation_summary.json
  subject_merge_candidate_registry.json
  subject_merge_area_partition_input.json
  subject_merge_area_partition_decision.json
  subject_merge_area_clusters.json
  subject_merge_fine_clustering/{area_id}/subject_merge_fine_clustering_decision.json
  subject_merge_candidate_clusters.json
  subject_cluster_evaluations/{cluster_id}/subject_cluster_evaluation_decision.json
  subject_merge_decision.json
  subject_merge.json
  subject_merge_quality_audit_input.json
  subject_merge_quality_audit.json
  subject_merge_phase5b_repairs/
  dependency_inference.json
  lessons/{lesson_id}/lesson_segment_planner_input.json
  lessons/{lesson_id}/lesson_segment_planner_decision.json
  lessons/{lesson_id}/lesson_segment_concept_orderer_input.json
  lessons/{lesson_id}/lesson_segment_concept_orderer_decision.json
  lessons/{lesson_id}/lesson_segmentation_quality_audit.json
  lessons/{lesson_id}/lesson_segments.json
  lesson_segmentation_summary.json
  critics/
  conciliatory_review.json
  repairs/
  final_graph/
    build_graph.json
    runtime_graph.json
    validation_report.json
```

Current prototype smoke run:

```bash
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-smoke \
  --deterministic-fixture \
  --validation-failure-demo
```

Run phases independently:

```bash
# Phase 2: Source Ledger + Workbook Label Interpretation.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-2 \
  --deterministic-fixture

# Phase 3: Self-study Extraction from an existing Phase 2 run directory.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-3 \
  --phase-3-concurrency 60 \
  --deterministic-fixture

# Phase 3b: Metadata-only Extraction for unavailable Source Bodies from an existing Phase 2 run directory.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-3b \
  --phase-3b-concurrency 10 \
  --deterministic-fixture

# Phase 4: Lesson Reconciliation with Semantic Reduce.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-4 \
  --phase-4-concurrency 6 \
  --phase-4-clustering-route Pro \
  --phase-4-evaluation-route "Pro Thinking" \
  --phase-4-evaluation-batch-size 12 \
  --phase-4-repair-route Flash \
  --phase-4-contextual-repair-route Pro \
  --phase-4b-route "Pro Thinking" \
  --deterministic-fixture

# Phase 5: Subject Merge / Concept Finalization with Semantic Reduce.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-5 \
  --phase-5-model-route "Pro Thinking" \
  --phase-5-evaluation-route "Pro Thinking" \
  --phase-5-repair-route Flash \
  --phase-5-contextual-repair-route "Pro Thinking" \
  --phase-5b-route "Pro Thinking" \
  --phase-5-fine-clustering-concurrency 6 \
  --phase-5-evaluation-concurrency 6 \
  --deterministic-fixture

# Phase 5b only: rebuild Subject Merge quality audit/repair from saved Phase 5
# artifacts, discard previous Phase 5b artifacts, and rerun the model audit.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-5b \
  --phase-5-repair-route Flash \
  --phase-5-contextual-repair-route "Pro Thinking" \
  --phase-5b-route "Pro Thinking" \
  --deterministic-fixture

# Phase 6: Dependency Deferral from saved Phase 5 artifacts.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-6

# Phase 7: Lesson Segmentation And Ordering from saved Phase 5 artifacts.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-7 \
  --phase-7-planner-route "Pro Thinking" \
  --phase-7-orderer-route Pro \
  --phase-7-audit-route "Pro Thinking" \
  --phase-7-quality-repair-route Pro \
  --phase-7-concurrency 6 \
  --deterministic-fixture

# Phase 7b: Knowledge Type Classification from saved Phase 7 artifacts.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-7b \
  --phase-7b-classification-route "Pro Thinking" \
  --phase-7b-audit-route "Pro Thinking" \
  --phase-7b-quality-repair-route Pro \
  --phase-7b-concurrency 6 \
  --deterministic-fixture

# Phase 8: Final Graph Assembly from saved Phase 6, Phase 7, and Phase 7b artifacts.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-8

# Phase 4b only: rebuild Lesson Reconciliation from saved Phase 4a outputs,
# discard previous Phase 4b artifacts, and rerun the quality gate/repairs.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-phase-2 \
  --phase phase-4b \
  --phase-4-repair-route Flash \
  --phase-4-contextual-repair-route Pro \
  --phase-4b-route "Pro Thinking" \
  --deterministic-fixture

# Whole current creation system.
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-all \
  --phase all \
  --phase-3-concurrency 60 \
  --phase-4-concurrency 6 \
  --phase-4-clustering-route Pro \
  --phase-4-evaluation-route "Pro Thinking" \
  --phase-4-evaluation-batch-size 12 \
  --phase-4-repair-route Flash \
  --phase-4-contextual-repair-route Pro \
  --phase-4b-route "Pro Thinking" \
  --phase-5-model-route "Pro Thinking" \
  --phase-5-evaluation-route "Pro Thinking" \
  --phase-5-repair-route Flash \
  --phase-5-contextual-repair-route "Pro Thinking" \
  --phase-5b-route "Pro Thinking" \
  --deterministic-fixture
```

Phase 3 runs one Pro Thinking extraction pass for each usable Self-study by
default. The per-Self-study `self_study_extraction_set.json` packages the
validated pass artifact for Lesson Reconciliation without merging or pruning it.

Phase 3 uses a continuously refilled worker pool. It starts at the requested
concurrency and backs down through `60`, `50`, `40`, `30`, `25`, `20`, `16`,
`14`, `8`, `6`, `4`, and `2` when DeepSeek returns provider-pressure responses
(`429`, `503`, or transient request failures). Only the failed Pro Thinking
Self-study pass is retried.

Phase 3 is resumable. On rerun, any existing Self-study pass artifact that
still satisfies the Stage Contract and matches the expected lesson, Self-study,
and model route is reused. Invalid or missing pass artifacts are regenerated,
so an interrupted or provider-blocked run can continue without redoing completed
work.

Phase 3b runs Metadata-only Extraction for Self-studies whose Source Body is
unavailable. It uses Workbook Metadata and Lesson context only, does not open
URLs or search the web, and marks candidates with `evidence_type:
workbook_metadata`. This branch intentionally does not run Top-down Concept
Extraction.

Phase 4 runs Lesson Reconciliation as two Semantic Reduce steps plus a
deterministic quality gate. First,
Lesson Candidate Clustering groups per-Lesson source-body and metadata-only
candidates with `Pro` and writes `lesson_candidate_clusters.json`. Then Lesson
Cluster Evaluation evaluates validated clusters, batched by
`--phase-4-evaluation-batch-size`, with `Pro Thinking` and assembles the final
`lesson_reconciliation.json`. Deterministic assembly owns lesson-local IDs,
evidence rehydration, source roles, evidence types, anchors, and summaries.
After Phase 4a finishes, Phase 4b writes
`lesson_reconciliation_quality_audit.json` for each reconciled Lesson. The
quality gate deterministically scores review fallback, suspicious pruning,
over-pruning, over-merging, duplicate fragmentation, metadata overreach,
off-lesson accepted material, over-acceptance, and traceability signals.
Lessons with `net_phase4_benefit <= 1` get targeted
`lesson_reconciliation_quality_repair` calls through `--phase-4b-route`; repair
calls receive only the affected candidates plus compact lesson context and must
resolve each target as accepted, merged, or pruned with no final human-review
escape.
If an `over_pruned` repair rechecks every target and confirms all of them as
controlled prunes while no other risk label remains, Phase 4b records the
Lesson as `confirmed` with `over_pruned_confirmed` instead of leaving it as
unrepaired.
`--phase phase-4b` is available when Phase 4a artifacts already exist. It
rebuilds `lesson_reconciliation.json` from `lesson_reconciliation_decision.json`,
removes previous `lesson_reconciliation_quality_audit.json` and
`phase4b_repairs/`, then reruns only Phase 4b.
Phase 4 has separate bounded worker queues for clustering and evaluation via
`--phase-4-clustering-concurrency` and `--phase-4-evaluation-concurrency`;
both default to `--phase-4-concurrency`. Targeted format repair uses `Flash`,
and contextual repair uses `Pro`. Existing valid Phase 4 artifacts are reused
unless `--phase-4-clean` is supplied.

Phase 5 uses task-specific Subject Merge prompts at Subject scope. It consumes
validated Lesson Reconciliation artifacts and runs three model-led steps:

1. Area Partition groups all lesson-local candidates into broad subject areas.
2. Fine Clustering runs one call per area and proposes tight same-concept
   candidate clusters.
3. Cluster Evaluation runs one call per non-singleton cluster and decides
   whether to merge or keep candidates separate.

Singleton clusters pass through deterministically. The final
`subject_merge.json` uses deterministic stable Concept IDs and rolls up Lesson
Reconciliation provenance. Phase 5 requires a complete Phase 4 summary before
it will run. Existing valid Phase 5 artifacts are reused unless
`--phase-5-clean` is supplied.

Phase 5 model routing is split by task. Area Partition and Fine Clustering
default to `--phase-5-model-route`, which defaults to `Pro Thinking`, but can
be overridden separately with `--phase-5-area-partition-route` and
`--phase-5-fine-clustering-route`. Cluster Evaluation defaults to
`Pro Thinking`; format repair uses `Flash`; contextual repair uses
`Pro Thinking`. In practice, Area Partition may need `Pro` as a fallback when
`Pro Thinking` returns empty provider responses.

Phase 5b reruns only the Subject Merge quality gate when Phase 5 artifacts
already exist. It deletes previous `subject_merge_quality_audit*.json`,
`subject_merge_phase5b_repairs/`, and raw Phase 5b outputs, then runs a
`Pro Thinking` quality audit. The audit receives current concepts, compact
source candidate context, prior merge attempts, and conservative review signals
for possible missed obvious merges. Deterministic code is limited to hard
bookkeeping guardrails such as missing assignments and provenance loss; semantic
judgment belongs to the model audit. Targeted repairs are routed through
`--phase-5b-route` and are checked by a second model audit. If the second audit
is clean, the result is recorded as `repaired`; if a repair creates a new
problem, the run records `repair_unstable` instead of looping indefinitely.

Phase 6 Dependency Deferral is deterministic. It writes
`dependency_inference.json` with `deferred: true` and an explicit empty
`dependency_edges` list because v0 trusts the university Lesson order instead of
inferring global prerequisite edges.

Phase 7 Lesson Segmentation And Ordering runs per Lesson and can process
Lessons concurrently. The Planner uses `Pro Thinking` to choose Segment
boundaries and Segment order from only Lesson ID, Lesson title, and stable
Lesson Concepts with label, teaching description, and Coverage Criteria. The
Concept Orderer uses `Pro` to order Concepts within each Segment without moving
Concepts between Segments. A `Pro Thinking` quality audit checks the complete
Lesson segmentation while staying blind to other Lessons. If the audit requires
repair, a targeted `Pro` repair runs and the audit reruns. The runtime artifact
`lesson_segments.json` stays clean: deterministic code assigns
`segment_001`-style IDs and `instructional_role: "teach"`.

Phase 7b Knowledge Type Classification runs one `Pro Thinking` classification
call per Lesson Segment. It uses the `knowledge_type` taxonomy from
`prompts/system_prompt.txt`, writes a separate
`knowledge_type_classification_summary.json` overlay, audits the labels, and can
run one targeted repair pass. It does not mutate `subject_merge.json`.

Phase 8 Final Graph Assembly is deterministic. It consumes `subject_merge.json`,
`dependency_inference.json`, `lesson_segmentation_summary.json`,
`knowledge_type_classification_summary.json`, and per-Lesson
`lesson_segments.json` artifacts. It writes run-local final artifacts under
`final_graph/`: `build_graph.json` keeps provenance and source metadata for
audit, `runtime_graph.json` strips build-only metadata and keeps lesson-based
Segments, and `validation_report.json` records blockers and warnings. It never
promotes or writes into `reference/courses/...`.
