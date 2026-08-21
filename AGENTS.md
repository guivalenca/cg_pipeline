# Concept Universe

## Agent skills

### Issue tracker

Issues vivem no **Linear** (time `DEV`; `BISOPS` só para trabalho não-engenharia),
acessado pela API GraphQL com `curl` e `LINEAR_API_KEY`. GitHub Issues não é usado.
Ver `docs/agents/issue-tracker.md`.

### Triage labels

Grupo `Triage` no time `DEV`, seleção única: `needs-triage`, `needs-info`,
`ready-for-agent`, `ready-for-human`. O papel `wontfix` é o estado `Canceled`, não uma
label. Ver `docs/agents/triage-labels.md`.

### Domain docs

Contexto único: `CONTEXT.md` na raiz, ADRs em `docs/adr/`. Ver `docs/agents/domain.md`.
