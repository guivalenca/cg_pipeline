# 0029: Accepted Lesson Refs project immutable Graph Revisions

Date: 2026-09-02
Status: accepted by DEV-79

## Context

Lesson Builds finish and are reviewed independently, but Companion needs one stable
Subject graph that never exposes in-progress work or loses previously accepted content
while a replacement runs. Updating one mutable `graph.json` would make history,
rollback, and concurrent Lesson acceptance difficult to audit.

## Decision

Whole-Lesson Review records one immutable accept or reject decision per finished build.
Acceptance atomically moves that stable Lesson's Accepted Lesson Ref and deterministically
projects all Accepted Lesson Refs in curricular order into a new immutable, numbered
Graph Revision; rejection and failure move no ref. The Subject graph id and curricular
Lesson ids remain stable, while every new Lesson Build scopes its final Concept and
Lesson Segment ids to that build. A separate current pointer selects the revision served
by default, and every prior revision remains directly addressable. There is no readiness,
completeness, graph-ready state, or cross-Lesson Concept deduplication.

## Consequences

- An accepted sibling Lesson is unaffected by another Lesson's replacement.
- In-progress, failed, rejected, and stale worker output cannot enter a Graph Revision.
- Reassembling the same ordered Accepted Lesson Refs yields the same raw graph bytes.
