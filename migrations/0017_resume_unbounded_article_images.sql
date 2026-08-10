-- Visual relevance is never inferred from candidate volume. Resume candidates
-- previously stopped by the obsolete per-article cap, and retry the image-only
-- model work that failed while the OpenRouter key had no available budget.
-- Existing downloaded assets and failed analysis rows remain immutable facts.

UPDATE source_image_candidate
SET status = 'queued',
    failure_code = NULL,
    diagnostics = diagnostics || jsonb_build_object(
        'requeued_by', '0017_resume_unbounded_article_images'
    ),
    analysis_id = NULL,
    available_at = now(),
    claimed_at = NULL,
    lease_expires_at = NULL,
    claim_token = NULL,
    finished_at = NULL,
    updated_at = now()
WHERE status = 'failed'
  AND (
      failure_code = 'article_image_limit_exceeded'
      OR diagnostics->>'category' IN ('model_credits', 'model_authentication')
  );
