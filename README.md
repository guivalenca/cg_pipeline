# CG Pipeline

CG Pipeline is the Source Publication pilot for Companion. It imports a
full-fidelity Adalove Observer Exporter workbook, preserves Syllabus history,
acquires each selected Source, and publishes auditable canonical Markdown.
This branch deliberately stops there: it does not generate or reconcile
derived knowledge, tasks, graphs, or learning activities.

## What the pilot keeps

- immutable Syllabus Versions and operator-reviewed reconciliation;
- Lesson Subject grouping, filters, Source cards, and source-usage views;
- article, YouTube, authenticated-book, PDF, and ordered-image acquisition;
- hide, remove, replace, retry, validation, and source-cleanup controls;
- PostgreSQL queues with fair claiming and recoverable leases;
- content-addressed Source Assets on an application-managed filesystem; and
- a per-Lesson build boundary whose stage registry is intentionally empty.

The accepted workbook has exactly these six sheets: `Activities`, `Subjects`,
`Materials`, `Order audit`, `Read me`, and `Errors`. The importer models
Classes and their Self-studies, ignores Orientations and their children, and
preserves Deliverables and Evaluations as curricular records. The exporter is
[`tools/adalove_observer_export.js`](tools/adalove_observer_export.js).

## Boot the complete local stack

Docker Compose starts PostgreSQL 16, applies the single baseline migration,
then starts the web app and one worker:

```sh
docker compose up --build
```

Open <http://127.0.0.1:8100>. PostgreSQL is available only on
`127.0.0.1:5433`; override the two host ports with `UNIVERSE_WEB_PORT` and
`UNIVERSE_POSTGRES_PORT`. Provider credentials are optional until an operator
requests an acquisition that needs them. Copy `.env.example` to `.env` for
local values.

The stack has no Redis, Celery, object-storage service, vector extension, or
publicly bound port. Source Asset bytes live in the `source-assets` Docker
volume and their hashes, lineage, order, and storage keys live in PostgreSQL.
Compose uses `config/companion-graph-namespace.json` as its intake namespace;
refresh that snapshot from Companion before targeting a different institution
or graph catalog.

## Local development

Python 3.12 or newer and PostgreSQL 16 are required. PDF and video acquisition
also use Poppler, FFmpeg, `yt-dlp`, Node.js 24, and the pinned npm package.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
npm ci
docker compose up -d postgres
python -m universe.migrate
python serve.py
```

`python serve.py` serves <http://127.0.0.1:8100> and runs an in-process worker.
To keep the processes separate, run:

```sh
uvicorn universe.web.app:app --host 127.0.0.1 --port 8100
python -m universe.acquisition work --forever
```

Useful commands:

```sh
python -m universe.syllabus import path/to/export.xlsx \
  --name "CC07 2026-2A" --institution-id inteli
python -m universe.syllabus list
python -m universe.acquisition enqueue SOURCE_ID
python -m universe.acquisition work
pytest
```

The durable flow is:

```text
Syllabus Version → Source → Source Evidence → canonical cleanup → Source Publication
```

Uploading a workbook never queues provider work. Acquisition is explicit and
one Source at a time. A successful result is immutable Canonical Source
Markdown with complete lineage to its Source Evidence. Failed and superseded
attempts remain auditable beside the current publication.
Operator validation records the exact publication artifact and content hash;
a newer publication must be validated again before a Lesson Build can pin it.

## Architecture

Read [`CONTEXT.md`](CONTEXT.md) for the domain vocabulary and
[`docs/adr/`](docs/adr/) for active decisions. The fork provenance and the
intentional stopping boundary are recorded in ADR 0027.
