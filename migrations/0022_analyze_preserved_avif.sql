-- AVIF originals remain immutable source assets. Pillow now creates a bounded
-- PNG representation for Gemini, so retry only the prior unsupported AVIF
-- outcomes and retain their existing source assets.

UPDATE source_image_candidate c
SET status = 'queued',
    failure_code = NULL,
    diagnostics = diagnostics || '{"requeued_by":"0022_analyze_preserved_avif"}'::jsonb,
    analysis_id = NULL,
    available_at = now(),
    claimed_at = NULL,
    lease_expires_at = NULL,
    claim_token = NULL,
    finished_at = NULL,
    updated_at = now()
FROM source_asset a
WHERE c.asset_id = a.id
  AND c.status = 'failed'
  AND c.failure_code = 'image_analysis_unsupported_type'
  AND a.mime_type = 'image/avif';
