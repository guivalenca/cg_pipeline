# Concept Universe

A content ledger: permanent fact records for the material a course is taught
from, kept apart from every interpretation built on top of them
(`docs/concept-system-vision-compilation.md`, `docs/adr/`).

What exists today is the first three links of the ingestion chain, in
Postgres: **source** (the thing a teacher chose), **source_snapshot** (its
material at a moment in time, including failed acquisitions), and **artifact**
(a processed form of a snapshot, typically extracted Markdown). Rows are
inserted, never updated or deleted.

## Setup

Postgres 16 with pgvector, on host port 5433 (5432 belongs to the Companion
project's compose):

    docker compose up -d

Python 3.12+, plain venv:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

`DATABASE_URL` defaults to `postgresql://universe:universe@localhost:5433/universe`.
Copy `.env.example` if you want to override it; `.env` is git-ignored.

If the editable install does not take (some macOS setups hide the `.pth` file
pip writes, and Python ignores hidden ones), prefix the commands below with
`PYTHONPATH=src`. `pytest` needs no such help: it puts `src` on the path
itself.

## Migrate

Numbered SQL files in `migrations/`, applied in order, recorded in
`schema_migrations`. No down-migrations: a correction is a new migration.

    python -m universe.migrate

## Backfill

Loads an archived fixture into the ingestion chain. Ids are derived from the
fixture, so the load is idempotent.

    python -m universe.backfill data/si-mod6-com

For `data/si-mod6-com` that is 69 sources, 67 ok snapshots with a sha256 of
the Markdown body plus 67 markdown artifacts, and 2 failed snapshots carrying
the archive's reason for the failure.

## Test

Tests need the compose database running. They drop and recreate a separate
`universe_test` database, so the working database is never touched.

    pytest
