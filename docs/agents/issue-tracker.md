# Issue tracker: Linear

Issues e specs deste repo vivem no **Linear**, workspace `thecompanion`, conta
`guilherme@thecompanion.com.br`.

| Time              | Key      | Team id                                | Uso                                                    |
| ----------------- | -------- | -------------------------------------- | ------------------------------------------------------ |
| DEV Companion     | `DEV`    | `a0525884-099d-4fde-bc8e-8c0a6ccb9bd6` | **Padrão.** Todo trabalho de engenharia.               |
| BisOps Companion  | `BISOPS` | `1b1da05c-923e-4933-9145-5e72665771a0` | Não-engenharia (contábil, fornecedor, deck, processo). |

Crie sempre em `DEV`, a não ser que o founder diga o contrário ou o item claramente não
seja engenharia. Na dúvida entre os dois times, pergunte — não chute.

Não existe MCP do Linear nem CLI aqui. Tudo passa pela **API GraphQL** em
`https://api.linear.app/graphql` via `curl`.

## Auth

A chave está no `.env` como `LINEAR_API_KEY`. Carregue antes de qualquer chamada:

```bash
set -a && source .env && set +a
```

O header é a chave crua — **sem** prefixo `Bearer`:

```
Authorization: $LINEAR_API_KEY
```

Se `LINEAR_API_KEY` não existir, pare e avise o founder. Não invente um lugar alternativo
para gravar a issue.

## O formato da chamada

Toda operação é o mesmo POST. Defina uma vez por sessão e reutilize:

```bash
linear() {
  curl -s -X POST https://api.linear.app/graphql \
    -H "Content-Type: application/json" \
    -H "Authorization: $LINEAR_API_KEY" \
    --data @-
}
```

Monte o payload com `jq -n --arg` para que corpos multi-linha e aspas sobrevivam:

```bash
jq -n --arg q 'query { viewer { id name } }' '{query: $q}' | linear
```

Leia `success` na resposta e mostre `errors` na íntegra quando falhar. Um `200` com array
`errors` é falha.

**Cuidado com zsh:** `GID`, `UID` e `EUID` são parâmetros inteiros especiais do shell.
Nomear uma variável `GID` para guardar um UUID quebra com `bad math expression`. Use
outro nome.

## Resolvendo ids

Mutations do Linear pedem UUID, não nome. Os ids de time estão na tabela acima e são
estáveis. **Ids de label e de estado devem ser resolvidos em runtime** e guardados só
para a sessão — nunca escritos dentro de um skill ou commitados.

**Labels de um time:**

```bash
jq -n --arg q 'query { team(id: "a0525884-099d-4fde-bc8e-8c0a6ccb9bd6") { labels { nodes { id name isGroup parent { name } } } } }' '{query: $q}' | linear
```

**Estados do workflow:**

```bash
jq -n --arg q 'query { team(id: "a0525884-099d-4fde-bc8e-8c0a6ccb9bd6") { states { nodes { id name type } } } }' '{query: $q}' | linear
```

Os dois times usam os estados padrão: Backlog (`backlog`), Todo (`unstarted`),
In Progress (`started`), Done (`completed`), Canceled (`canceled`), Duplicate (`duplicate`).

**Você mesmo** (para atribuir): `query { viewer { id } }`.

## Operações

- **Criar issue** — `issueCreate`. Campos: `teamId` (obrigatório), `title`,
  `description` (Markdown), `labelIds`, `assigneeId`, `stateId`, `parentId`, `priority`.

  ```bash
  jq -n --arg t 'Título aqui' --arg d "$(cat body.md)" --arg team "$TEAM_ID" '
    {query: "mutation($i: IssueCreateInput!) { issueCreate(input: $i) { success issue { id identifier url } } }",
     variables: {i: {teamId: $team, title: $t, description: $d}}}' | linear
  ```

  Reporte o `identifier` (ex. `DEV-17`) e a `url` de volta ao founder.

- **Ler issue** — `issue(id: "DEV-17")` aceita o identificador humano além do UUID.
  Puxe os comentários na mesma chamada:

  ```graphql
  query { issue(id: "DEV-17") {
    id identifier title description url
    state { name type } labels { nodes { name } } assignee { name }
    parent { identifier } children { nodes { identifier title } }
    comments { nodes { body user { name } createdAt } }
  } }
  ```

- **Listar issues** — `issues(filter: …)`, sempre com escopo de time:

  ```graphql
  query { issues(filter: {
    team: { key: { eq: "DEV" } }
    state: { type: { nin: ["completed", "canceled"] } }
    labels: { name: { eq: "needs-triage" } }
  }) { nodes { identifier title url labels { nodes { name } } assignee { name } } } }
  ```

- **Comentar** — `commentCreate(input: { issueId: "<uuid>", body: "..." })`. Aqui vai o
  **UUID**, não o `DEV-17`; resolva antes com uma query `issue`.

- **Aplicar labels** — `issueUpdate(id: "DEV-17", input: { labelIds: [...] })`. `labelIds`
  **substitui o conjunto inteiro**. Leia as labels atuais primeiro e mande a união; para
  remover uma, mande o conjunto menos ela. Regras de triagem em
  `docs/agents/triage-labels.md`.

- **Criar label faltante** — `issueLabelCreate(input: { name, teamId, parentId, color })`.
  Confira as labels do time antes e reutilize em vez de duplicar.

- **Fechar** — não existe mutation de close. Comente o motivo e mova o estado:
  `issueUpdate(id: …, input: { stateId: "<id de Done ou Canceled>" })`.

## PRs como superfície de entrada

**Não.** O remote GitHub (`thecompanion-tech/concept-universe`) é só código — GitHub
Issues não é usado e PR não é fila de triagem. `/triage` lê o Linear.

## Quando um skill diz "publique no issue tracker"

Crie uma issue no time `DEV` e reporte `identifier` e `url`.

## Quando um skill diz "busque o ticket"

Rode a query `issue(id: "<identificador>")` acima, com comentários.

## Operações de wayfinding

Usadas pelo `/wayfinder`. O **mapa** é uma issue; os tickets são **sub-issues** dela.

- **Mapa** — issue com label `wayfinder:map`, com o corpo Notes / Decisions-so-far / Fog
  em `description`. A label `wayfinder:*` ainda não existe no `DEV`; crie na primeira vez,
  **fora** do grupo `Triage` (grupo é seleção única e ocuparia o slot de estágio).
- **Ticket filho** — issue criada com `parentId` apontando para o UUID do mapa. É a
  sub-issue nativa do Linear e aparece na UI. Label `wayfinder:<tipo>`
  (`research` / `prototype` / `grilling` / `task`).
- **Bloqueio** — `issueRelationCreate(input: { issueId: "<bloqueadora>", relatedIssueId: "<bloqueada>", type: blocks })`.
  Atenção à direção: `type: blocks` significa que `issueId` **bloqueia** `relatedIssueId`
  (verificado em 2026-08-21; a bloqueada mostra a aresta em `inverseRelations`). Leia
  `relations` / `inverseRelations` para ver as arestas. Desbloqueada quando todo
  bloqueador está em estado `completed` ou `canceled`.
- **Frontier** — liste os filhos abertos do mapa
  (`filter: { parent: { id: { eq: "<uuid do mapa>" } } }`), descarte os com bloqueador
  aberto ou com `assignee`; o primeiro na ordem do mapa vence.
- **Claim** — `issueUpdate(id: …, input: { assigneeId: "<id do viewer>" })`, a primeira
  escrita da sessão.
- **Resolver** — `commentCreate` com a resposta, mova para Done, e acrescente um ponteiro
  de contexto no Decisions-so-far do mapa.
