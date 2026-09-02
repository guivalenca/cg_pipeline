# 0025: Stable Lesson identity carried by reconciliation

Date: 2026-08-21
Status: accepted, amended 2026-08-23 and 2026-09-02

## Context

A Lesson appears in many immutable Syllabus Versions. Deriving its identity
from mutable title, description, Subject, or date would turn an ordinary edit
into an unrelated Lesson. Reconciliation already compares the current and
incoming records and is the correct boundary for identity continuity.

## Decision

A Lesson receives a stable id the first time it appears. Reconciliation carries
that id forward when the match is unambiguous and the Lesson kind and Subject
are unchanged. Ambiguous, low-confidence, or structurally changed records
require the operator to select a previous Lesson or declare a new one. Keeping
current content cannot simultaneously mint or claim another identity.

The Adalove Observer Exporter carries an Activity UUID that the institution
preserves across re-exports. Equal Activity UUIDs are the strongest identity
assertion and carry the stable Lesson id automatically, even when title,
description, Subject, kind, order, or date changed. The conservative text rules
still govern records without a UUID and records whose UUID changed.

The uploaded workbook remains immutable evidence. Automatic and operator
identity outcomes are stored as versioned reconciliation interpretations.

## Consequences

- Typo fixes, date moves, and ordinary reordering do not orphan a Lesson.
- A recreated institutional activity can intentionally receive a new identity.
- Matcher conservatism produces review work instead of silent identity damage.
- Stable Lesson identity is available to the retained empty Lesson Build seam.
