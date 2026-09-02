# 0002: PostgreSQL plus a local Asset Store

Date: 2026-07-23 (records the standing technology verdict)
Status: accepted

## Context

The source ledger, queues, leases, and publication lineage need relational
transactions. Original PDFs, images, and video frames are too large to store
comfortably as database values but still need immutable content identity.

## Decision

PostgreSQL 16 stores the source ledger, every cleanup interpretation, and all
operational queues and leases. Binary Source Assets live in one
application-managed filesystem, addressed by SHA-256; PostgreSQL stores their
hashes, lineage, order, MIME type, and storage keys.

The pilot has no vector extension, graph database, Redis, Celery, S3-compatible
backend, or separate queue service.

## Consequences

- Queue claims and publication writes are transactional.
- Binary integrity is verified whenever an Asset is stored or read.
- Web and worker containers must share the same Asset Store volume.
