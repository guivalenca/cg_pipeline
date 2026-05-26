# Concept Graph Pipeline Context

This context defines the language for turning assigned course materials into a
runtime Concept Graph. It is local to `cg_pipeline`; the root `CONTEXT.md`
continues to describe the Companion runtime domain.

The pipeline inherits the root meanings of **Course**, **Module**, **Subject**,
**Concept**, **Concept Graph**, **Session**, **Concept Map**, **Confidence**, and
**Concept Status**. This file only adds generation-side terms that are not part
of the Companion runtime glossary.

## Language

### Source And Scope

**Lesson**:
A scheduled university meeting from the workbook that anchors a set of assigned Self-studies.
_Avoid_: class, day preset

**Self-study**:
An assigned preparatory resource for a Lesson, such as an article, video, book excerpt, documentation page, or activity.
_Avoid_: source when referring to the assignment row itself

**Source Body**:
The acquired readable content of a Self-study, usually markdown from article, book, or video extraction.
_Avoid_: source when referring to workbook metadata

**Referenced Visual**:
An image, diagram, screenshot, or video frame referenced by a Source Body and treated as part of the assigned source context.
_Avoid_: external research image

**Workbook Metadata**:
The title, description, related subjects, required flag, grade weight, URL, and source identity recorded in the workbook for a Self-study.
_Avoid_: source body

**Workbook Related Labels**:
The semicolon-separated labels from the workbook's `Related subjects` column, used as curriculum-intent hints rather than Companion runtime Subjects.
_Avoid_: related subjects unqualified, related topics

**Workbook Label Pattern**:
The observed role a Workbook Related Label plays in context, such as lesson cluster, prerequisite hint, application area, or adjacent-domain signal.
_Avoid_: concept type

**Workbook Label Interpretation**:
A pre-dependency classification of Workbook Related Labels into the small set of patterns that v0 actively uses.
_Avoid_: concept extraction

**Extraction Corpus**:
The post-acquisition set of usable Source Bodies plus the explicit list of blocked or unavailable Source Bodies.
_Avoid_: clean corpus, annotated corpus

**Source Ledger**:
The run-level inventory that connects Lessons, Self-studies, Source Bodies, Workbook Metadata, warnings, hashes, and exclusions.
_Avoid_: annotation

**Unavailable Source Body**:
A Self-study whose full linked content could not be acquired or used, while its Workbook Metadata may still provide lesson-intent evidence.
_Avoid_: discarded source

**Metadata-only Extraction**:
A constrained extraction path for a Self-study with an Unavailable Source Body, using only Workbook Metadata and clearly marking the result as metadata-backed.
_Avoid_: source-body extraction

**Evidence Type**:
The support class for a candidate or accepted Concept, especially `source_body` or `workbook_metadata`.
_Avoid_: source role

**Activity-only Self-study**:
A Self-study whose assignment asks the student to do a task but provides no usable teaching content in the Source Body, title, or description.
_Avoid_: activity concept

### Concepts And Evidence

**Candidate Concept**:
A source-local teachable idea proposed by a per-Self-study extractor before merging, deduplication, or final ID assignment.
_Avoid_: final concept

**Concept**:
A final teachable idea small enough for the Companion to check with one to three focused questions.
_Avoid_: topic, activity

**Coverage Criterion**:
An observable student behavior that tells the Companion what evidence would count as covering a Concept in a session.
_Avoid_: objective, learning goal, mastery rule

**Common Misconception**:
A recurring wrong mental model for a Concept, included in v0 only when explicitly grounded in a source.
_Avoid_: guessed misconception

**Concept Provenance**:
Lightweight structured evidence showing which Self-studies, source roles, or inferred reasons support a Concept.
_Avoid_: citation dump, chain of thought

**Source Anchor**:
A lightweight locator such as book page, video timestamp, markdown heading, or article section that helps find the source support without copying the source text.
_Avoid_: excerpt

**Source Role**:
The way a Source Body supports a Candidate Concept, such as introducing, explaining, demonstrating, implementing, practicing, referencing, warning, or incidental mention.
_Avoid_: confidence

**Extraction Reason**:
A short source-grounded explanation for why Self-study Extraction included a Candidate Concept.
_Avoid_: centrality label

**Source-local Connector Candidate**:
A Candidate Concept proposed by Self-study Extraction because it connects important ideas inside one Source Body's own teaching flow.
_Avoid_: bridge concept

**Pipeline-inferred Concept**:
A Concept not directly extracted from one Source Body but accepted because it connects source-grounded Concepts or repairs a pedagogical gap.
_Avoid_: generic background

**Bridge Concept**:
A Pipeline-inferred Concept whose purpose is to make the teaching flow between other Concepts coherent.
_Avoid_: filler concept

**Practice Context**:
A future graph-adjacent object for an assignment or activity that applies Concepts without becoming a Concept itself.
_Avoid_: activity concept

### Output Artifacts

**Build Graph Artifact**:
The metadata-rich final pipeline artifact containing the accepted graph content plus provenance, source roles, exclusions, confidence signals, and review support.
_Avoid_: runtime graph, final concept graph

**Runtime Graph Export**:
The lean Concept Graph consumed by the Companion runtime, containing only the curriculum content needed for tutoring.
_Avoid_: build graph, metadata graph

**Dependency Projection**:
The deterministic Final Assembly step that converts canonical flat dependency edges from the Build Graph Artifact into nested runtime dependency objects on each Concept.
_Avoid_: dependency inference

**Dead Runtime Field**:
A field included in the Runtime Graph Export schema but intentionally left empty in v0 until a grounded producer exists.
_Avoid_: placeholder content

**Graph Schema Version**:
The version of the JSON structure used by a Build Graph Artifact or Runtime Graph Export.
_Avoid_: graph content version

**Graph Content Version**:
The manually bumped version of the curriculum content for a Subject's Concept Graph.
_Avoid_: schema version

**Manual Promotion**:
The human-triggered step that copies an accepted Runtime Graph Export into Companion reference data.
_Avoid_: automatic deployment

**Legacy Day Preset**:
The old Companion runtime grouping for a lesson-like session plan, intentionally not emitted by the v0 pipeline.
_Avoid_: lesson

### Synthesis Stages

**Top-down Concept Extraction**:
A lesson-level pass that proposes Candidate Concepts from Lesson metadata, Self-study titles/descriptions, unavailable-source metadata, and lesson-cluster labels.
_Avoid_: source-body extraction

**Self-study Extraction**:
The source-local pass that extracts Candidate Concepts and raw Coverage Criteria from one Self-study without merging, deduping, or inventing bridge Concepts.
_Avoid_: reconciliation

**Lesson Reconciliation**:
The lesson-local pass that merges source-grounded Candidate Concepts, removes incidental material, and preserves important lesson content.
_Avoid_: subject merge

**Candidate Pruning Reason**:
A controlled reason for removing a Candidate Concept during reconciliation.
_Avoid_: silent deletion

**Pedagogical Story Review**:
The pass that asks whether a Lesson teaches coherently and proposes Bridge Concepts when the flow has a real gap.
_Avoid_: storytelling, narrative writing

**Subject-level Merge**:
The pass that deduplicates Concepts across Lessons and decides whether repeated material is the same Concept, a revisit, or a deeper Concept.
_Avoid_: lesson reconciliation

**Same-Concept Reuse**:
The decision to use one Concept ID across multiple Lessons or Segments only when the teachable idea is literally the same.
_Avoid_: similarity merge

**Deeper Revisit**:
A later treatment of related material that requires a stronger or different understanding than the earlier Concept.
_Avoid_: same concept

**Dependency Inference**:
The future pass that adds typed prerequisite relationships after a concrete
runtime need exists, such as exam-study planning or adaptive remediation.
_Avoid_: background expansion

**Dependency Deferral**:
The v0 pass that explicitly emits no dependency edges because the university
Lesson order is the trusted prerequisite structure.
_Avoid_: failed dependency inference

**Dependency Type**:
One of `blocking`, `hard`, or `soft`, describing how strongly one Concept depends on another.
_Avoid_: custom dependency labels

**Lesson Segment**:
A coherent teaching unit inside a Lesson that groups ordered Concepts for Session Plan and Session Focus.
_Avoid_: section when referring to source text

**Instructional Role**:
The pedagogical job of a Lesson Segment. V0 Lesson Segmentation deterministically
emits only `teach`; overview, practice, review, and repair are future
runtime-aware roles.
_Avoid_: concept type

**Critic Finding**:
An independent review note about coverage, granularity, dependency, pedagogy, source grounding, or security.
_Avoid_: repair

**Critic Pass**:
A separate review run focused on one concern such as coverage, granularity, dependency quality, pedagogy, or source grounding.
_Avoid_: combined critic

**Conciliatory Review**:
The pass that decides which Critic Findings are valid before any graph repair happens.
_Avoid_: critic

**Repair**:
The pass that applies accepted Conciliatory Review decisions to the Build Graph Artifact or routes work back to an earlier synthesis stage.
_Avoid_: critic review

**Format Repair**:
A narrow non-semantic retry that fixes malformed or schema-invalid agent output without changing graph meaning.
_Avoid_: semantic repair

**Stage Contract**:
The schema and validation rules that an agent artifact must satisfy before any downstream stage can consume it.
_Avoid_: prompt format suggestion

**Validation Blocker**:
A deterministic validation failure that prevents Final Assembly or runtime export.
_Avoid_: warning

**Final Assembly**:
The deterministic step that emits the promoted graph, compatibility fields, display codes, and review reports after accepted repairs.
_Avoid_: final agent

### Identity

**Candidate ID**:
A temporary handle for a Candidate Concept before final graph promotion.
_Avoid_: concept ID

**Concept ID**:
The stable machine identity of a promoted Concept, preferably a readable slug plus a short hash based on canonical meaning.
_Avoid_: display code, ordinal ID

**Display Code**:
A pretty ordered label for humans, regenerated at Final Assembly and not used as persistent identity.
_Avoid_: concept ID

## Relationships

- A pipeline run targets exactly one root-defined **Course** / **Module** /
  **Subject** and produces one **Concept Graph** for that Subject.
- A **Lesson** has zero or more **Self-studies**.
- A **Self-study** has **Workbook Metadata** and may or may not have a usable **Source Body**.
- **Workbook Metadata** may include **Workbook Related Labels** that inform top-down expectation, dependency hints, and bridge review.
- A **Workbook Related Label** may have different **Workbook Label Patterns** and should not be treated as a Concept or dependency edge without interpretation.
- **Workbook Label Interpretation** feeds Top-down Concept Extraction with
  lesson-cluster labels. Prerequisite hints are recorded for audit and future
  dependency work, but do not create v0 dependency edges.
- **Top-down Concept Extraction** produces lesson-intent Candidate Concepts
  that are weaker than source-body candidates until Lesson Reconciliation
  accepts them.
- The **Extraction Corpus** contains usable **Source Bodies** and explicit **Unavailable Source Bodies**.
- The **Source Ledger** connects every **Self-study** to its Lesson, Source Body status, warnings, and provenance inputs.
- **Metadata-only Extraction** may run for an **Unavailable Source Body**, but
  it uses the same candidate schema as normal Self-study Extraction and marks
  candidates with Evidence Type `workbook_metadata`.
- **Self-study Extraction** produces **Candidate Concepts**, raw **Coverage Criteria**, and **Source Roles**.
- **Self-study Extraction** may inspect **Referenced Visuals** from the Source
  Body, but must not browse for unrelated topic research or use outside
  material as concept evidence.
- **Self-study Extraction** records an **Extraction Reason** for each
  Candidate Concept instead of assigning central, supporting, or borderline
  labels.
- Each **Extraction Reason** includes a short paraphrase or grounding of the
  supporting source signal and explains why the Candidate Concept is the right
  granularity: not too specific and not too general.
- **Self-study Extraction** may produce **Source-local Connector Candidates**,
  but not cross-source **Bridge Concepts**.
- **Self-study Extraction** does not produce teaching order or dependency
  edges; ordering belongs to **Lesson Segment** generation and v0 prerequisite
  edge inference is deferred.
- **Lesson Reconciliation** turns lesson-local **Candidate Concepts** into lesson-local draft Concepts.
- **Lesson Reconciliation** may remove **Candidate Concepts**, but every
  removal needs a **Candidate Pruning Reason**.
- **Pedagogical Story Review** may propose **Bridge Concepts**, but cannot silently promote generic background.
- **Subject-level Merge** produces the subject-wide Concept inventory before
  **Dependency Deferral** and **Lesson Segment** generation.
- v0 **Dependency Deferral** emits an explicit empty dependency artifact. Lesson
  sequencing comes from ordered Lesson Segments, not prerequisite edges.
- Future **Dependency Inference** may use `blocking`, `hard`, and `soft`, but
  v0 does not infer those edges.
- Future `blocking` dependencies require stronger justification than `hard` or
  `soft` and should be rare to avoid trapping the Companion.
- **Dependency Inference** does not create Concepts. Missing prerequisite
  Concepts are identified by critics and handled through repair when the future
  pass is enabled.
- **Critic Passes** run as separate prompts and separate artifacts by concern,
  not as one combined critic.
- **Conciliatory Review** produces accepted findings and a repair plan; **Repair**
  applies those decisions. These are separate responsibilities.
- **Repair** routes accepted structural fixes back to the stage that owns the
  decision when possible; direct repair is reserved for small local edits.
- Every agent artifact must satisfy its **Stage Contract** immediately after
  output. One narrow **Format Repair** retry may fix malformed output; semantic
  issues go to critics or Repair instead.
- Format Repair retry context includes the validator error and the full failed
  stage output, but its instruction remains non-semantic correction only.
- If an artifact still fails its Stage Contract after the allowed Format Repair
  retry, the pipeline stops at that stage instead of continuing with partial
  downstream output.
- Isolated lesson-level stages may run once their own inputs validate, but
  cross-lesson stages such as Subject-level Merge wait for all required lesson
  artifacts to validate or be explicitly excluded.
- **Same-Concept Reuse** is allowed across Lessons and Segments, but similar
  material must split when the teachable idea is materially different.
- Subject-level Merge should use compatible Coverage Criteria, not label
  similarity alone, to decide whether candidates are the same Concept.
- A **Deeper Revisit** should become a separate Concept. In v0, the relation is
  expressed through lesson order and Lesson Segments; future dependency work may
  add an explicit prerequisite edge.
- A **Concept** must have **Coverage Criteria** and **Concept Provenance** or an explicit inferred reason.
- In v0 Runtime Graph Export, **Coverage Criteria** are plain strings, not
  separately identified objects.
- **Common Misconceptions** default to empty in v0 unless source-grounded.
- Empty Common Misconceptions and empty teaching notes are expected v0 Dead
  Runtime Fields and should not produce warnings.
- The pipeline emits a metadata-rich **Build Graph Artifact** and a lean
  **Runtime Graph Export**; only the Runtime Graph Export is the root-defined
  **Concept Graph** consumed by the Companion.
- **Display Codes** appear in both the Build Graph Artifact and Runtime Graph
  Export, but never serve as persistent identity.
- The Build Graph Artifact owns canonical flat dependency edges. In v0 this
  edge list is intentionally empty.
- The Runtime Graph Export gets nested dependency objects through deterministic
  **Dependency Projection**. In v0 projection therefore emits empty dependency
  lists.
- Runtime Lessons do not store a separate concept ID list; a Lesson's Concepts
  are derived from its ordered Lesson Segments.
- Runtime Graph Export omits Self-studies; source inventory and source
  traceability live in the Build Graph Artifact.
- **Final Assembly** assigns **Concept IDs** and **Display Codes** after repair, not during extraction.
- **Final Assembly** is deterministic code only: it assigns IDs/display codes,
  projects dependencies, strips build-only metadata, validates schemas, and
  writes final artifacts.
- A **Graph Schema Version** changes when the export shape changes; a **Graph
  Content Version** changes manually when the graph content is revised.

## Resolved Decisions

- V0 graph synthesis starts from the organized Extraction Corpus plus workbook/index metadata; separate AI cleaning and annotation are out of scope.
- The current runtime `graph.json` may inform compatibility only; it is not a concept-content reference for the new graph.
- The workbook is the backbone for Lessons and Self-study membership.
- The new graph should use the richer future-shaped schema even if the current Companion initially consumes only part of it.
- Unavailable Source Bodies still contribute Workbook Metadata to top-down expectation, gap reports, and cautious bridge review.
- Workbook Related Labels are useful metadata signals for lesson intent,
  dependency hints, and bridge review, but they are not Source Body evidence.
- Workbook Related Labels in `si_mod6.xlsx` behave as mixed curriculum taxonomy:
  some are precise prerequisite hints, some are broad repeated lesson-cluster
  labels, some are application areas, and some are adjacent-domain signals.
- For v0, lesson-cluster labels are active inputs to **Top-down Concept
  Extraction**. Prerequisite hints are retained as audit/future-planning
  signals but are not active dependency-edge inputs. Application-area and
  adjacent-domain labels are recorded but otherwise ignored.
- Workbook Label Interpretation is incremental: reuse the existing
  interpretation table for known labels, send only unseen or unresolved labels
  to a light LLM review with local workbook context, then update the table for
  the rest of the run.
- Labels classified as ambiguous in v0 are recorded in a separate ignored row
  and excluded from downstream top-down expectation, future dependency work,
  and critic prompts.
- Activity-only Self-studies are excluded from concept extraction only when they have no usable teaching content in Source Body, title, or description.
- Concept Provenance is a pipeline control surface for validation, reconciliation, critic review, repair, confidence scoring, and human audit.
- Pipeline-inferred Concepts require a dedicated cautious review path and stronger critic scrutiny.
- Source-local Connector Candidates are allowed during Self-study Extraction
  when grounded in one Source Body's internal teaching flow.
- Final output is split into a metadata-rich Build Graph Artifact for audit and
  repairability, and a lean Runtime Graph Export for Companion use.
- The v0 Runtime Graph Export is lesson-based and does not emit Legacy Day
  Presets; the Companion runtime will be adapted later.
- Professor is stored at Subject level for v0 rather than repeated on every
  Lesson.
- The v0 Runtime Graph Export does not include difficulty. Teaching notes are
  included as a Dead Runtime Field and left empty/deferred like source-grounded
  Common Misconceptions.
- V0 does not infer Concept dependency edges. The university Lesson order is
  treated as the trusted prerequisite structure, and Lesson Segmentation owns
  lesson-local concept ordering.
- Generation writes Build Graph Artifacts and Runtime Graph Exports into
  pipeline run artifacts; **Manual Promotion** is the only path into runtime
  reference data.
- Concept Provenance lives in the Build Graph Artifact for v0; the Runtime Graph
  Export omits provenance unless a concrete runtime use appears later.
- Evidence Type remains trackable in the Build Graph Artifact but is stripped
  from the Runtime Graph Export after accepted validation.
- Extraction Reasons remain in the Build Graph Artifact and are stripped from
  the Runtime Graph Export.
- Source Anchors remain in the Build Graph Artifact and are stripped from the
  Runtime Graph Export.
- v0 Validation Blockers include failed Stage Contracts, missing extraction or
  explicit exclusion for usable Self-studies, Lessons without Segments,
  Segments without Concepts, Concepts without Coverage Criteria, missing
  required runtime concept fields, non-empty or invalid v0 dependency edges,
  Segment concept IDs pointing to missing Concepts, dependency projection
  mismatch, and Build Graph Artifact / Runtime Graph Export disagreement on
  Concept IDs, Lessons, or Segment membership.
- Practice Contexts are promising but deferred beyond v0.

## Example Dialogue

> **Dev:** "Book 64 is blocked. Should the pipeline discard it?"
> **Domain expert:** "No. Its Source Body is unavailable, but its Workbook Metadata still tells us what the Lesson intended and should appear in gap review."
>
> **Dev:** "The activity is graded. Should it become a Concept?"
> **Domain expert:** "Not by itself. Grade weight shows importance, but only teachable content or a transferable accepted bridge becomes a Concept."

## Flagged Ambiguities

- **Lesson** is the scheduled university meeting from the workbook. It is not a
  Companion **Session**, which is the student's tutoring conversation at
  runtime.
- The workbook column `Related subjects` does not mean root-glossary
  **Subject**. Use **Workbook Related Labels** for those semicolon-separated
  curriculum hints.
- "source" can mean the workbook assignment or the acquired content. Use **Self-study** for the assignment row, **Workbook Metadata** for workbook fields, and **Source Body** for acquired readable content.
- "discarded" is too broad for blocked resources. Use **Unavailable Source Body** when only the linked content is missing, and reserve exclusion for cases with no usable teaching signal.
- "story" does not mean literal narrative. Use **Pedagogical Story Review** for checking whether the Lesson teaches coherently.
- "final graph" is ambiguous. Use **Build Graph Artifact** for the pipeline's
  metadata-rich final artifact and **Runtime Graph Export** for the lean
  Companion-facing Concept Graph.
