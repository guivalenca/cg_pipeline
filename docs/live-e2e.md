# Live source-publication tests

Live provider tests are intentionally not part of this pilot's ordinary test
suite. The remaining `tests/live_e2e` directory contains the fail-closed gate
that future source-only tracers must inherit: both `--live-e2e` and
`RUN_LIVE_SOURCE_E2E=I_UNDERSTAND_THIS_CALLS_EXTERNAL_PROVIDERS` are required
before any test in that directory may run.

The donor's sanitized Source Publication evidence remains in
`source-publication-acceptance-2026-08-11.md`. It is historical evidence, not a
promise that the removed all-in-one tracer is available in this branch.
