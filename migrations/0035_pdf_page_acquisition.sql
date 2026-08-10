-- Page-aware PDF evidence. The uploaded PDF remains the immutable primary
-- asset; deterministic page text and page renders are separate facts, while
-- grouped visual readings remain stamped interpretations.

ALTER TABLE source_asset DROP CONSTRAINT source_asset_kind_check;
ALTER TABLE source_asset ADD CONSTRAINT source_asset_kind_check CHECK (
    kind IN ('pdf', 'pdf_page', 'screenshot', 'image', 'article_image')
);

ALTER TABLE source_asset DROP CONSTRAINT source_asset_kind_mime;
ALTER TABLE source_asset ADD CONSTRAINT source_asset_kind_mime CHECK (
    (kind = 'pdf' AND mime_type = 'application/pdf')
    OR (kind IN ('pdf_page', 'screenshot', 'image', 'article_image')
        AND mime_type LIKE 'image/%')
);

CREATE TABLE source_pdf_page (
    id                 TEXT PRIMARY KEY,
    acquisition_job_id TEXT NOT NULL,
    source_id          TEXT NOT NULL,
    pdf_asset_id       TEXT NOT NULL REFERENCES source_asset (id),
    page_number        INTEGER NOT NULL CHECK (page_number > 0),
    text_body          TEXT NOT NULL,
    text_sha256        TEXT NOT NULL CHECK (text_sha256 ~ '^[0-9a-f]{64}$'),
    text_layer_status  TEXT NOT NULL CHECK (text_layer_status IN ('usable', 'empty')),
    render_asset_id    TEXT NOT NULL UNIQUE REFERENCES source_asset (id),
    created_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (acquisition_job_id, page_number),
    FOREIGN KEY (acquisition_job_id, source_id)
        REFERENCES acquisition_job (id, source_id)
);

CREATE INDEX source_pdf_page_job_idx
    ON source_pdf_page (acquisition_job_id, page_number);

CREATE TRIGGER source_pdf_page_immutable
BEFORE UPDATE OR DELETE ON source_pdf_page
FOR EACH ROW EXECUTE FUNCTION reject_source_asset_mutation();

CREATE TABLE pdf_page_analysis_call (
    id                   TEXT PRIMARY KEY,
    acquisition_job_id   TEXT NOT NULL REFERENCES acquisition_job (id),
    pdf_asset_id         TEXT NOT NULL REFERENCES source_asset (id),
    batch_ordinal        INTEGER NOT NULL CHECK (batch_ordinal > 0),
    page_ids             JSONB NOT NULL CHECK (jsonb_typeof(page_ids) = 'array'),
    prompt_ref           TEXT NOT NULL,
    prompt_sha           TEXT NOT NULL CHECK (prompt_sha ~ '^[0-9a-f]{64}$'),
    requested_model      TEXT NOT NULL,
    input_manifest_hash  TEXT NOT NULL CHECK (
        input_manifest_hash ~ '^[0-9a-f]{64}$'
    ),
    status               TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed')
    ),
    attempt_count        INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    response_model       TEXT,
    provider             TEXT,
    usage                JSONB NOT NULL DEFAULT '{}',
    duration_ms          INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    failure_code         TEXT,
    diagnostics          JSONB NOT NULL DEFAULT '{}',
    created_at           timestamptz NOT NULL DEFAULT now(),
    finished_at          timestamptz,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (acquisition_job_id, batch_ordinal, prompt_ref),
    CONSTRAINT pdf_page_analysis_call_state_shape CHECK (
        (status IN ('queued', 'running') AND finished_at IS NULL)
        OR (status IN ('succeeded', 'failed') AND finished_at IS NOT NULL)
    ),
    CONSTRAINT pdf_page_analysis_call_failure_shape CHECK (
        (status = 'failed' AND failure_code IS NOT NULL)
        OR (status <> 'failed' AND failure_code IS NULL)
    )
);

ALTER TABLE source_asset_analysis
    DROP CONSTRAINT source_asset_analysis_purpose_check;
ALTER TABLE source_asset_analysis
    ADD CONSTRAINT source_asset_analysis_purpose_check CHECK (
        purpose IN (
            'article_image_relevance',
            'source_image_analysis',
            'manual_image_description',
            'pdf_page_analysis'
        )
    );
ALTER TABLE source_asset_analysis
    ADD COLUMN pdf_page_id TEXT REFERENCES source_pdf_page (id);
ALTER TABLE source_asset_analysis
    ADD COLUMN pdf_analysis_call_id TEXT REFERENCES pdf_page_analysis_call (id);

CREATE UNIQUE INDEX source_asset_analysis_pdf_page_call_idx
    ON source_asset_analysis (pdf_page_id, pdf_analysis_call_id)
    WHERE pdf_page_id IS NOT NULL;
