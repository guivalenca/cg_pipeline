# 0004: Build externally, bridge with a disposable compiler

Date: 2026-07-23
Status: accepted

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
