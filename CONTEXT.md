# CG Pipeline

CG Pipeline turns an evolving institutional syllabus and its learning sources
into auditable Source Publications, then derives per-Lesson learning structure
only through an explicit Lesson Build. Source Publication remains the trust
boundary between acquired evidence and interpreted learning content.

## Syllabus

**Syllabus Version**:
An immutable import of one accepted Adalove workbook at a point in time.
_Avoid_: spreadsheet upload, current sheet

**Syllabus Reconciliation**:
An auditable comparison between the current and incoming Syllabus Versions.
Unambiguous institutional identities carry forward automatically; ambiguous
matches require an operator decision.
_Avoid_: merge, overwrite, row edit

**Lesson**:
One dated curricular activity imported from `Activities`. A Lesson keeps a
stable identity across reconciled Syllabus Versions.
_Avoid_: row, meeting title, source

**Lesson Subject**:
The institution/curriculum/code identity used to group Lessons. Its graph id is
allocated once per Subject and reused across imports and reconciliations.
_Avoid_: syllabus graph, free-text tag

**Self-study**:
A curricular activity whose institutional parent identity links it to a
Lesson. It is not flattened into an independent Lesson.
_Avoid_: orphan activity, source card

**Source Reference**:
A Syllabus Version's use of a Source. Visibility, replacement, and removal are
versioned reference decisions and do not mutate Source evidence.
_Avoid_: source, URL row, acquisition

## Source Publication

**Source**:
The stable identity of one learning resource across references, retries, and
Syllabus Versions.
_Avoid_: URL row, artifact, acquisition job

**Source Evidence**:
Immutable acquired material, including provider Markdown, document pages,
captions, speech segments, frames, figures, and original bytes.
_Avoid_: final Markdown, temporary download

**Source Asset**:
A content-addressed byte object retained on the local Asset Store with its
hash, provenance, and stable same-origin reference recorded in PostgreSQL.
_Avoid_: temporary file, remote image URL, database blob

**Passage**:
A stable ordered range of Source Evidence evaluated as one unit during
canonical cleanup.
_Avoid_: arbitrary chunk, rewritten summary

**Canonical Source Markdown**:
The publishable Markdown produced after visual evidence handling and
element-preserving cleanup retain at least one teachable element.
_Avoid_: raw Markdown, provider response, transcript artifact

**Source Publication**:
A successful Canonical Source Markdown artifact with complete lineage back to
Source Evidence.
_Avoid_: successful download, acquisition result

**Source Publication Validation**:
An operator decision bound to one immutable publication artifact and content
hash. A later acquisition or cleanup result does not inherit it.
_Avoid_: validated Source, permanent checkbox

## Lesson Creation

**Source Ledger**:
The per-Lesson presentation of stable Lesson identity and pinned Source Bodies
consumed by Lesson Creation.
_Avoid_: workbook, Subject ledger, current Sources

**Source Body**:
The hash-verified Canonical Source Markdown from one pinned Source Publication
as presented to Lesson Creation.
_Avoid_: raw response, transcript, unchecked file path

**Candidate Concept**:
A source-grounded teachable idea proposed from one Self-study before Lesson-wide
reconciliation.
_Avoid_: Concept, tag, topic

**Lesson Reconciliation**:
An auditable consolidation of Candidate Concepts within one Lesson that retains
their evidence and assignment decisions.
_Avoid_: Syllabus Reconciliation, Subject Merge

**Concept**:
A teachable unit accepted for one Lesson with identity rooted in that Lesson's
stable identity.
_Avoid_: Candidate Concept, label, keyword

**Coverage Criterion**:
An observable statement of what a learner must be able to explain, distinguish,
or perform for a Concept.
_Avoid_: objective, rubric item

**Lesson Segment**:
An ordered instructional grouping of Concepts within one Lesson.
_Avoid_: arbitrary chunk, page section

**Knowledge Type**:
The primary teaching mode of a Concept: conceptual, procedural, factual, or
applied.
_Avoid_: difficulty, subject area

**Subject Merge**:
Cross-Lesson Concept consolidation within a Lesson Subject. The per-Lesson pilot
deliberately excludes it.
_Avoid_: Lesson Reconciliation, one-Lesson projection

## Scheduling

**Lesson Build**:
A durable request pinned to a Lesson and its current Source Publications. It is
the sole boundary for requesting post-publication Lesson Creation.
_Avoid_: implicit pipeline, source acquisition, background interpretation

**Lesson Build Manifest**:
The immutable statement of a Lesson Build's ordered Source Publications,
Lesson metadata, prompt identities, and model routes.
_Avoid_: KC Corpus Manifest, current selection, Source Ledger

**Lesson Build Checkpoint**:
An immutable output of one Lesson Creation stage, reusable only when its Lesson
Build Manifest and stage fingerprint still match.
_Avoid_: cache, mutable draft, latest artifact

**Attempt**:
One model-provider invocation attributed to a Lesson Build, including its model
identity, outcome, usage, and cost.
_Avoid_: call row, retry counter

**Claim Lease**:
A PostgreSQL-backed, expiring right for one worker to process one queued item.
_Avoid_: Redis lock, process ownership

## Graph Review

**Whole-Lesson Review**:
The operator decision to accept or reject one finished Lesson Build as a whole.
Only acceptance changes the Subject graph; rejection preserves its current content.
_Avoid_: checkpoint review, partial acceptance, graph readiness

**Accepted Lesson Ref**:
The current accepted Lesson fragment for one stable Lesson inside a Lesson Subject.
A replacement moves this ref without changing the curricular Lesson identity.
_Avoid_: latest build, accepted checkpoint, merged Lesson

**Graph Revision**:
An immutable, numbered projection of every Accepted Lesson Ref in a Lesson Subject.
Each accepted addition or replacement creates one; unaccepted work never appears in one.
_Avoid_: graph-ready state, mutable graph, build output

**Current Graph Revision**:
The Graph Revision served by default for a Lesson Subject while its prior revisions
remain addressable.
_Avoid_: latest build, complete graph, final graph
