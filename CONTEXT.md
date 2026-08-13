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

**Lesson Knowledge Build**:
An explicit, idempotent request to interpret the current validated Source Publications referenced by one lesson. References remain curricular decisions; local KC work is deduplicated by Source Publication and can be reused across lessons.
_Avoid_: Lesson-owned KC, opening the KC viewer as a write, one build per reference

**KC Corpus Manifest**:
An immutable, content-addressed set of Source Publications authorized for shared embedding, judging, grouping, and canonicalization.
_Avoid_: Latest global corpus, visible Sources in the DOM, syllabus id alone

**Syllabus Knowledge Build**:
The second explicit checkpoint that publishes the four shared KC stages for exactly one Syllabus Version's KC Corpus Manifest.
_Avoid_: Automatic fallthrough from local KC creation, mutable Universe
