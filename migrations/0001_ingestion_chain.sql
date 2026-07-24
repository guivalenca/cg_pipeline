-- Ingestion chain, first three links: source -> source_snapshot -> artifact.
-- These are permanent fact records. Rows are inserted, never updated or
-- deleted; a better acquisition or a better extraction is a new row beside
-- the old one.

CREATE EXTENSION IF NOT EXISTS vector;

-- The logical thing a teacher chose. Identity is the stable external handle
-- (canonical URL, video id, ISBN); everything else about it may change.
CREATE TABLE source (
    id         TEXT PRIMARY KEY,
    identity   JSONB NOT NULL,
    title      TEXT,
    media_type TEXT,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- The source's material as it was at a moment in time. An acquisition that
-- failed is still a fact: status 'failed', no hash, the reason in
-- failure_note. captured_at is NULL when the capture date is unknown, as with
-- archival imports.
CREATE TABLE source_snapshot (
    id           TEXT PRIMARY KEY,
    source_id    TEXT NOT NULL REFERENCES source (id),
    captured_at  timestamptz,
    content_hash TEXT,
    status       TEXT NOT NULL CHECK (status IN ('ok', 'failed')),
    failure_note TEXT,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_snapshot_status_shape CHECK (
        (status = 'ok' AND content_hash IS NOT NULL AND failure_note IS NULL)
        OR (status = 'failed' AND content_hash IS NULL)
    )
);

CREATE INDEX source_snapshot_source_idx ON source_snapshot (source_id);

-- A processed form of a snapshot, made for model consumption: extracted
-- Markdown, a transcript, OCR output. The producing tool is part of the fact.
CREATE TABLE artifact (
    id           TEXT PRIMARY KEY,
    snapshot_id  TEXT NOT NULL REFERENCES source_snapshot (id),
    kind         TEXT NOT NULL,
    tool         TEXT NOT NULL,
    tool_version TEXT,
    body         TEXT NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX artifact_snapshot_idx ON artifact (snapshot_id);
