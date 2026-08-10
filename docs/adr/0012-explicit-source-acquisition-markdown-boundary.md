# 0012: Explicit source acquisition and the Markdown boundary

Date: 2026-08-06
Status: accepted

## Context

The Syllabus is both the teacher's versioned curricular input and the founder's
operating surface for source acquisition. Earlier dashboard work treated every
unprocessed source as implicit work and offered actions that could continue
from acquisition through Blocks, Passages, Tasks, and knowledge extraction.
That made a simple act -- acquiring one selected source -- hard to reason about
and coupled the Syllabus to the full interpretation pipeline.

Syllabus references also change over time. A removed or materially changed
reference must disappear from the current curriculum without erasing a Source,
Snapshot, Artifact, Task, or KC already present in the Universe.

## Decision

Acquisition is always requested for exactly one Source. Uploading a Syllabus
does not enqueue work. There is no implicit "extract pending" operation in the
Syllabus interface. Several sources may run concurrently only because several
independent source jobs were explicitly requested.

The job is durable in Postgres before an external Adapter is called. Its
terminal successful result is an immutable `artifact(kind = 'markdown')` with
lineage through a successful Source Snapshot. A failed retry never hides or
invalidates an older successful Artifact.

Markdown is a deliberate pipeline boundary. Acquisition does not automatically
create Blocks, Passages, Tasks, KC statements, or KC groups. Those are separate
explicit operations over a selected Artifact.

The Syllabus page shows acquisition and knowledge progress per Source, never as
state owned by a lesson. Its default projection reads only the current complete
Syllabus Version. Historical versions remain selectable. Removing a reference
authors a new version without it; all content-ledger and interpretation rows
remain untouched.

Canonical Markdown stays in Postgres `artifact.body`, which is the existing
Concept Universe handoff. Binary capture evidence such as PDFs and page
screenshots lives outside Postgres and is referenced by immutable ledger
metadata and `storage_key` (ADR 0013); that does not change the Markdown
contract.

## Consequences

- The founder controls cost and scope one Source at a time.
- Agents and the HTML interface use the same durable queue and facts.
- Restarts cannot erase queued work or completed Markdown.
- Curriculum visibility and permanent Universe knowledge remain distinct.
- Provider complexity stays behind acquisition Adapters.
- KC generation can evolve without changing Syllabus ingestion or acquisition.
