-- Durable bounding-box interpretations for candidate PDF page renders. These
-- calls are independent from the Firecrawl document parse and remain opt-in.

CREATE TABLE pdf_figure_localization_call (
    id                   TEXT PRIMARY KEY,
    acquisition_job_id   TEXT NOT NULL REFERENCES acquisition_job (id),
    pdf_asset_id         TEXT NOT NULL REFERENCES source_asset (id),
    batch_ordinal        INTEGER NOT NULL CHECK (batch_ordinal > 0),
    page_ids             JSONB NOT NULL CHECK (jsonb_typeof(page_ids) = 'array'),
    prompt_ref           TEXT NOT NULL,
    input_manifest_hash  TEXT NOT NULL CHECK (
        input_manifest_hash ~ '^[0-9a-f]{64}$'
    ),
    status               TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed')
    ),
    attempt_count        INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    requested_model      TEXT,
    response_model       TEXT,
    provider             TEXT,
    usage                JSONB NOT NULL DEFAULT '{}',
    duration_ms          INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    result               JSONB NOT NULL DEFAULT '{}',
    failure_code         TEXT,
    diagnostics          JSONB NOT NULL DEFAULT '{}',
    created_at           timestamptz NOT NULL DEFAULT now(),
    finished_at          timestamptz,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (acquisition_job_id, pdf_asset_id, batch_ordinal, prompt_ref),
    CONSTRAINT pdf_figure_localization_call_state_shape CHECK (
        (status IN ('queued', 'running') AND finished_at IS NULL)
        OR (status IN ('succeeded', 'failed') AND finished_at IS NOT NULL)
    ),
    CONSTRAINT pdf_figure_localization_call_failure_shape CHECK (
        (status = 'failed' AND failure_code IS NOT NULL)
        OR (status <> 'failed' AND failure_code IS NULL)
    )
);

CREATE INDEX pdf_figure_localization_call_job_idx
    ON pdf_figure_localization_call (acquisition_job_id, batch_ordinal, id);
