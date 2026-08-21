# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

This repo is **single-context**: one `CONTEXT.md` at the root, one `docs/adr/` directory.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the glossary of domain terms, each with an `_Avoid_`
  line naming the synonyms this project rejects.
- **`docs/adr/`** — read the ADRs that touch the area you're about to work in.
  `docs/adr/README.md` explains the numbering and points at the maintained design
  narrative, `docs/concept-system-vision-compilation.md`.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't
suggest creating them upfront. The `/domain-modeling` skill (reached via
`/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or
decisions actually get resolved.

## File structure

```
/
├── CONTEXT.md
├── docs/
│   ├── adr/
│   │   ├── README.md
│   │   ├── 0001-facts-versus-interpretations.md
│   │   └── …
│   └── concept-system-vision-compilation.md
└── src/universe/
```

If this repo ever splits into multiple bounded contexts, the layout becomes a root
`CONTEXT-MAP.md` pointing at one `CONTEXT.md` per context, with context-scoped ADRs under
`src/<context>/docs/adr/`. Until that file exists, treat the repo as single-context.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a
hypothesis, a test name), use the term as defined in `CONTEXT.md` — and honour the
`_Avoid_` list, which exists precisely because those synonyms caused confusion before.

If the concept you need isn't in the glossary yet, that's a signal — either you're
inventing language the project doesn't use (reconsider) or there's a real gap (note it for
`/domain-modeling`).

## Flag ADR conflicts

An ADR here closes only when the founder closes it explicitly. If your output contradicts
an existing ADR, surface it rather than silently overriding:

> _Contradicts ADR-0008 (frozen KC ids) — but worth reopening because…_
