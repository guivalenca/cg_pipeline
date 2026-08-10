-- One paid Firecrawl parse per durable manual-upload job. The result is kept
-- separately from the final artifact so a reclaimed worker can resume without
-- paying to parse the same immutable PDF again.

CREATE TABLE pdf_document_parse_call (
    id                   TEXT PRIMARY KEY,
    acquisition_job_id   TEXT NOT NULL REFERENCES acquisition_job (id),
    pdf_asset_id         TEXT NOT NULL REFERENCES source_asset (id),
    parser_ref           TEXT NOT NULL,
    input_sha256         TEXT NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
    options              JSONB NOT NULL DEFAULT '{}',
    status               TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed')
    ),
    attempt_count        INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    provider_attempts    INTEGER NOT NULL DEFAULT 0 CHECK (provider_attempts >= 0),
    result               JSONB NOT NULL DEFAULT '{}',
    failure_code         TEXT,
    diagnostics          JSONB NOT NULL DEFAULT '{}',
    created_at           timestamptz NOT NULL DEFAULT now(),
    finished_at          timestamptz,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (acquisition_job_id, pdf_asset_id, parser_ref),
    CONSTRAINT pdf_document_parse_call_state_shape CHECK (
        (status IN ('queued', 'running') AND finished_at IS NULL)
        OR (status IN ('succeeded', 'failed') AND finished_at IS NOT NULL)
    ),
    CONSTRAINT pdf_document_parse_call_failure_shape CHECK (
        (status = 'failed' AND failure_code IS NOT NULL)
        OR (status <> 'failed' AND failure_code IS NULL)
    )
);

CREATE INDEX pdf_document_parse_call_job_idx
    ON pdf_document_parse_call (acquisition_job_id, created_at, id);
