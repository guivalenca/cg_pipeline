-- The visual model can contradict its own relevance label by returning
-- meaningful description/OCR together with `not_important`.  The parser now
-- resolves that contradiction by preserving the image. Retry only these
-- model-level failures; downloaded assets and earlier analysis facts remain.

UPDATE source_image_candidate
SET status = 'queued',
    failure_code = NULL,
    diagnostics = diagnostics || jsonb_build_object(
        'requeued_by', '0018_retry_fail_open_image_analysis'
    ),
    analysis_id = NULL,
    available_at = now(),
    claimed_at = NULL,
    lease_expires_at = NULL,
    claim_token = NULL,
    finished_at = NULL,
    updated_at = now()
WHERE status = 'failed'
  AND failure_code = 'image_analysis_failed'
  AND diagnostics->>'exception' = 'ModelError'
  AND asset_id IS NOT NULL;
