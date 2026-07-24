# 0002: Postgres plus pgvector, no additional stores

Date: 2026-07-23 (records the standing technology verdict)
Status: accepted

## Context

The grouping loop needs embedding search; the rest of the system needs
ordinary relational storage with transactions. Graph databases, GraphRAG
stacks, and dedicated vector databases were evaluated and rejected during the
technology research phase (`docs/technology-foundations.md`).

## Decision

Postgres stores both ledgers and every interpretation layer. pgvector, inside
the same database, handles embedding search, keeping vectors and rows under
the same transactions. No graph database, no separate vector store.

## Consequences

- Blocking-stage search is transactional with the rows it serves.
- Swapping embedding models is a re-embed of derived data, not a migration.
- Infrastructure stays within what the team already operates.
