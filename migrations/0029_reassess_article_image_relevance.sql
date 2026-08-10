-- v2 distinguishes evidence in the primary article from ads, calls to action
-- and recommended-content cards. Reassess only prior model decisions; exact
-- deterministic chrome remains filtered and download failures remain intact.

UPDATE source_image_candidate c
SET status = 'queued',
    failure_code = NULL,
    diagnostics = c.diagnostics || '{"requeued_by":"0023_reassess_article_image_relevance"}'::jsonb,
    analysis_id = NULL,
    available_at = now(),
    claimed_at = NULL,
    lease_expires_at = NULL,
    claim_token = NULL,
    finished_at = NULL,
    updated_at = now()
FROM source_asset_analysis a
WHERE c.analysis_id = a.id
  AND c.status IN ('useful', 'not_important')
  AND a.purpose = 'article_image_relevance'
  AND a.prompt_version = 'article-image-analysis.v1';
