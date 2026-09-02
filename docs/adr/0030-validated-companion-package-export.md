# 0030: Export Graph Revisions as validated Companion Packages

Date: 2026-09-02
Status: accepted by DEV-80; supersedes the export restriction in ADR 0027

## Context

ADR 0027 excluded runtime graphs and a package assembler when Source Publication was
the pilot's only product boundary. ADRs 0028 and 0029 subsequently introduced audited
Lesson Builds, Accepted Lesson Refs, and immutable Graph Revisions. Operators now need
to hand one exact revision to Companion without letting CG Pipeline write into the
Companion repository or weakening either application's validation rules.

## Decision

CG Pipeline may export a current or explicitly selected Graph Revision as a Companion
Package containing only `graph.json` and an empty, schema-valid `intro_notes.json`.
The package is downloadable only after Companion's real package validator accepts the
exact candidate files; validation errors fail closed while the raw Graph Revision stays
available. Installation and Lesson Preview generation remain manual Companion-side
operations, and CG Pipeline never writes into the Companion repository.

This supersedes ADR 0027's prohibition on a package assembler and runtime-graph export.
Source Publication remains the immutable trust boundary for build inputs; only accepted,
immutable Graph Revisions may cross the new downstream export boundary.

## Consequences

- Companion's validator, not a duplicated CG Pipeline schema, is the final acceptance
  authority for installable packages.
- Historical Graph Revisions remain reproducibly downloadable and cannot be confused
  with the current revision.
- A validator outage or build/runtime contract disagreement blocks the package download.
