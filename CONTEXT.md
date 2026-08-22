# Concept Universe

Concept Universe turns an evolving syllabus and its learning sources into auditable source publications, then derives reusable knowledge from those publications.

## Syllabus

**Syllabus Version**:
An immutable import of the workbook accepted as the syllabus at a point in time.
_Avoid_: Spreadsheet upload, current sheet

**Syllabus Reconciliation**:
An operator-reviewed comparison between the current Syllabus Version and an incoming workbook, including lesson and source disposition decisions.
_Avoid_: Blind re-import, spreadsheet diff

**Source Review**:
The syllabus-level decision that preserves, moves, hides, or replaces one Source while reconciling versions.
_Avoid_: Row edit, automatic deletion

## Source publication

**Source**:
The stable identity of one learning resource across repeated acquisitions and Syllabus Versions.
_Avoid_: URL row, artifact, extraction job

**Source Evidence**:
Immutable material acquired from a Source before interpretation or cleanup, including provider Markdown, pages, captions, speech segments, frames, figures, and original bytes.
_Avoid_: Final Markdown, temporary download

**Source Asset**:
A content-addressed visual or document byte object retained as Source Evidence with provenance and a stable same-origin reference.
_Avoid_: Temporary file, remote image URL

**Passage**:
A stable, ordered range of source blocks evaluated as one unit by triage and refinement.
_Avoid_: Chunk, paragraph batch

**Canonical Source Markdown**:
The only publishable Markdown for a Source Snapshot, produced after visual evidence handling and passage cleanup preserve at least one teachable element.
_Avoid_: Raw Markdown, enriched intermediate, transcript artifact

**Source Publication**:
A successful Canonical Source Markdown artifact together with its complete lineage back to Source Evidence.
_Avoid_: Successful download, acquisition result

## Video evidence

**Speech Evidence**:
Exact ordered publisher-caption cues or speech-to-text segments with timestamps and acquisition lineage.
_Avoid_: Summary, rewritten transcript

**Visual Teaching Beat**:
One major instructional idea communicated visually during a video, represented by an ordered time range, a representative frame, visible text, and teaching explanation.
_Avoid_: Sampled frame, screenshot candidate

**Referenced Visual**:
A figure, image, page crop, or video frame retained because it contributes distinct teachable information to its Source Publication.
_Avoid_: Decoration, unresolved remote image

## Knowledge

**Knowledge Component**:
A reusable unit of knowledge derived downstream from source-grounded tasks and statements, never created implicitly by Source acquisition.
_Avoid_: Passage, task, Markdown section

**KC Candidate**:
A unitary unit of knowledge produced by KC Generation — one task with its answer, statement, and axes — before any lesson has selected it. It joins the Universe only when at least one active lesson selects it.
_Avoid_: KC, task row, rejected knowledge

**KC Generation**:
The first explicit checkpoint: turns one lesson's validated Source Publications into KC Candidates by running the whole per-source generation chain. Work is keyed by Source Publication, so a publication shared by two lessons is generated once and reused.
_Avoid_: Lesson-owned KC, opening the KC viewer as a write, Lesson Knowledge Build (former name)

**KC Selection**:
The second explicit checkpoint: selects, from one lesson's KC Candidates, the set that best fulfills the lesson's curricular record — title and description carry the intention, subjects detail it. Selection is optimization, not reduction, and is local to the lesson: an omitted candidate remains reusable and may be selected by another lesson.
_Avoid_: Deletion, quality gate, per-source quota, Lesson Purpose (removed intermediate)

**Reconciliation Scope**:
The frozen, exact list of what one Universe Reconciliation runs over — locked before reconciling starts so the result can never silently drift.
_Avoid_: Latest global corpus, visible Sources in the DOM, syllabus id alone, KC Corpus Manifest (former name)

**Universe Reconciliation**:
The third explicit checkpoint: decides cross-source identity over its frozen Reconciliation Scope — near-identical KC Candidates merge into one composite KC with a canonical statement. Also the only producer of the directional (one-way implication) signal, unused downstream today.
_Avoid_: Syllabus Reconciliation, automatic fallthrough from local KC creation, mutable Universe, Syllabus Knowledge Build (former name)
