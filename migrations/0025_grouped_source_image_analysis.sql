-- Separate technical image acquisition from one source-level visual call.
ALTER TABLE source_image_candidate
    DROP CONSTRAINT source_image_candidate_status_check;

ALTER TABLE source_image_candidate
    ADD CONSTRAINT source_image_candidate_status_check CHECK (
        status IN (
            'queued', 'filtered', 'running', 'downloaded',
            'useful', 'not_important', 'failed'
        )
    );

ALTER TABLE source_image_candidate
    DROP CONSTRAINT source_image_candidate_state_shape;

ALTER TABLE source_image_candidate
    ADD CONSTRAINT source_image_candidate_state_shape CHECK (
        (status = 'queued' AND claim_token IS NULL AND finished_at IS NULL)
        OR (status = 'running' AND claim_token IS NOT NULL AND finished_at IS NULL)
        OR (status IN ('filtered', 'downloaded', 'useful', 'not_important', 'failed')
            AND claim_token IS NULL AND finished_at IS NOT NULL)
    );

-- Article image volume is unbounded; the manual upload adapter retains its
-- own explicit 50-file validation.
ALTER TABLE source_asset DROP CONSTRAINT source_asset_ordinal_check;
ALTER TABLE source_asset ADD CONSTRAINT source_asset_ordinal_positive
    CHECK (ordinal > 0);

CREATE TABLE source_image_analysis_call (
    id                   TEXT PRIMARY KEY,
    markdown_artifact_id TEXT NOT NULL REFERENCES artifact (id),
    prompt_ref           TEXT NOT NULL,
    prompt_sha           TEXT NOT NULL,
    requested_model      TEXT NOT NULL,
    input_manifest_hash  TEXT,
    status               TEXT NOT NULL CHECK (
        status IN ('waiting', 'queued', 'running', 'succeeded', 'failed', 'skipped')
    ),
    attempt_count        INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at         timestamptz NOT NULL DEFAULT now(),
    claimed_at           timestamptz,
    lease_expires_at     timestamptz,
    claim_token          TEXT,
    response_model       TEXT,
    provider             TEXT,
    usage                JSONB NOT NULL DEFAULT '{}',
    duration_ms          INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    failure_code         TEXT,
    diagnostics          JSONB NOT NULL DEFAULT '{}',
    created_at           timestamptz NOT NULL DEFAULT now(),
    finished_at          timestamptz,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (markdown_artifact_id, prompt_ref),
    CONSTRAINT source_image_analysis_call_state_shape CHECK (
        (status IN ('waiting', 'queued') AND claim_token IS NULL AND finished_at IS NULL)
        OR (status = 'running' AND claim_token IS NOT NULL AND finished_at IS NULL)
        OR (status IN ('succeeded', 'failed', 'skipped')
            AND claim_token IS NULL AND finished_at IS NOT NULL)
    ),
    CONSTRAINT source_image_analysis_call_failure_shape CHECK (
        (status = 'failed' AND failure_code IS NOT NULL)
        OR (status <> 'failed' AND failure_code IS NULL)
    )
);

CREATE INDEX source_image_analysis_call_claim_idx
    ON source_image_analysis_call (available_at, created_at, id)
    WHERE status IN ('queued', 'running');

ALTER TABLE source_asset_analysis
    DROP CONSTRAINT source_asset_analysis_purpose_check;

ALTER TABLE source_asset_analysis
    ADD CONSTRAINT source_asset_analysis_purpose_check CHECK (
        purpose IN (
            'article_image_relevance',
            'source_image_analysis',
            'manual_image_description'
        )
    );

ALTER TABLE source_asset_analysis
    ADD COLUMN analysis_call_id TEXT REFERENCES source_image_analysis_call (id);

CREATE INDEX source_asset_analysis_call_idx
    ON source_asset_analysis (analysis_call_id, source_asset_id);
