# 0016 — Reconcile incoming workbooks before creating a SyllabusVersion

Status: accepted

## Context

Uploading a replacement workbook used to make it the current immutable version
immediately. That skipped the founder's review and could overwrite local
curation such as corrected links, hidden references, validation and complexity
markers. A visual prototype established that review is easiest as a lesson
tree whose indented items are the lesson metadata and its auto-studies.

## Decision

An update upload creates a durable `syllabus_reconciliation`, not a
`syllabus_version`. The review is a three-way comparison:

1. the institution's last accepted workbook is the baseline;
2. the latest SyllabusVersion is the current, locally curated projection;
3. the uploaded workbook is the incoming projection.

Only baseline-to-incoming changes require decisions. Unchanged institutional
fields retain current local edits. `Manter` selects the current item;
`Transicionar` applies only the incoming institutional field deltas over the
current item; a manual choice authors the item explicitly. Local visibility
and review markers are preserved for matched references. A removed Source
reference never deletes its logical Source, snapshots or artifacts.

The incoming workbook, comparison plan and decisions remain auditable. The
current version changes only after every changed item has a destination and
the reconciliation is applied. Reapplying an already completed reconciliation
is idempotent.

## Consequences

- A pending review can be reopened by URL without exposing an unapproved
  workbook as the current syllabus.
- Exact 1:1 items do not create review work, including cases where the founder
  previously edited or hid the item locally.
- Matching uses stable content signals and conservative positional fallback.
  An orphan source may infer its lesson only when Week, Axis and Professor
  identify exactly one candidate; ambiguity remains an explicit input error.
- The accepted prototype was absorbed into the production page and its
  throwaway assets were removed.
