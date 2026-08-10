-- Reclassify only exact legacy interface assets as deterministic chrome.
-- Ambiguous SVG/AVIF candidates are retried so their original bytes can be
-- preserved locally even when the visual model cannot analyze that format.

UPDATE source_image_candidate
SET status = 'filtered',
    filter_reason = 'Strong URL or label evidence identifies website chrome.',
    failure_code = NULL,
    diagnostics = '{"category":"deterministic_web_chrome","reclassified_by":"0019_preserve_legacy_modern_images"}'::jsonb,
    analysis_id = NULL,
    claimed_at = NULL,
    lease_expires_at = NULL,
    claim_token = NULL,
    finished_at = COALESCE(finished_at, now()),
    updated_at = now()
WHERE status IN ('queued', 'failed')
  AND (
      lower(btrim(alt_text)) = 'add as favorite google source'
      OR lower(split_part(original_url, '?', 1)) ~ '/(close|preloader|loader|loading|spinner)([-_]?(icon|button))?\\.(svg|avif|gif|jpe?g|png|webp)$'
      OR lower(split_part(original_url, '?', 1)) ~ '/(facebook|instagram|linkedin|pinterest|twitter|whatsapp|tiktok)([-_]?(logo|icon|share))?\\.(svg|avif|gif|jpe?g|png|webp)$'
  );

UPDATE source_image_candidate
SET status = 'queued',
    failure_code = NULL,
    diagnostics = diagnostics || '{"requeued_by":"0019_preserve_legacy_modern_images"}'::jsonb,
    analysis_id = NULL,
    available_at = now(),
    claimed_at = NULL,
    lease_expires_at = NULL,
    claim_token = NULL,
    finished_at = NULL,
    updated_at = now()
WHERE status = 'failed'
  AND failure_code = 'image_type_invalid'
  AND lower(split_part(original_url, '?', 1)) ~ '\\.(svg|avif)$';
