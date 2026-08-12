-- A visual-only video is interpreted once as an ordered teaching-beat
-- document. Reuse the grouped visual-call ledger rather than paying for a
-- second source-image interpretation of the representative frames.

ALTER TABLE source_image_analysis_call
    ADD COLUMN operation_kind TEXT NOT NULL DEFAULT 'source_image_analysis';

ALTER TABLE source_image_analysis_call
    ADD CONSTRAINT source_image_analysis_call_operation_kind_check CHECK (
        operation_kind IN ('source_image_analysis', 'video_teaching_beats')
    );

ALTER TABLE source_image_analysis_call
    ADD COLUMN result JSONB NOT NULL DEFAULT '{}';

ALTER TABLE source_image_analysis_call
    ADD COLUMN result_hash TEXT;

ALTER TABLE source_image_analysis_call
    ADD CONSTRAINT source_image_analysis_call_result_hash_check CHECK (
        result_hash IS NULL OR result_hash ~ '^[0-9a-f]{64}$'
    );

ALTER TABLE source_asset_analysis
    DROP CONSTRAINT source_asset_analysis_purpose_check;

ALTER TABLE source_asset_analysis
    ADD CONSTRAINT source_asset_analysis_purpose_check CHECK (
        purpose IN (
            'article_image_relevance',
            'source_image_analysis',
            'video_teaching_beat',
            'manual_image_description',
            'pdf_page_analysis'
        )
    );
