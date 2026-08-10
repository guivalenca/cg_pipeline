-- Image analysis may use an inline data URL as request transport, but the
-- durable ledger must never duplicate those bytes in PostgreSQL telemetry.

UPDATE source_asset_analysis
SET diagnostics = (diagnostics - 'model_image_url') || jsonb_build_object(
    'model_image_transport',
    CASE
        WHEN lower(diagnostics->>'model_image_url') LIKE 'data:%' THEN 'data_url'
        WHEN lower(diagnostics->>'model_image_url') LIKE 'http://%'
          OR lower(diagnostics->>'model_image_url') LIKE 'https://%' THEN 'remote_url'
        ELSE 'other'
    END
)
WHERE diagnostics ? 'model_image_url';

ALTER TABLE source_asset_analysis
    ADD CONSTRAINT source_asset_analysis_no_inline_image_payload
    CHECK (position('data:image' IN lower(diagnostics::text)) = 0);
