# CG Pipeline

CG Pipeline turns an evolving institutional syllabus and its learning sources
into auditable Source Publications. Source Publication is the boundary of this
pilot; concepts that would interpret or compile those publications belong to a
later slice and are absent here.

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

## Scheduling

**Lesson Build**:
A durable request pinned to a Lesson and its current Source Publications. The
pilot retains the fenced stage planner and worker process but registers no
build stages.
_Avoid_: implicit pipeline, source acquisition, background interpretation

**Claim Lease**:
A PostgreSQL-backed, expiring right for one worker to process one queued item.
_Avoid_: Redis lock, process ownership
