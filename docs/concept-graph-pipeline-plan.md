# Autonomous Concept Graph Pipeline Plan

This plan defines how to turn a faculty XLSX and its assigned Self-studies into
a trustworthy `concept_graph.json` for the Companion.

The pipeline is local-first and manually invoked. It may live under
`cg_pipeline/` in this repo for v1, while staying isolated from the Companion
runtime. Remote OpenClaw on the VPS is used only when browser/operator
acquisition is needed.

## Core Architecture

The pipeline has four execution layers:

```text
Local deterministic code
  workbook parsing, normal fetches, run store, hashes, schemas, validators,
  artifact export, promotion candidates

Local LangGraph orchestration
  run state, conditional routing, AI cleaning, AI annotation, extraction,
  reconciliation, critics, repair, resumability

Remote OpenClaw acquisition
  Sophia / Minha Biblioteca, authenticated browser work, dynamic pages,
  screenshots, page images, manual login/MFA resume

Companion runtime
  consumes only promoted graph artifacts
```

The Companion app must not request graph generation during normal runtime and
must not import source acquisition, cleaning, synthesis, or critic modules.

LangGraph can coordinate every phase, including deterministic nodes. That does
not make deterministic work agentic. It only gives the run one state machine and
allows source-acquisition and repair routing:

```text
deterministic fetch fails because browser/auth is required
  -> remote OpenClaw acquisition

AI cleaning finds source capture incomplete
  -> reacquire source

validation finds graph blockers
  -> repair or stop without trusted export

critic reports major structure issue
  -> conciliatory review -> repair -> validation
```

LangGraph state should store artifact references, hashes, statuses, costs, and
routing decisions. Raw credentials, cookies, browser profile paths, and bulky
source text should stay out of checkpoint state.

## Local And VPS Placement

Recommended v1 local placement:

```text
cg_pipeline/
  schemas/
  pipeline/
  prompts/
  fixtures/
  tests/
  README.md

cg_pipeline/runs/{run_id}/ or configured run root
  source_ledger.json
  workbook_label_interpretation.json
  self_study_extraction_summary.json
  metadata_only_extraction_summary.json
  top_down_concept_extraction_summary.json
  lessons/
    {lesson_id}/self_studies/{self_study_id}/
      extraction_passes/pro-thinking/self_study_extraction.json
      self_study_extraction_set.json
      metadata_only_extraction.json
    {lesson_id}/top_down_concept_extraction.json
    {lesson_id}/lesson_reconciliation.json
  critics/
  repairs/
  final_graph/
    build_graph.json
    runtime_graph.json
    validation_report.json

configured cache/tmp root
  cache/
  tmp/
```

The exact artifact root can be configured. It should not be committed by
default. The pipeline writes final artifacts into the run directory only;
copying a Runtime Graph Export into Companion reference data is a later Manual
Promotion step.

The current creation prototype still has a compatibility wrapper named
`self_study_extraction_set.json`. Going forward, that set should contain exactly
one source-body pass: `Pro Thinking`. It should not imply three model opinions
or a later route-merge stage.

OpenClaw remains installed on the VPS. The safest integration is not a public
gateway by default; it is a file-contract call over SSH tunnel, SSH command,
SFTP, rsync, or a private network with authentication.

## Canonical Terms

**Lesson** means the scheduled university meeting extracted from the
spreadsheet. It replaces the old `day_presets` language.

**Self-study** means an assigned preparatory resource for a Lesson, such as a
video, article, book excerpt, documentation page, or exercise list.

**Assigned Scope** means the exact part of a Self-study that the spreadsheet
assigns. For book-library resources, only the Assigned Scope counts as coverage.

**Concept** means a single teachable idea small enough that the Companion can
verify understanding with one to three focused questions.

**Coverage Criterion** means an observable condition that tells the Companion
what evidence is needed before treating a Concept as covered.

**Common Misconception** means a predictable wrong mental model or error pattern
for a Concept.

**Concept Dependency** means a prerequisite relationship between Concepts.
Dependency types are `blocking`, `hard`, and `soft`.

**Lesson Segment** means a coherent teaching unit inside a Lesson. It groups
related Concepts so the Companion can teach naturally.

**Instructional Role** means the segment's planned pedagogical job. In v0
Lesson Segmentation, every emitted Segment is deterministically marked `teach`.
`overview`, `practice`, `review`, and `repair` are reserved for later
runtime-aware work that combines graph structure with student state.

**Pipeline Review Artifact** means a human-readable audit file explaining
source acquisition, cleaning, annotation, extraction, reconciliation,
validation, exclusions, critic findings, and repair decisions.

## Output Artifacts

The pipeline emits a clean runtime graph plus separate review artifacts.

Runtime graph:

```text
cg_pipeline/runs/{run_id}/final_graph/runtime_graph.json
```

Recommended review artifacts inside the run directory:

- `resource_quality_report.md`
- `self_study_extraction_report.md`
- `top_down_expectation_report.md`
- `lesson_reconciliation_report.md`
- `dependency_report.md`
- `critic_report.md`
- `repair_report.md`
- `validation_report.md`
- `release_note.md`

The runtime graph should not include heavy intermediate reasoning, long source
excerpts, browser traces, or full resource text.

## Runtime Concept Graph Content

At the Subject level, the graph contains Subject metadata, Concepts, Concept
Dependencies, and Lessons.

At the Lesson level, it contains date, title, professor if available,
description, related subjects, Self-studies, Lesson Segments, and ordered
Concepts.

At the Lesson Segment level, it contains label, Instructional Role, ordered
Concepts, and optional teaching-flow notes.

At the Concept level, it contains Concept ID, label, knowledge type, optional
difficulty, machine-facing teaching description, Coverage Criteria, Common
Misconceptions when useful, and lightweight Concept Provenance.

At the dependency level, the schema can contain prerequisite Concept, dependent
Concept, dependency type, short reason, and source label. In v0, dependency
edges are intentionally empty; lesson order and Lesson Segments provide the
trusted teaching sequence.

## Section 1: Source Corpus

Phases 1-4 build the reliable source-corpus half of the system: XLSX ingestion,
resource acquisition, AI Resource Cleaning, and AI Resource Annotation. The
concrete implementation checklist lives in
[Concept Graph Section 1 Implementation](concept-graph-section-1-implementation.md).

## Source Quality Gates

Section 1 owns these hard gates before Concept extraction:

- Every XLSX Self-study row has an acquisition result.
- Access blockers are reported, not bypassed.
- Source identity matches the XLSX row.
- Book-library coverage is restricted to Assigned Scope.
- Text/OCR/transcript quality is extraction-grade.
- Browser acquisition proves it saw content, not only an app shell.
- Provenance bundles include raw artifact hashes, quality reports, and redaction
  confirmation.
- Source prompt injection is treated as inert source data.

## Current Routing Decision

Evaluation of the creation pipeline showed that Pro Thinking outputs are much
higher quality than chat and Pro outputs. Pro sometimes adds extra granularity,
but not enough to justify running multiple extraction routes and reconciling
their disagreements.

The v0 graph-synthesis path is therefore Pro Thinking-first. The pipeline
should not continue the Route Cleanup and Source Merge design that compared
chat, Pro, and Pro Thinking outputs for the same Self-study. That branch of
work was checkpointed on `feat/concept-graph-pipeline-2` as commit `e275ab4`
(`Checkpoint abandoned route merge path`) for historical reference. The clean
continuation branch restarts from `a8ef08e`.

Practical consequences:

- Do not build or maintain `route_cleanup` as a required graph-synthesis phase.
- Do not build or maintain `source_merge` as a cross-route comparison phase.
- Do not run chat or Pro extraction merely to increase recall.
- Use `Flash` for format-only repair when the Stage Contract shape is wrong.
- Use `Pro` as a pragmatic fallback for stages where `Pro Thinking` repeatedly
  returns no usable provider output, especially broad Subject Merge area
  partitioning.
- Spend the saved complexity budget on finalization, dependencies,
  segmentation, validation, and critic/repair quality.
- Keep artifact contracts, validation, resumability, and model-call retry
  patterns from the prototype where they remain useful.

Current implementation context:

- The implemented creation CLI supports `phase-2`, `phase-3`, `phase-3b`,
  `phase-4`, `phase-4b`, `phase-5`, `phase-5b`, and `all`.
- Source-body extraction is one Pro Thinking pass per usable Self-study.
- Metadata-only Extraction exists for unavailable Source Bodies. Top-down
  Concept Extraction is still deferred.
- Lesson Reconciliation is implemented as clustering, cluster evaluation,
  deterministic assembly, and a Phase 4b quality gate/repair pass.
- Subject Merge is implemented as area partitioning, fine clustering,
  per-cluster evaluation, deterministic assembly, and a Phase 5b Pro Thinking
  quality audit/repair pass.
- Dependency Deferral, Lesson Segmentation And Ordering, and later graph
  assembly stages are not implemented yet.

## Current Implementation Phases

Phase 2 Source Ledger And Workbook Label Interpretation:

- Parses the workbook and index into a Source Ledger for one Subject.
- Interprets Workbook Related Labels into active v0 patterns.

Phase 3 Self-study Extraction:

- One primary Pro Thinking Concept Extractor per usable Self-study.
- No chat/Pro comparison pass or route override in the v0 pipeline.
- Optional follow-up extraction is allowed only for a clearly scoped repair
  using Pro Thinking, not as a routine route ensemble.
- Outputs candidate Concepts, Coverage Criteria, Common Misconceptions, local
  dependencies, and source-grounded rationale.
- Writes source-body candidates with compact, source-local IDs and provenance
  sufficient for lesson reconciliation.

Phase 3b Metadata-only Extraction:

- Uses Pro Thinking by default.
- Metadata-only Extraction runs only for Self-studies whose source body is
  unavailable. It uses workbook title, description, assigned scope, required
  flag, grade weight, related labels, and acquisition failure notes.
- Metadata-only candidates are weaker than source-body candidates until Lesson
  Reconciliation accepts them.

Phase 4 Lesson Reconciliation:

- Runs per Lesson as clustering plus cluster evaluation.
- Lesson Candidate Clustering defaults to `Pro`.
- Lesson Cluster Evaluation defaults to `Pro Thinking` and can batch multiple
  candidate clusters per call.
- Consumes Pro Thinking source-body candidates plus optional metadata-only
  candidates.
- Collapses duplicates and near-duplicates inside the Lesson while preserving
  candidate provenance.
- Prunes low-teaching-value, incidental, too-narrow, too-broad, unrelated, or
  unsupported metadata candidates with controlled reasons.
- Keeps Self-study-derived Concepts by default unless there is an explicit
  pruning or merge reason.
- Emits reconciled lesson-local candidate IDs, not final stable Concept IDs.
- Does not run Route Cleanup or Source Merge.

Phase 4b Lesson Reconciliation Quality Gate:

- Rerunnable independently from saved Phase 4a artifacts.
- Deterministically audits each Lesson for review fallback, suspicious pruning,
  over-pruning, over-merging, duplicate fragmentation, metadata overreach,
  off-lesson accepted material, over-acceptance, and traceability risks.
- Sends targeted repair calls through `--phase-4b-route` when quality requires
  repair.
- Format repair uses `Flash`; contextual repair currently defaults to `Pro`.

Phase 5 Subject Merge:

- Consumes every validated Lesson Reconciliation artifact after Phase 4
  completes.
- Area Partition groups lesson-local candidates into broad Subject areas.
- Fine Clustering runs one model call per area and proposes tight candidate
  clusters.
- Cluster Evaluation runs one model call per non-singleton cluster and decides
  same-concept reuse versus separate subject concepts.
- Singleton clusters pass through deterministically.
- Deterministic assembly writes `subject_merge.json`, stable Concept IDs, and
  rolled-up Lesson Reconciliation provenance.

Phase 5b Subject Merge Quality Audit:

- Rerunnable independently from saved Phase 5 artifacts.
- Runs a Pro Thinking quality audit over the current subject concepts, compact
  source-candidate context, prior merge attempts, and conservative review
  signals for missed obvious merges.
- Deterministic code supplies only hard bookkeeping guardrails such as missing
  assignments and provenance loss.
- The model owns semantic judgments about over-merges, residual duplicates, and
  missed obvious merges.
- Targeted repairs are checked by a second Pro Thinking audit. Clean repaired
  output is marked `repaired`; unstable repair output is marked
  `repair_required` with `repair_unstable`.

## Planned Next Stages

Dependency Deferral:

- Emits `dependency_inference.json` with an explicit empty edge list.
- Records that dependency inference is deferred because the university Lesson
  order is the trusted prerequisite structure for v0.
- Keeps Workbook Related Label prerequisite hints available for audit and
  future exam-study/adaptive-remediation work, but does not convert them into
  edges.

Lesson Segmentation And Ordering:

- Runs per Lesson and stays blind to other Lessons.
- Uses only Lesson ID, Lesson title, and stable Lesson Concepts with label,
  knowledge type, teaching description, and Coverage Criteria.
- Groups Lesson Concepts into coherent teaching-flow units, not source-text
  sections.
- Ensures each Lesson Concept appears in exactly one Segment.
- Targets one to four Concepts per Segment; five or more is a warning and
  usually indicates the Segment should split.
- Uses `Pro Thinking` for Segment grouping and Segment order, `Pro` for
  ordering Concepts within each Segment, `Pro Thinking` for quality audit, and
  `Pro` for targeted repair when the audit rejects the result.
- Adds deterministic Segment IDs and `instructional_role: "teach"` after model
  calls; the model does not emit either field.

Build Graph Assembly:

- Separates code-defined fields from LLM-defined fields.
- Normalizes stable IDs deterministically.
- Produces labels, display codes, machine-facing descriptions, Coverage
  Criteria, provenance, ordered Lesson Segments, and the empty v0 dependency
  edge list.

Deterministic Validation:

- Blocks structural and source-trust failures.
- Emits warnings for quality concerns that critics should inspect.

Mandatory Critic Passes:

- Coverage Critic.
- Granularity Critic.
- Pedagogy Critic.
- Source/Security Critic.

Critics write independent reports from the frozen draft graph and relevant
artifacts. They do not mutate the graph directly.
Dependency Critic is deferred while v0 dependency edges are intentionally
empty.

Repair Loop:

- Conciliatory Agent decides which criticisms are valid.
- Repair Agent applies accepted changes.
- Validation reruns after repair.
- Major repairs may rerun selected critics.

Runtime Graph Export:

- Emits the run-local runtime graph from the validated Build Graph Artifact.
- Does not emit trusted output if blocking validation remains.

## Deterministic Validation Blockers

Blocking errors:

- A Lesson has no Concepts.
- A Lesson Concept is missing from all Lesson Segments.
- A Concept has no Coverage Criteria.
- A v0 dependency edge list is non-empty.
- Duplicate Concepts exist with no merge or exclusion decision.
- An assigned Self-study could not be fetched, parsed, OCRed, cleaned,
  annotated, or transcribed after fallback.
- A book-library Self-study includes unassigned pages as coverage.
- Provenance or redaction integrity fails.

Warnings:

- A Lesson Segment is unusually large.
- A Lesson has unusually many Concepts.
- Concept Provenance is low confidence.
- A non-empty Common Misconception is unsupported by source evidence.
- Top-down candidate Concepts are absent from Self-study extraction and not
  accepted by Lesson Reconciliation.
- A Self-study-derived Concept was excluded as incidental or unrelated.
- A video transcript passed only after STT fallback.
- A Segment label is vague or too long.

## Model Routing

The primary semantic model route in the creation pipeline is:

- `Pro Thinking`: `deepseek-v4-pro` with thinking enabled and
  `reasoning_effort=high`.

Two additional aliases are intentionally still available:

- `Flash`: `deepseek-v4-flash`, used for format-only repair.
- `Pro`: `deepseek-v4-pro` without thinking, used for cheaper or more reliable
  broad clustering when Pro Thinking repeatedly returns no usable provider
  output.

The legacy DeepSeek model names `deepseek-chat` and `deepseek-reasoner` should
not be used as design language for this pipeline.

Recommended v0 routing:

- Workbook Label Interpretation: `Pro Thinking`.
- Self-study Extraction: one `Pro Thinking` pass per usable Self-study.
- Metadata-only Extraction: `Pro Thinking`.
- Lesson Candidate Clustering: `Pro`.
- Lesson Cluster Evaluation: `Pro Thinking`.
- Lesson Reconciliation Phase 4b quality repair: `Pro Thinking`.
- Subject Merge Area Partition: `Pro Thinking` by default, `Pro` fallback when
  provider behavior requires it.
- Subject Merge Fine Clustering: `Pro Thinking`.
- Subject Merge Cluster Evaluation: `Pro Thinking`.
- Subject Merge Phase 5b quality audit and semantic repair: `Pro Thinking`.
- Dependency Deferral: deterministic code only.
- Lesson Segmentation And Ordering: Planner `Pro Thinking`, Concept Orderer
  `Pro`, Quality Audit `Pro Thinking`, targeted Quality Repair `Pro`.
- Critic Passes: `Pro Thinking`.
- Conciliatory Review: `Pro Thinking`.
- Format Repair: `Flash`.
- Contextual Repair: same model family as the owning stage unless a specific
  route override is configured.
- Final Assembly and validation: deterministic code only.

Most graph-generation agents should not browse the open web. Their authority is
the XLSX plus assigned Self-studies. Web access is for source retrieval,
provider documentation, troubleshooting inaccessible resources, or explicit
operator-approved research tasks.

## V0 Post-Extraction Source Policy

For v0, graph synthesis may start from the organized extraction markdown plus
workbook/index metadata without separate AI cleaning or annotation artifacts.

Unavailable or blocked full sources are not automatically ignored. Their
workbook title, description, related subjects, required flag, grade weight, and
source identity still contribute lesson-intent evidence and gap reporting. They
must not produce source-body concepts, but they can inform top-down expectation,
missing-source reports, and cautious bridge review.

Activity-only Self-studies should be excluded from concept extraction only when
they provide no usable teaching content in the linked source, title, or
description. Grade weight signals importance, but does not by itself create a
Concept.

## Cost Controls

- Cache fetched resources, OCR, transcripts, cleaned sources, annotations, and
  extraction outputs by source hash.
- Fetch captions before STT.
- Run secondary extractors only for dense or high-risk resources.
- Run critic passes on the draft graph, not every raw chunk.
- Keep provenance and source excerpts out of runtime prompts.
- Bound each run by max dollars, tokens, STT minutes, OCR pages, retries, and
  repair cycles.
- Budget exhaustion stops the run with a clear report rather than silently
  lowering graph quality.

## V1 Completion Criteria

V1 is complete when the local script can take a real XLSX such as
`si_mod6.xlsx`, collect all Self-studies for one Subject, clean and annotate
sources, generate a final Concept Graph, produce review artifacts, pass
deterministic validation, pass mandatory critic repair, and export a graph that
Companion can use through an enriched text-first summary.

The output is acceptable when source-grounded Concepts are not silently dropped,
every final Concept has Coverage Criteria, Lessons are organized into ordered
Lesson Segments, dependency edges are explicitly empty for v0, and the
Companion receives enough teaching detail to avoid shallow broad topics.

## V2 And Later

- Dynamic Session Plan and Session Focus runtime.
- Boundary-only Focus Transition Signal.
- Evidence Ledger persistence.
- First-class Practice Contexts for activities and assignments that apply
  Concepts without introducing new teachable Concepts. In v0, activity-only
  sources may be excluded or treated as weak lesson evidence instead of becoming
  graph objects.
- Selective Companion Simulation for dense or risky Lessons.
- Empirical validation from student outcomes.
- Possible extraction of `cg_pipeline/` into a standalone repository if it
  becomes operationally useful.
