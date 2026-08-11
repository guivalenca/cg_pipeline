# Unified source-publication acceptance — 2026-08-11

This is the sanitized acceptance record for the first consolidated extraction
pipeline. The local quality reports and isolated PostgreSQL databases remain
available for forensic replay; source bytes, credentials, provider responses,
and private reader URLs are intentionally not committed.

## Acceptance boundary

Every media Adapter must publish the same domain result: immutable Source
Evidence followed by non-empty Canonical Source Markdown. A case passes only
when its acquisition, visual work, PDF child work, and cleanup are terminal;
every rendered image locator is a local `source_asset`; required subject matter
is present; and every observable provider attempt is priced and stays below the
case's observed post-call ceiling.

The branch passed its provider-free suite immediately before the final book
run: **635 passed, 4 gated live tests skipped**. The only warning was the
pre-existing Starlette/httpx deprecation notice.

## Accepted vertical slices

| Case | Run | Quality result | External-use evidence |
| --- | --- | --- | --- |
| XLSX reconciliation | `xlsx-20260811b` | 64 lessons; 130 references; 129 linked; 128 logical Sources; one missing concrete scope; byte-identical reimport was idempotent | No provider calls |
| Article | `article-20260811c` | 6,866 canonical characters; one pedagogical GIF retained locally; six non-teaching/invalid candidates failed closed; no pending work | Firecrawl: 1 successful attempt, 0 estimated credits; OpenRouter: 15/15 priced attempts, **$0.006319142** |
| YouTube video | `video-20260811a` | Publisher-caption route; 386 seconds; 129 ordered cues; seven retained frame assets (five useful, two not important); 9,059 canonical characters; no pending work | OpenRouter: 13/13 priced attempts, **$0.006568954** |
| PDF | `pdf-20260811a` | Pinned SHA-256 `e22b6b7ea0d7e67151b1585ea3108a6eabcf76ccf6a03b69b29adbdbf4920f4f`; 24/24 usable pages; three localization batches; four placed figures; 49,994 canonical characters; no pending work | Firecrawl: 1 successful parse, 24 estimated credits; OpenRouter: 19/19 priced attempts, **$0.037692480** |
| Book | `book-20260811c` | ISBN `9788522128303`, pages 198–205; 8/8 exact reader-text pages captured in one attempt; forced OCR; nine placed figures; 31,311 canonical characters; no pending work | Firecrawl: 1 successful parse, 8 estimated credits; OpenRouter: 11/11 priced attempts, **$0.019681874** |

All four paid cases completed below their individual observed ceilings
(`$0.12`, `$0.12`, `$0.15`, and `$0.20`, respectively). These are audit
ceilings evaluated after calls, not provider-side spending controls.

## Failures that hardened the pipeline

The accepted results were not obtained by weakening quality gates:

- The first article run exposed an unsupported public GIF; after its original
  bytes and bounded first-frame analysis were implemented, the second run
  exposed the missing `source_asset` MIME constraint. Migration 0049 and a
  full roundtrip regression fixed both layers before the accepted third run.
- The first book run stopped after pages 198–199 with `book_page_clipped`.
  Investigation proved Playwright's element screenshot composited fixed reader
  navigation over the clean `IMG#pbk-page`, truncating Figure 6.2. Capture v5
  now retrieves that authenticated, same-book HTTPS image resource directly,
  validates dimensions/size/decodability, normalizes it losslessly, and retains
  the old guarded screenshot only as fallback. The accepted run captured all
  eight pages on its first attempt.
- The next book run reached canonical publication but exposed a stale tracer
  assertion: the durable ledger stores `pdf_mode=ocr`, while only the Firecrawl
  transport serializes that intent as `parsers=[{type: pdf, mode: ocr}]`.
  Provider-free tests cover the mapping; the final run validates the durable
  contract.

## Reproduction and evidence

The gated commands and immutable input locations are documented in
[`live-e2e.md`](live-e2e.md). Local reports live under
`.data/live-e2e/<run-id>/quality-report.json`; their matching databases are
`universe_live_e2e_<run_id>`. Ordinary `pytest` cannot make provider calls:
the suite requires both `--live-e2e` and the exact consent sentinel, plus an
explicit case list.
