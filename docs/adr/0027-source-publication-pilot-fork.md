# 0027: Fork CG Pipeline at the Source Publication boundary

Date: 2026-09-02
Status: accepted by DEV-74 and implemented by DEV-76

## Context

DEV-74 chose a maintained branch in `cg_pipeline` rather than another
repository. DEV-75 completed the donor boundary in Concept Universe. The pilot
needs that proven syllabus and acquisition work without carrying the later
interpretation system or its infrastructure assumptions.

## Decision

The pilot was forked from Concept Universe commit `46eab4b`, after DEV-75, into
the `cg_pipeline` repository. Its source boundary is an immutable, validated
Source Publication. Syllabus import/versioning/reconciliation, Source
acquisition and cleanup, content-addressed local assets, usage accounting,
PostgreSQL scheduling, producer publication, and claim leases are retained.

`pilot` is the maintained integration branch for this fork. Every pilot ticket
starts from `pilot` and merges back into `pilot`; `main` is not used for pilot
work. The initial five completed ticket increments contained by `pilot` are:

- DEV-76 at `dae3fe54d` (`codex/dev-76-source-publication-pilot`);
- DEV-77 at `015874953` (`codex/dev-77-creation-stages`);
- DEV-78 at `b124211d3` (continued on the DEV-77 branch line);
- DEV-79 at `b0a7a5114` (continued on the DEV-77 branch line); and
- DEV-80 at `c631d308a` (`codex/dev-80-package-download`).

All post-publication generation, selection, reconciliation, judging, task and
embedding code, migrations, prompts, tests, and web assets are removed. The
generic per-Lesson build request and fair worker remain, but their stage
registry is empty until a later issue defines the first consumer.

The 62-file donor migration history is replaced by one clean baseline for a
fresh PostgreSQL 16 database. Binary assets use only the application-managed
content-addressed filesystem. Redis, Celery, S3-compatible storage, pgvector,
and dedicated graph infrastructure are not part of this pilot.

Subject graph ids are allocated once for the tuple Institution, curriculum,
and Subject code. A Syllabus has no graph identity of its own.

The intake-only Companion namespace seam remains. Compose reads the checked-in
pilot namespace snapshot, so a fresh standalone stack can import a workbook;
operators refresh that snapshot from Companion before deploying against a
different graph catalog. No package assembler or runtime-graph fixture crosses
the Source Publication boundary.

ADR 0030 later supersedes only that final export restriction after Accepted Lesson
Refs and immutable Graph Revisions establish a new audited downstream boundary.

## Consequences

- A fresh stack has one product boundary and no reachable downstream phase.
- Deployment consists of PostgreSQL, web, worker, and a local asset volume.
- Future build stages must enter through the explicit Lesson Build registry.
- Donor history remains recoverable from git without becoming runtime surface.
