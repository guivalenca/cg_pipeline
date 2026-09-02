# 0028: Vendor per-Lesson creation behind Lesson Build

Date: 2026-09-02
Status: accepted by DEV-77

## Context

The Source Publication pilot needs the proven creation behavior from
`claude/improvements` without restoring the donor's Subject-wide pipeline or
letting unvalidated files cross the publication boundary. Rewriting the stages
under `universe` would make their provenance difficult to audit.

## Decision

Vendor the donor creation runtime and six retained stages from commit
`17ab9d93c` under their original `concept_graph_creation` namespace, and permit
that namespace through the Lesson Build module guard. Keep them unreachable
until a later issue registers concrete Lesson Build stages.

Every invocation consumes one Source Ledger containing one stable Lesson and
hash-verified Source Bodies. Concept identity is rooted in that stable Lesson.
Metadata-only creation and Subject Merge remain excluded; a deterministic
per-Lesson projection supplies the downstream shape formerly produced by
Subject Merge. Prompt bytes are part of execution identity, and generated prose
is Brazilian Portuguese while code, notation, proper names, and identifiers are
preserved.

## Consequences

- Donor stage changes remain auditable against one pinned commit.
- Reordering or changing another Lesson cannot stale this Lesson's build.
- Final Assembly remains inert until Lesson Build wiring also carries the stored
  Lesson Subject graph id and other publication provenance into the Source
  Ledger.
