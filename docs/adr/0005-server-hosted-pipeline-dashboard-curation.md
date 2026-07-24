# 0005: Server-hosted pipeline, dashboard as the curation surface

Date: 2026-07-23
Status: accepted

## Context

cg_pipeline lived on the founder's machine, was driven by agents, and its
graphs entered production by committing files. The founder wants direct
control, visibility into every phase, and operation from the web instead of
the local machine.

## Decision

The universe runs as a deployed service in production infrastructure from the
start; it is designed as a web system, not a local pipeline. The admin
dashboard is its operating and curation surface: the founder adds, edits,
deletes, and runs processes on the actual server. Logs are agent-friendly so
agents can assist with adjustments, but the founder drives.

The dashboard is the curation surface in the strict sense: every action taken
through it (fixing metadata, excluding a source, approving or rejecting a KC
grouping) writes a permanent curation fact to the ledger, stamped with the
actor, exactly as model decisions are stamped with model and prompt.

Every creation phase boundary starts with a hard audit gate: the pipeline
waits for founder approval before proceeding. Gates are relaxed per phase as
trust builds. A run-comparison view (same fixture, two prompt versions, side
by side, with a push action to adopt the preferred result) is part of the
harness plan; its UI design is deferred to implementation and will be
minimalist.

## Consequences

- No more committing graph files to ship curriculum content.
- The dashboard's action inventory and the curation record schema are the
  same design object.
- cg_pipeline is a quarry, not a foundation: rules and adapters are ported
  selectively with review, and its transcribed corpora serve as test fixtures.
