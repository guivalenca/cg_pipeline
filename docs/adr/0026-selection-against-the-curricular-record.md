# 0026: Selection judges the curricular record directly

Date: 2026-08-22
Status: accepted. Supersedes the Lesson Purpose and the counterfactual
survival criterion of ADR 0024.

## Context

ADR 0024 placed a generated, operator-editable Lesson Purpose between the
lesson's curricular record and KC Selection. The DEV-22 prototype tested how
to build it (branch `prototype/lesson-purpose`, commit 7abae20; 48 real
generations: 8 instruction meetings × 2 input levels × 3 samples,
deepseek-v4-flash reasoning high). The founder judged the outputs: on rich
records the generated purpose is the description reorganized into "existe
para" prose — no information gain; on poor records the model oscillates
per-sample between refusing and padding with domain knowledge not present in
the record; adding course/module context rescues poor on-topic lessons but
causes refusals on rich off-module ones, and no framing stopped that. No
method won because the step itself adds nothing over its inputs.

## Decision

**There is no Lesson Purpose artifact.** KC Selection consumes the lesson's
curricular record directly: title, description, subjects. Binding rules that
came out of the prototype:

- **Priority rule.** Title and description carry the lesson's intention;
  subjects detail it; when they diverge, title and description win. This
  rule lives in the KC Selection prompt.
- **Autoestudo metadata is inadmissible** for judging a lesson's intention —
  it reintroduces "summarize what the sources contain".
- **Admissible-input principle.** An input is admissible only if its change
  should legitimately change the output. The full course meeting list fails
  it; module topic and degree name are absent from the type-2 workbook and,
  if ever revisited, are operator-provided fields — moot while the
  record-only decision stands.
- **The criterion is optimization, not reduction.** The selected set is the
  one that best fulfills the lesson's curricular record. The counterfactual
  wording of ADR 0024 ("selected when removing it would materially
  reduce...") is rejected: elimination is itself reduction; the job is
  optimizing, and the counterfactual framing invites leniency.

## Consequences

- ADR 0024 stands in everything else: three checkpoints, locality of
  selection, Universe as the union of selections, zero-selected blocking,
  selection generations.
- ADR 0025 is amended: the stable meeting id and its reconciliation lineage
  are untouched; the purpose-validity toggle becomes a selection-validity
  toggle at the same screen.
- Sparse records now reach selection raw — nothing upstream repairs them.
  The weak-signal problem lands on the DEV-23 bench, which must include a
  sparse-record lesson ("Testes de desempenho" is the canonical case).
- Tool contracts for selection require the payload text fields, not only an
  enum — the prototype showed the model omitting text exactly on the torn
  cases.
- Prompt craft validated in the prototype and reused for selection: the
  intenção→objetivo essence, destination over prohibition, the schema as the
  single source of truth for format, and the founder's unslop pass. The
  approved prompt survives as the PROMPT constant in `purpose_bench.py` on
  the prototype branch.
