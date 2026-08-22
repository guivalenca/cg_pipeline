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

## Syllabus HTML and source acquisition

The Syllabus surface is intentionally smaller than the interpretation
pipeline. Start it locally with:

    python serve.py

Then open `http://127.0.0.1:8100`. Uploading a workbook requires a human name,
stores the original XLSX and an immutable parsed version, and **does not queue
any source**. From a Syllabus version, the operator explicitly queues one
Source at a time. A successful acquisition creates a successful
`source_snapshot` and an `artifact(kind = 'markdown')`, then stops. It does not
automatically create Blocks, Passages, Tasks, statements, or KCs. Markdown and
KC progress are therefore displayed independently. This boundary is fixed in
ADR 0012. When the original URL is blocked, private, or otherwise unsuitable,
the same Source can instead be acquired from one uploaded PDF or an explicitly
ordered set of images (ADR 0013); this is a new acquisition attempt, not a new
Source or a Syllabus edit.

The same operations are available without the browser:

    python -m universe.syllabus import path/to/syllabus.xlsx --name "SI module 7"
    python -m universe.syllabus list
    python -m universe.acquisition enqueue SOURCE_ID
    python -m universe.acquisition work

Adapter status is deliberately narrow: public **article** acquisition through
Firecrawl and manual acquisition from **one PDF or ordered images** are
implemented. Manual input accepts one PDF or 1-50 PNG, JPEG, or WebP
images, with a 30 MB total limit. The selected image order is persisted and
becomes the Markdown order; every image is embedded beside a structured visual
description and visible-text transcription. It uses the existing Source and
creates a new immutable Snapshot and Markdown Artifact without generating KCs.

Article images are a distinct acquisition branch—not the manual fallback and
not a scan started after Markdown exists. Image candidates are collected with
the source. Code rejects only technical impossibilities; filenames, alt text,
placement and apparent site chrome do not delete an otherwise valid image.
Surviving candidates are downloaded into immutable ledger assets, then one
source-level Gemini call receives the source once and every downloaded image
under a stable id. Every image still has its own result and failure state. For
an article, a failed or malformed visual result remains in the ledger but is
omitted from Markdown; it never invalidates text or protects adjacent chrome.

The raw text remains an internal artifact while this branch runs, but the UI
publishes only after terminal enriched Markdown and passage cleanup. Each
retained image is referenced
beside its OCR, visual description and any limitation as one atomic document
element; model prose never replaces the asset. This lets image meaning affect
passage boundaries without making one failed image retry the source.

Manual screenshots are reconstructed document-wide. Their visible order is
preserved and the original normalized PNGs remain immutable evidence. The
audit-only PDF transport stays lossless up to 24 MB; above that provider-risk
threshold it uses JPEG quality 94 without chroma subsampling, while Firecrawl
runs in forced OCR mode. The same PDF Figure Placement Module then
inventories every page and inserts only local figure crops beside the Blocks
that explain them. Whole-page screenshots remain immutable evidence and are
never published as Markdown images.

PDF extraction is structural (ADR 0017). An explicitly consented private PDF is
uploaded to Firecrawl `/v2/parse`, which returns reading-order Markdown,
Markdown tables and figure references. Returned figures are downloaded at once,
stored as immutable `pdf_figure` assets and rewritten to local URLs; full-page
screenshots are never published. Poppler still records the exact text layer and
a stable PNG render for every page as audit evidence only. The enriched Markdown
is published after extracted figures are local and passage cleanup has
succeeded. Set `FIRECRAWL_ALLOW_PRIVATE_PDF_UPLOADS=1` only where this external
document processing is approved; `FIRECRAWL_API_KEY` is also required.

Install Poppler locally before processing PDFs (`brew install poppler` on
macOS; the Railway worker image needs the equivalent `poppler-utils` package).

Concretely scoped book pages use the Browserbase/Sophia Adapter. Each captured
page and its reader accessibility text is committed before navigation
continues, so a transient browser failure resumes from the completed prefix.
If Firecrawl exhausts its short request-level retries, the same acquisition is
rescheduled with its durable parse ledger and already captured page prefix;
the book is not recaptured merely because the document provider was temporarily
unavailable. The manifest-addressed transport PDF is reused byte-for-byte on
that retry instead of being regenerated.
Before committing a page, the Adapter expands the viewport until the page root,
its scroll area, and every visual descendant fit horizontally and vertically;
the bitmap is then checked for both dense and sparse content covered by the
reader's navigation divider. The verified empty clearance band and its chrome
are removed together, and hover/focus controls are dismissed before capture;
otherwise a larger viewport is tried. An unverifiable or clipped page is retried and never
replaced by a body or viewport screenshot containing reader chrome. Figure
crops are validated against the page pixels: a clean Gemini edge is preserved.
When ink crosses an edge, a nearby inner gutter removes neighboring prose;
otherwise the edge grows to the first outer gutter to complete the figure.
This retains complete tall and rotated diagrams without crossing a verified
gap into neighboring prose; a region with no safe gutter remains explicit
attention work instead of becoming a contaminated crop.
After the Browserbase session is released, those ordered pages enter the same
forced-OCR reconstruction and figure-placement path as manual screenshots.
Exact reader text remains separate evidence: it helps page-local validation
but cannot override OCR formulas or document structure. The Syllabus action
names Browserbase, Firecrawl, OpenRouter/Gemini, and the exact page scope before
queueing.

YouTube sources begin with a metadata-only preflight. Publisher captions are
preserved exactly when available; otherwise bounded, durable OpenRouter STT
chunks are used after the duration policy is satisfied. Every route also
captures visual evidence: spoken videos use Summarize to select candidate
frames for the shared grouped image analysis, while proven visual-only videos
use one whole-video teaching-beat interpretation and materialize its selected
frames without paying for a second semantic decision. Frames, timestamps,
caption/STT facts and provider usage remain auditable, and only the nonempty
canonical cleanup Artifact is exposed as ready Markdown. Workers need Node.js
24+, the lockfile installed with `npm ci`, `yt-dlp`, `ffmpeg`, and `ffprobe`.

For local use, `python serve.py` runs the web process and one in-process worker.
In Railway, use two services backed by the same Postgres database:

    # web service (ACQUISITION_WORKER_IN_WEB=0)
    uvicorn universe.web.app:app --host 0.0.0.0 --port "$PORT"

    # worker service
    python -m universe.acquisition work --forever

The durable queue is in Postgres; multiple workers claim independent jobs with
row locking. Redis is not required for this slice. The required deployment
variables are `DATABASE_URL` for both services and `FIRECRAWL_API_KEY` for the
Article Adapter. Manual image acquisition additionally needs an
OpenRouter-compatible model credential and Poppler installed in the worker
image. `ACQUISITION_POLL_SECONDS` controls an idle worker's polling interval
and `ACQUISITION_STALE_MINUTES` controls lease recovery. `MODEL_API_BASE`,
`MODEL_API_KEY`, and the OpenRouter key aliases are used by the interpretation
pipeline and by visual description, but not by Firecrawl page retrieval or
deterministic PDF text/render extraction.

Binary PDF/image source evidence never lives in Postgres. Postgres keeps immutable asset
metadata, SHA-256, order, lineage, and `storage_key`; canonical Markdown also
stays there. Local development stores bodies under
`CONCEPT_UNIVERSE_ASSET_ROOT`. Railway uses a Railway Bucket or another
S3-compatible object store configured with `AWS_ENDPOINT_URL`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET_NAME`,
`AWS_DEFAULT_REGION`, and `AWS_S3_URL_STYLE`. A manual acquisition remains
capped at 30 MB even when the backing store has a higher object limit.

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

The source-cleaning path uses the enriched Markdown as an immutable element
ledger. Passage triage may keep, drop, refine, or preserve a passage as
unknown. Refinement reports only numbered elements to remove; code applies the
omissions and sends the resulting revision through triage again. It never asks
the model to rewrite source text. A one-element passage cannot be refined.
Unresolved images from public articles stay in the image ledger but are
omitted from enriched Markdown before cuts, so they cannot shield adjacent
boilerplate. Unresolved manual screenshots or PDF pages remain primary
evidence and put the source in an explicit attention state.

After a stamped passage-cuts run, execute the complete cleanup loop with:

    python -m universe.passage_cleanup run \
        --cuts-run RUN_ID \
        --model MODEL_ID

The result includes a cleanup id and one deterministic canonical Markdown
artifact per source. Task generation is a separate explicit action over that
terminal cleanup; `keep` and `unknown` are eligible, `drop` is excluded, and a
passage may validly report no tasks:

    python -m universe.taskgen run \
        --prompt v005 \
        --model MODEL_ID \
        --cleanup CLEANUP_ID \
        --tool prompts/task-generation/tool-v002.json

The Syllabus surface now exposes that interpretation boundary directly. Once
every active reference in a lesson is validated and resolves to a current
Source Publication, an explicit KC Generation (code: `lesson_knowledge`;
formerly Lesson Knowledge Build) advances its eleven local KC stages. Work is
pinned to immutable publication artifacts and reused when the same publication
appears in another lesson; reading Markdown or KCs never starts provider work.

Universe Reconciliation (code: `syllabus_knowledge`; formerly Syllabus
Knowledge Build) is a separate explicit checkpoint. It seals the exact current
publications of one Syllabus Version into a content-addressed Reconciliation
Scope (formerly KC Corpus Manifest), then advances only the four shared stages
(embedding, judging, grouping, and canonical statements). `/graph` requires
that scope id, so historical versions never silently open a global/latest
corpus.

A third checkpoint, KC Selection, is decided but not built yet (ADRs 0024
and 0026): between generation and reconciliation, it selects the KC
Candidates that best fulfill each lesson's curricular record, and only
selected candidates enter the Universe. Until that slice lands, the
Reconciliation Scope still freezes publications as described above.

## Dashboard

`python serve.py` serves the integrated application at
`http://127.0.0.1:8100`. The rich Syllabus surface owns version review,
source acquisition, Markdown publication and manual PDF/image fallback. The
same process also preserves the overview and attention queue, organizational
structure, per-source pipeline progress, universe graph, and run ledger from
the KC dashboard. Static pages require no frontend build step.

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

Tests need the compose database running. Pytest migrates one temporary
`universe_test_template_*` database, clones a fresh `universe_test_*` database
for each test module, and drops them after the run. The working database is
never touched, and committed facts cannot leak between modules.

    pytest
