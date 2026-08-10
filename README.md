# Concept Universe

A content ledger: permanent fact records for the material a course is taught
from, kept apart from every interpretation built on top of them
(`docs/concept-system-vision-compilation.md`, `docs/adr/`).

The ingestion chain in Postgres: **source** (the thing a teacher chose),
**source_snapshot** (its material at a moment in time, including failed
acquisitions), and **artifact** (a processed form of a snapshot, typically
extracted Markdown). Rows are inserted, never updated or deleted.

On top of it, the extraction pipeline as built so far, one module per
stage under `src/universe/`:

    blocks → passages (cuts) → passage-triage → task-generation → task-granularity → task-revision → task-triage → task-substance → kc-statement → task-modality + task-knowledge (axes) → task-embedding → kc-judge (mutual-mastery pair calls) → clique grouping into KCs (ADR 0011)

Orientation for a new session:

- **Why the pipeline has this shape**: `docs/adr/`, one decision per file;
  ADR 0010 (amended) is the pipeline itself.
- **Which model and prompt each stage uses, and the current reference
  chain of runs**: `docs/pipeline-defaults.md`.
- **What the experiments taught us** (prompt lessons, model temperaments,
  why stages exist): `experiments.md` in the research archive at
  `~/Desktop/concept-universe-research/` (kept outside the repo with the
  research memos; consult when needed).

Every model call is stamped in the run ledger (`run`, `run_item`); prompts
are versioned files under `prompts/<stage>/`, hashed into each run.

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

## Harness

Runs a versioned prompt against stored artifacts and records every call as a
fact: `run` (stage, model, prompt ref, sha of the prompt file at run time,
params, timings) and `run_item` (one call, its response or its error, usage,
duration). Prompts live at `prompts/<stage>/<vNNN>.md`, with `{{body}}` where
the artifact body goes.

    python -m universe.harness list
    python -m universe.harness report r0001
    python -m universe.harness compare r0001 r0002

Each pipeline stage has its own runner on the same machinery, e.g.
`python -m universe.taskgen run ...`, `python -m universe.task_revision
run ...`; run them with `--help` for the exact flags, and see
`docs/pipeline-defaults.md` for the presets that are known to work.

The judge stage writes its verdicts to the ledger (`kc_verdict`, one pair
judged once per judge generation — a new model or prompt version re-judges
beside the old verdicts, and consumers read the newest per pair) via
`python -m universe.kc_judge run`;
`python -m universe.kc_groups compute` derives composite KC snapshots from
the verdict ledger by the ADR 0011 clique rule. Both are recomputable
interpretations over permanent facts.

## Syllabus

Sources enter through the syllabus (ADR 0006). `python -m universe.syllabus
import <xlsx>` reads the workbook (single 'Projetos' sheet; row order is
meaningless), mints sources from canonical URLs, and records a new syllabus
version beside the previous one; an unchanged workbook records nothing.
Uploading through the dashboard does the same and stamps a curation event.

## Dashboard

A local web dashboard (ADR 0005 as amended: local until wired into the
Companion, then Railway):

    python serve.py

serves http://127.0.0.1:8100 — overview and attention queue, syllabus
upload/versions/diff, per-source ingestion progress (`universe.spine`),
the universe graph (unitary KCs, verdict edges, committed composite KCs),
and the run ledger. Static pages, no build step; design system ported from
the Companion admin.

`report` and `compare` write self-contained HTML into `reports/`, which is
git-ignored because it is regenerable from the database. Historical judge
benches, raw outputs, evaluations, and notebooks are isolated in
`~/Desktop/concept-universe-research/judge-research-2026-08/`; current
operational choices live in `docs/pipeline-defaults.md`. The model endpoint is
any OpenAI-chat-completions-compatible API, set by `MODEL_API_BASE` and
`MODEL_API_KEY`, defaulting to OpenRouter with `OPEN_ROUTER_API_KEY` from
`.env`; the model id is per run, because switching models is the point. A failed call does not end the run: the error lands on the item, and
the run is `failed` only if every item failed.

## Test

Tests need the compose database running. They drop and recreate a separate
`universe_test` database, so the working database is never touched.

    pytest
