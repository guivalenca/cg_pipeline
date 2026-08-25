# 0004: Build externally, bridge with a disposable compiler

Date: 2026-07-23
Status: accepted, amended 2026-08-02 (see Amendments): the
disposable-compiler bridge is no longer the expected seam; the external
build stands.

## Context

The Companion already treats Concept Graphs as read-only reference data that
arrives from outside, resolved through a catalog seam and snapshotted by each
Session (companion ADR 0007). Nothing in the running product cares how a graph
was authored. Adapting the Companion's evaluation to the universe would couple
the new system to a structure it is meant to replace.

## Decision

The universe is built as a standalone external system: its own repo, its own
schema, importing nothing from Companion internals. The bridge is a one-way,
deliberately disposable compiler on the universe side that emits a Concept
Graph in today's format at the existing seam: universe concepts become graph
concepts, syllabus day ordering becomes graph ordering, lesson plans become
Runtime Lessons, KC digests feed teaching context. The Companion changes zero
lines. Exported concept ids embed universe identity so phase-1 session records
and Concept States remain mappable when phase 2 lands.

Dependency edges are emitted empty; production graphs already have no edges.
Later the Companion may adopt a new clean format that accepts KCs and Concepts
natively; the founder prefers that over carrying the legacy format forever.
At that point the compiler is deleted, not surgically removed from eval code.

## Consequences

- The universe's fact layer never knows the Companion exists.
- Throwaway code is confined to one clearly labeled formatter.
- The running product keeps teaching from universe-authored content during the
  whole build, giving real usage feedback without integration risk.

## Amendments (2026-08-02)

Founder correction: the compiler emitting today's Concept Graph format is
no longer expected to serve as the bridge. The decision to make segments
the unit the Companion consumes means the Companion itself will change —
tutor ingestion, student evaluation, and whatever else consumes the graph
today — so the legacy graph format will not survive as the seam, and
"the Companion changes zero lines" no longer holds.

What stands from this ADR: the universe is a standalone external system,
its own repo and schema, importing nothing from Companion internals, and
the universe's fact layer never knows the Companion exists. The shape of
the new seam — what exactly the Companion will consume, at what boundary —
is undesigned; it is tracked as an open question in the vision document
and depends on the segment design, itself open.

## Amendment (2026-08-23)

The local authoring shell may read Companion's versioned, read-only graph
namespace: Institution slugs/names and occupied graph ids. It does not mirror
Course or Group. A second Companion-owned interface assesses the exact finished
package with Companion's runtime Graph Catalog loader before export. Generated
content still leaves Concept Universe as an explicit JSON package installed in
Companion; this check does not deploy either repository or assign the graph to
a Group.
