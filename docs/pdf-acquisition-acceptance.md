# PDF acquisition acceptance — Process mining: From theory to practice

Date: 2026-08-10
Worktree: `/Users/guilhermevalenca/Desktop/concept-universe`
Branch: `main`
Source: `src-99e0b250dab5a4ac`

## Legacy diagnosis

The legacy acquisition was
`acq-5861fb8dc1fb4cfba355dbea3b06b2f5`. It stored one 68,126-character
Artifact using `pdftotext` / `manual-pdf-text.v1`, then stopped: there were no
Blocks and no cleanup job. The modal consequently displayed that intermediate
Artifact as though it were canonical Markdown.

The original asset (`asset-ac498822c73848578903b3b60b66715c`) is a
175,634-byte, unencrypted, tagged PDF with 24 pages and SHA-256
`e22b6b7ea0d7e67151b1585ea3108a6eabcf76ccf6a03b69b29adbdbf4920f4f`.
All 24 pages have usable text layers. The failure was therefore not a scanned
document or missing text: `pdftotext` preserved words but flattened the
row/column relationships in Table 1 (pages 6–7) and Table 2 (pages 14–16),
lost the directed branches and return loops in Figure 1 (page 8), weakened
heading boundaries, and retained the six-page bibliography. No page renders,
visual interpretations, cleanup decisions, or canonical-clean lineage existed.

## Implemented contract

- The original PDF remains an immutable external `source_asset`.
- Poppler records exact ordered text and a 144 dpi PNG render for every page.
- Stable `source_pdf_page` facts retain page provenance, hashes, text-layer
  status, and render identity.
- Technically bounded grouped visual calls receive page renders and their text
  layers. Forced structured results reconcile by stable page id.
- Raw text-layer, visually enriched, and clean Markdown are separate Artifacts
  with lineage. Visual atoms remain positioned on their pages.
- Scanned pages require OCR/description; any unresolved page puts publication
  in attention without erasing successful siblings.
- A terminal enriched PDF Artifact automatically enters the existing
  adapter-neutral Blocks → cuts → triage/refine/retriage cleanup queue.
- The UI withholds intermediate Artifacts and publishes only the latest clean
  Artifact.
- Enriched PDF-page images are primary evidence. Cleanup cannot remove them or
  drop their containing passage; conflicting model decisions are preserved in
  the ledger with `primary_enriched_image_preserved`. This PDF-only policy does
  not alter ordinary article-image cleanup.
- Stable call/page/asset identities make terminal retries idempotent and avoid
  duplicate paid calls or immutable facts.

## Page-aware baseline UI acceptance run

The PDF was uploaded through the Syllabus UI; no CLI cleanup step was used.

| fact | result |
| - | - |
| acquisition | `acq-386acdab53734a8c8d80ea01ab14384b` |
| cleanup job | `cleanup-386acdab53734a8c8d80ea01ab14384b` |
| cleanup | `pc-526e0cd084424b40a34bbb0cab099f60` |
| raw Artifact | `src-99e0b250dab5a4ac:snap:acq-386acdab53734a8c8d80ea01ab14384b:01:raw-markdown` (57,741 characters) |
| enriched Artifact | `src-99e0b250dab5a4ac:snap:acq-386acdab53734a8c8d80ea01ab14384b:01:markdown` (71,150 characters) |
| clean Artifact | `src-99e0b250dab5a4ac:snap:acq-386acdab53734a8c8d80ea01ab14384b:01:markdown:clean:pc-526e0cd084424b40a34bbb0cab099f60` (58,477 characters) |
| page outcomes | 24/24 succeeded; 24 text-layer, 0 scanned; 0 unresolved |
| retained visuals | pages 6, 7, 8, 14, 15, 16 |
| passage outcomes | 13 terminal passages: 12 keep, 1 drop, 0 unknown, 0 refinements |
| UI publication | `passage-cleanup`; clean-only state |

The rendered modal preserved both pages of Table 1, including the page-7
“Concurrent processes” continuation; Figure 1's decisions and backwards loops;
and all three pages of Table 2. Visuals appear in ascending page order. Ordinary
page text is not repeated as full-page OCR. `5. Conclusions` is a separate
heading, pages 20–24 and the `References` heading are absent, and the clean
document ends with the teaching content on page 19. The structural visual
policy was not required to override this run's model verdicts; its drop and
refinement conflict paths are covered by regression tests.

## Usage and timing

| stage | calls | prompt tokens | completion tokens | total tokens | cost | stage/call time |
| - | -: | -: | -: | -: | -: | -: |
| PDF page analysis v002 / Gemini 2.5 Flash | 1 | 24,557 | 4,524 | 29,081 | $0.018677100 | 28.203 s |
| passage cuts v001 / DeepSeek v4 Flash | 1 | 19,133 | 81 | 19,214 | $0.002682005 | 8.398 s |
| passage triage v004 / DeepSeek v4 Flash | 13 | 237,684 | 1,981 | 239,665 | $0.021831607 | 38.461 s |
| **Total** | **15** | **281,374** | **6,586** | **287,960** | **$0.043190712** | **75.062 s model-stage time** |

Acquisition wall time was 35.044 seconds and cleanup wall time was 47.007
seconds, for 82.051 seconds from UI queue creation to clean publication.

## Verification

The complete integrated `main` suite passes: **531 passed**, with the
pre-existing Starlette/httpx deprecation warning. Coverage includes textual,
mixed, and scanned PDFs; ordered page provenance; technical batching and
stable reconciliation; per-page failure/attention; retry idempotency; automatic
cleanup queueing; intermediate-artifact withholding; latest-clean selection;
PDF primary-visual preservation; and unchanged article/manual-image behavior.

## Firecrawl structural retest

The page-aware selector above was superseded by ADR 0017. A new isolated UI
upload (`acq-1e9d06e098454fce8977896063b563f7`) sent the 24-page PDF once to
Firecrawl `/v2/parse`. It completed in 6.992 seconds, returned 55,795 Markdown
characters and zero image URLs, and recorded an estimate of 24 credits. The
result contains 20 pipe-table lines: Table 1 and Table 2 are structural
Markdown tables rather than retained page screenshots.

Only page 8 matched the figure-caption candidate rule. Gemini 2.5 Flash located
one region; no other PDF page was exported to OpenRouter. The first box exposed
a real defect by describing the whole flowchart while cropping its lower and
left portions. The v002 retest replaced positional arrays with named
coordinates and cost $0.0058052 (17,290 tokens, 4.496 seconds), but still left
`Output` and `End` below its lower edge.

The final implementation therefore treats model geometry as advisory. Poppler
located the Figure 1 caption at normalized y=549, and the local completion rule
changed the model box `[268, 89, 730, 399]` to `[268, 89, 730, 539]`. The
resulting 550×758 PNG contains Start, all three phases, every decision and
feedback loop, Output, and End, while excluding the caption and following
prose. This final correction reused the stored Firecrawl and Gemini results and
made no further provider call.

## Final structural end-to-end run

The final browser-triggered run used the structural Firecrawl path and the
local geometry completion rule from the start:

| fact | result |
| - | - |
| acquisition | `acq-5a12333b4abc4b459b4db77ae0a892d2` |
| cleanup job | `cleanup-5a12333b4abc4b459b4db77ae0a892d2` |
| cleanup | `pc-0ffbf7968ebf45f29443d71343e9e4a1` |
| clean Artifact | `src-99e0b250dab5a4ac:snap:acq-5a12333b4abc4b459b4db77ae0a892d2:01:markdown:clean:pc-0ffbf7968ebf45f29443d71343e9e4a1` |
| Firecrawl | 24 pages, 55,795 raw Markdown characters, 20 table rows, estimated 24 credits |
| Gemini | page 8 only, one call, prompt `pdf-figure-localization/v002`, 17,296 tokens, $0.005829 |
| figure | `pdf-figure-48228ca37059cdc74fee0e399b7ba0e0`, 549×759, complete flowchart only |
| cleanup | 20 passages: 18 keep, 2 drop, 0 unknown |
| clean Markdown | 44,716 characters, 3 rendered tables and 1 local image |

Gemini returned `[268, 88, 729, 519]`. Poppler located the caption at y=549,
so deterministic code extended only the lower edge to y=539. The published
crop contains the full diagram and excludes the caption and unrelated prose.
The earlier two attempts were development/acceptance iterations of the crop
contract, not retries in this final job: the final job made one Gemini call.
