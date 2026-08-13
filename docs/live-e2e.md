# Bounded live extraction tracer

The first consolidated acceptance results are recorded in
[`source-publication-acceptance-2026-08-11.md`](source-publication-acceptance-2026-08-11.md).

`tests/live_e2e` is a deliberately opt-in tracer for the source-publication
pipeline. It is not part of the ordinary test suite and it never downloads a
fixture automatically. Its first purpose is to prove one trustworthy vertical
slice for each source Adapter before concurrency and corpus expansion are
tested.

## Design

The tracer treats source publication as one deep **Module**. Its narrow
**Interface** is: select named cases, provide immutable inputs, and receive a
canonical Markdown artifact plus a durable quality report. Provider routing,
page analysis, image triage, cleanup, and persistence remain hidden
**Implementation** details. That **Depth** keeps the common caller trivial.

The source-media boundary is the **Seam**. Article, PDF, video, and book are
each an **Adapter** behind the same publication contract. Shared canonical and
asset assertions provide **Leverage**, while route-specific assertions stay
next to their fixtures for **Locality**. The tracer is intentionally serial;
queue concurrency belongs in a later soak test, after these vertical slices
are trusted.

## Hard opt-in

All three controls are required:

1. pytest must receive `--live-e2e`;
2. `RUN_LIVE_SOURCE_E2E` must exactly equal
   `I_UNDERSTAND_THIS_CALLS_EXTERNAL_PROVIDERS`;
3. `LIVE_E2E_CASES` must explicitly select a comma-separated subset of
   `xlsx,article,knowledge,pdf,video,book`. `knowledge` requires `article`
   and continues that one real Canonical Source Publication through the 11
   local and 4 shared KC stages.

Provider cases additionally require an explicit
`LIVE_E2E_MAX_OPENROUTER_USD`. The suite rejects global ceilings above `$1.00`
and refuses non-local PostgreSQL databases. PDF and book cases require both
private-upload consent flags. Missing credential messages mention only setting
names, never values.

The directory's session-autouse gate checks the first two controls for every
test below `tests/live_e2e`, even if a future test omits the `live_e2e` marker.
The collection skip is only an early, readable signal; it is not the safety
boundary. An unmarked canary and ordinary provider-free contract tests keep
that distinction executable.

The XLSX case itself makes no external call, but it uses the same hard gate so
an ordinary pytest invocation cannot create its isolated database or evidence
directory. Case selection is truthful: selecting only one provider case does
not implicitly import the workbook.

## Pinned inputs and candidates

The authorized workbook is:

- `/Users/guilhermevalenca/Desktop/concept-universe/data/GRAD CC07 - 2026-2A.xlsx`
- SHA-256: `873b45e428304988f23446b20e0e58d3ed9edfb8cfb8ba50e9ebe22b81e18fc5`
- expected: 64 lessons, 130 references, 128 logical Sources, with 81 articles,
  29 videos, and 20 books.

The characterized PDF is immutable local evidence produced by the previously
tested syllabus pipeline:

- `/Users/guilhermevalenca/Desktop/concept-universe-syllabus/.data/source-assets/sha256/e2/e22b6b7ea0d7e67151b1585ea3108a6eabcf76ccf6a03b69b29adbdbf4920f4f`
- SHA-256: `e22b6b7ea0d7e67151b1585ea3108a6eabcf76ccf6a03b69b29adbdbf4920f4f`
- expected: 175,634 bytes and 24 usable pages.

The deterministic vertical-slice candidates are:

| Case | Candidate | Why it is bounded |
| --- | --- | --- |
| Article | `https://www.ibm.com/docs/pt-br/rsas/7.5.0?topic=topologies-deployment-diagrams` | Known UML terminology and archived visual evidence |
| PDF | pinned local file above | Immutable hash, 24 known pages |
| Video | `https://www.youtube.com/watch?v=UFtXy0KRxVI` | Known publisher-caption route, about 386 seconds and 129 cues |
| Book | resource `9788522128303`, pages `198-205` | Exactly eight known reader pages |

The workbook also contains later corpus-expansion candidates: Lucidchart's UML
deployment article, `https://theodpbook.lcc.uma.es/docs/Chapter1.pdf`, YouTube
video `vmvSMYaV4oE`, and book `9788577800643` pages `66-72`. They are asserted
as workbook facts but are not silently substituted for the characterized
fixtures.

Before spending on the live book case, its ordered reconstruction can be
replayed entirely offline from the complete eight-page CG capture:

```sh
SAVED_BROWSERBASE_BOOK_FIXTURE='/Users/guilhermevalenca/Desktop/cg_pipeline/archive/cc-mod6-mtf/_misc/extraction/acquisition/book/output/25' \
  .venv/bin/python -m pytest -q tests/test_saved_ordered_book_fixture.py
```

That saved acceptance replaces Browserbase, Firecrawl, and model clients with
local fixture transports while preserving the real reader images and exact
page text.

## Acceptance and observed post-call ceilings

Every selected provider case must reach `passage-cleanup`, leave no runnable
work for that Source, contain no temporary or remote image links, resolve every
canonical asset through the content-addressed store, and create no KC tasks.
Terminal-work inspection covers acquisition, image candidates, grouped image
analysis, asset analysis, cleanup, STT chunks and attempts, document parsing,
PDF page analysis, figure localization, figure-region outcomes, and page text
states. It reports terminal failures separately from unfinished work.

Canonical image validation uses the same CommonMark parser family as the web
surface. It resolves inline and reference-style Markdown images and inspects
raw HTML image attributes (`src`, `srcset`, SVG `href`, input images, and video
posters); every rendered locator must be an exact same-origin
`/api/source-assets/<id>` URL whose bytes match the ledger hash.

The OpenRouter figures are **observed post-call ceilings**, not transactional
provider spending limits. Accounting includes successful and failed durable
rows, every STT fallback attempt, cleanup's primary/fallback attempt ledger,
and prior retries. An attempted row without numeric cost is reported as
`unpriced_attempts` and fails acceptance instead of disappearing from the
total. Firecrawl attempts include failed acquisition and parse rows; its credit
figures remain estimates.

| Case | Observed OpenRouter post-call ceiling | Other bounds | Quality gates |
| --- | ---: | ---: | --- |
| Article | `$0.12` | at most 4 Firecrawl attempts | at least 2,500 canonical characters, UML terms, terminal image outcomes, at least one useful local image |
| Knowledge | `$0.75` | one 60 minute deadline for all 11+4 stages | exact Source Publication pin, 11/11 local, 4/4 shared, manifest-scoped API and Universe nodes |
| PDF | `$0.15` | at most 32 estimated Firecrawl credits | 24 usable pages covered exactly once, no failed figure region, at least one figure, at least 30,000 characters, expected structure/content |
| Video | `$0.12` | 30 minute wall timeout | publisher-caption preflight, 360-410 seconds, 100-160 cues, no STT chunks, 1-20 frames, at least one useful frame |
| Book | `$0.20` | at most 16 estimated Firecrawl credits | exactly pages 198-205 with exact text and image bytes, forced OCR, eight-page diagnostics, at least one cropped figure |

A full extraction-only run therefore requires a global observed ceiling of at least `$0.59`;
use `$0.60` for `LIVE_E2E_MAX_OPENROUTER_USD`. An article+knowledge tracer
requires `$0.87`. The small fixed inputs,
per-case assertions, serial ordering, and stop-on-first-failure behavior bound
exposure, but the environment value cannot stop a provider call in flight.

`quality-report.json` is written atomically before each selected case and again
from a `finally` path. A quality assertion therefore leaves a durable failed
case with its sanitized error, wall time, terminal-work snapshot, and whatever
post-call usage/Firecrawl evidence could still be collected. The isolated
database and assets remain available when a reporting query itself fails.

## Safe commands

Never use `set -x`, `env`, or `printenv` around these commands. Start local
PostgreSQL, load the two existing credential files without echoing them, and
name every immutable input explicitly:

```sh
cd /Users/guilhermevalenca/Desktop/concept-universe
docker compose up -d postgres
cd /private/tmp/concept-universe-extraction
set -a
source /Users/guilhermevalenca/Desktop/concept-universe/.env
source /Users/guilhermevalenca/Desktop/cg_pipeline/.env
set +a
export LIVE_E2E_WORKBOOK='/Users/guilhermevalenca/Desktop/concept-universe/data/GRAD CC07 - 2026-2A.xlsx'
export LIVE_E2E_PDF='/Users/guilhermevalenca/Desktop/concept-universe-syllabus/.data/source-assets/sha256/e2/e22b6b7ea0d7e67151b1585ea3108a6eabcf76ccf6a03b69b29adbdbf4920f4f'
export RUN_LIVE_SOURCE_E2E='I_UNDERSTAND_THIS_CALLS_EXTERNAL_PROVIDERS'
```

The no-provider workbook tracer is:

```sh
export LIVE_E2E_CASES=xlsx
.venv/bin/python -m pytest -q tests/live_e2e --live-e2e
```

Run one paid Adapter at a time first, for example:

```sh
export LIVE_E2E_CASES=article
export LIVE_E2E_MAX_OPENROUTER_USD=0.12
.venv/bin/python -m pytest -q tests/live_e2e --live-e2e
```

The bounded unified article-to-Universe tracer is:

```sh
export LIVE_E2E_CASES=article,knowledge
export LIVE_E2E_MAX_OPENROUTER_USD=0.87
.venv/bin/python -m pytest -q tests/live_e2e --live-e2e
```

It authors a one-lesson validated test route around the characterized article;
it does not claim that the separate 64-lesson XLSX tracer contains that exact
Source identity. Any internal model retry whose prior attempt has no durable
cost is reported as unpriced and fails acceptance.

The PDF and book cases also require explicit upload consent:

```sh
export FIRECRAWL_ALLOW_PRIVATE_PDF_UPLOADS=1
export OPENROUTER_ALLOW_PRIVATE_PDF_PAGE_UPLOADS=1
```

Only after the isolated slices pass, run the full tracer:

```sh
export LIVE_E2E_CASES=xlsx,article,pdf,video,book
export LIVE_E2E_MAX_OPENROUTER_USD=0.60
.venv/bin/python -m pytest -q tests/live_e2e --live-e2e
```

Each run creates a fresh local database named
`universe_live_e2e_<run-id>` and preserves its evidence under
`.data/live-e2e/<run-id>/quality-report.json`. Cleanup is intentionally a
separate, explicit operator action after inspection.
