-- Article images are an additional, source-local acquisition branch.  The
-- text Markdown may succeed while individual images are still queued,
-- useful, filtered, or in need of attention.

ALTER TABLE artifact
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';

ALTER TABLE source_asset
    ADD COLUMN original_url TEXT;

ALTER TABLE source_asset
    DROP CONSTRAINT source_asset_kind_mime;

ALTER TABLE source_asset
    DROP CONSTRAINT source_asset_kind_check;

ALTER TABLE source_asset
    ADD CONSTRAINT source_asset_kind_check CHECK (
        kind IN ('pdf', 'screenshot', 'image', 'article_image')
    );

ALTER TABLE source_asset
    ADD CONSTRAINT source_asset_kind_mime CHECK (
        (kind = 'pdf' AND mime_type = 'application/pdf')
        OR (kind IN ('screenshot', 'image', 'article_image')
            AND mime_type LIKE 'image/%')
    );

CREATE TABLE source_image_candidate (
    id                 TEXT PRIMARY KEY,
    acquisition_job_id TEXT NOT NULL REFERENCES acquisition_job (id),
    source_id          TEXT NOT NULL REFERENCES source (id),
    snapshot_id        TEXT NOT NULL REFERENCES source_snapshot (id),
    markdown_artifact_id TEXT NOT NULL REFERENCES artifact (id),
    ordinal            INTEGER NOT NULL CHECK (ordinal > 0),
    original_url       TEXT NOT NULL CHECK (btrim(original_url) <> ''),
    alt_text           TEXT NOT NULL DEFAULT '',
    placement          JSONB NOT NULL DEFAULT '{}',
    status             TEXT NOT NULL CHECK (
        status IN ('queued', 'filtered', 'running', 'useful', 'not_important', 'failed')
    ),
    filter_reason      TEXT,
    failure_code       TEXT,
    diagnostics        JSONB NOT NULL DEFAULT '{}',
    asset_id           TEXT,
    analysis_id        TEXT,
    attempt_count      INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at       timestamptz NOT NULL DEFAULT now(),
    claimed_at         timestamptz,
    lease_expires_at   timestamptz,
    claim_token        TEXT,
    finished_at        timestamptz,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (acquisition_job_id, ordinal),
    CONSTRAINT source_image_candidate_state_shape CHECK (
        (status = 'queued' AND claim_token IS NULL AND finished_at IS NULL)
        OR (status = 'running' AND claim_token IS NOT NULL AND finished_at IS NULL)
        OR (status IN ('filtered', 'useful', 'not_important', 'failed')
            AND claim_token IS NULL AND finished_at IS NOT NULL)
    ),
    CONSTRAINT source_image_candidate_failure_shape CHECK (
        (status = 'failed' AND failure_code IS NOT NULL)
        OR (status <> 'failed' AND failure_code IS NULL)
    )
);

CREATE INDEX source_image_candidate_claim_idx
    ON source_image_candidate (available_at, created_at, id)
    WHERE status IN ('queued', 'running');

CREATE INDEX source_image_candidate_source_idx
    ON source_image_candidate (source_id, created_at, ordinal);

CREATE INDEX source_image_candidate_markdown_idx
    ON source_image_candidate (markdown_artifact_id, ordinal);

CREATE TABLE source_asset_analysis (
    id                 TEXT PRIMARY KEY,
    source_asset_id    TEXT NOT NULL REFERENCES source_asset (id),
    purpose            TEXT NOT NULL CHECK (
        purpose IN ('article_image_relevance', 'manual_image_description')
    ),
    status             TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')),
    prompt_version     TEXT NOT NULL,
    requested_model    TEXT,
    response_model     TEXT,
    provider           TEXT,
    result             JSONB NOT NULL DEFAULT '{}',
    usage              JSONB NOT NULL DEFAULT '{}',
    duration_ms        INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    failure_code       TEXT,
    diagnostics        JSONB NOT NULL DEFAULT '{}',
    created_at         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_asset_analysis_shape CHECK (
        (status = 'succeeded' AND failure_code IS NULL)
        OR (status = 'failed' AND failure_code IS NOT NULL)
    )
);

CREATE INDEX source_asset_analysis_asset_idx
    ON source_asset_analysis (source_asset_id, created_at, id);

ALTER TABLE source_image_candidate
    ADD CONSTRAINT source_image_candidate_asset_fk
    FOREIGN KEY (asset_id) REFERENCES source_asset (id);

ALTER TABLE source_image_candidate
    ADD CONSTRAINT source_image_candidate_analysis_fk
    FOREIGN KEY (analysis_id) REFERENCES source_asset_analysis (id);
