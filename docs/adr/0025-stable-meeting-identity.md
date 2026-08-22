# 0025: Stable meeting identity carried by reconciliation

Date: 2026-08-21
Status: accepted, amended 2026-08-22 (see Amendment).

## Context

Lesson ids are re-minted on every Syllabus Version (`curate_syllabus` derives
them from the version id), so nothing durable can anchor to "this meeting."
The Lesson Purpose and the KC selections of ADR 0024 need exactly that anchor.
The institutional workbook (type 2, the incoming default) offers no help: it
has no unique meeting code — autoestudos reference their parent meeting by
exact title. Computing identity from content was considered and rejected: a
content signature turns a typo fix into a new meeting and orphans every
purpose and selection hanging off the old one.

## Decision

**Identity is the operator's reconciliation decision, recorded.** A meeting
receives a stable id the first time it appears. Syllabus Reconciliation
already matches lessons across versions and already asks the operator to
dispose of each match (Manter/Transicionar); that decision now carries the
stable id forward as lineage. Identity is never computed from content — the
match the operator confirms *is* the identity assertion. A lesson that
matches nothing is a new meeting with a new id.

**Purpose validity is one toggle at the same screen.** Each matched lesson
holding an approved Lesson Purpose shows one choice during reconciliation:
purpose still valid, or redo. The system suggests a default — curricular
fields (title, description, subjects) unchanged suggests valid, changed
suggests redo — and the operator's click is the recorded fact. No rule
engine; the founder's dealbreaker intuitions live in the suggestion, not in
enforcement.

**Selection freshness follows automatically.** Selection re-runs (as a new
generation, per ADR 0024) when the purpose changes or when the candidate pool
changes — sources added, removed, or re-published. A date move alone changes
nothing: identity, purpose, and selections all survive untouched.

## Consequences

- The reconciliation matcher becomes real infrastructure: a silent mis-match
  now mis-anchors purposes and selections. Its reliability under compound
  changes (title + description + subjects + date at once) is an open
  investigation, Linear DEV-19, blocked by type-2 workbook support.
- First-class type-2 workbook support (Assuntos as a structured list,
  Encontro pai parenthood) is a prerequisite of the KC Selection slice, since
  the purpose derives from those fields.
- Typo fixes and cosmetic edits never orphan anything.

## Amendment (2026-08-22)

ADR 0026 removed the Lesson Purpose, part of this decision's motivation.
What stands unchanged: the stable meeting id, its lineage through the
operator's reconciliation decision, and re-selection on candidate-pool
changes. The purpose-validity toggle is re-keyed to the selection itself:
each matched lesson holding a completed selection shows "selection still
valid / re-select", with the same suggested default (curricular fields —
title, description, subjects — unchanged suggests valid). The DEV-19
investigation is unaffected.
