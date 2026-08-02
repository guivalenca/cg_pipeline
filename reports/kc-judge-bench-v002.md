# kc-judge v002 bench: one call per pair, simplified candidates (2026-08-02)

Two runs over the r0130 corpus (33 statements), same prompt and tool:
`prompts/kc-judge/v002-surmise-pair.md` + `tool-v002.json` — both directions
judged in ONE call per pair. Candidate config per the founder decisions of
2026-08-02: floor 0.70, semantic cap 6, lexical top-5, axis filter applied
after the cap, legacy/dense generators off, merges = clear_yes in both
directions only. 100 pairs = 100 calls per run, 16 workers, throughput-sorted
non-low-bit OpenRouter routing (now wired into the runner defaults).

| run | model | calls | cost | wall time | file |
| - | - | - | - | - | - |
| pro | deepseek-v4-pro thinking high | 100 | $0.40 | ~4 min | deepseek-judge-v002-pair.json |
| flash | deepseek-v4-flash thinking high | 100 | $0.08 | ~3 min | deepseek-flash-judge-v002-pair.json |
| (reference) v001 two-call | deepseek-v4-pro thinking high | 558 | $1.10 | ~15 min | deepseek-judge-v001-surmise.json |

## Does one call per pair hold quality? Yes.

- Pro v002 vs the v001 two-call run, per direction over the 100 shared pairs:
  87.5% binary agreement (75% exact on the 4-level scale) — inside the noise
  band the v001 bench measured between judges (deepseek vs Opus was 90%).
- The clear duplicate core is identical across pro v002, the old run, and
  Opus: 17|18 (n-gram), 16|32 (dimensionality limitation), 8|10
  (vector-building), plus 27|28 (tokenization) with everyone except flash.
- All boundary flips orbit item 0, the known compound BOW-definition hub
  (0|24 lost one direction, 0|21 gained one). Its component {0,14,21} fails
  the perfect-clique rule (14|21 judged likely/clear_no) and correctly does
  not merge: the compound hub stays quarantined by under-merging, exactly the
  intended failure mode.
- Cost of pair mode: middle-level hedging rose from 10.6% (v001) to ~17.5%
  (both v002 runs). Under clear-yes-only merges this only makes merging more
  conservative, which is the chosen direction.

## Verdict on flash: zero false merges, strictly more conservative.

Flash found 3 doubles, all of them inside pro's 6 — no flash-only double in
100 pairs, so no measured false-merge risk. Its misses are genuine denials
(clear_no / unlikely on one direction), not hedges: it rejects 0|14, 0|21 and
the arguable 27|28 (does knowing what a token is imply mastering
tokenization? flash says unlikely; pro and Opus say yes).

## Resulting v1 groups (clique rule, clear-yes only)

- pro: 4 composite KCs — {17,18} {16,32} {27,28} {8,10}; 33 → 29 KCs.
- flash: 3 composite KCs — {17,18} {16,32} {8,10}; 33 → 30 KCs.
- The item-0 neighborhood stays unmerged under both (no clique closes).
- 0 closure pairs were added at runtime in either run.

## Cost projection and the open default

Judging per source: pro $0.40, flash $0.08. At 125 sources/module: pro ≈ $50
(judging alone exceeds the $40/module cap), flash ≈ $10. Extraction-stage
cost per source is not yet measured from the run ledger; measure before
claiming a module total.

Default judge: **deepseek-v4-pro thinking, decided by the founder
2026-08-02** over the 5x-cheaper flash. Rationale: flash surfaces far fewer
mutual flags (3 vs 8), and the flags themselves are information about the
corpus — a judge that shows more behavior is worth the cost. Ledger note:
the choice stays recomputable — verdict facts are stamped, and a later
re-judge of the whole universe rebuilds the merge layer without losing
anything.

Providers actually used (throughput-sort behavior confirmed): pro
concentrated on Novita 98/100 with spillover to Together/DigitalOcean; flash
spread Fireworks/SiliconFlow/Parasail as its fastest lane saturated.
