-- 0019 used a regex escape that is not portable under PostgreSQL's default
-- string rules. Re-run the deliberately narrow legacy classification using a
-- character class for the literal dot. Existing image/analysis facts remain
-- immutable; only the candidate outcome and derived Markdown are superseded.

UPDATE source_image_candidate
SET status = 'filtered',
    filter_reason = 'Strong URL or label evidence identifies website chrome.',
    failure_code = NULL,
    diagnostics = '{"category":"deterministic_web_chrome","reclassified_by":"0021_correct_legacy_image_classification"}'::jsonb,
    analysis_id = NULL,
    claimed_at = NULL,
    lease_expires_at = NULL,
    claim_token = NULL,
    finished_at = COALESCE(finished_at, now()),
    updated_at = now()
WHERE status IN ('queued', 'failed', 'useful', 'not_important')
  AND (
      lower(btrim(alt_text)) = 'add as favorite google source'
      OR lower(split_part(original_url, '?', 1)) ~ '/(close|preloader|loader|loading|spinner)([-_]?(icon|button))?[.](svg|avif|gif|jpe?g|png|webp)$'
      OR lower(split_part(original_url, '?', 1)) ~ '/(facebook|instagram|linkedin|pinterest|twitter|whatsapp|tiktok)([-_]?(logo|icon|share))?[.](svg|avif|gif|jpe?g|png|webp)$'
  );

UPDATE source_image_candidate
SET status = 'queued',
    failure_code = NULL,
    diagnostics = diagnostics || '{"requeued_by":"0021_correct_legacy_image_classification"}'::jsonb,
    analysis_id = NULL,
    available_at = now(),
    claimed_at = NULL,
    lease_expires_at = NULL,
    claim_token = NULL,
    finished_at = NULL,
    updated_at = now()
WHERE status = 'failed'
  AND failure_code = 'image_type_invalid'
  AND lower(split_part(original_url, '?', 1)) ~ '[.](svg|avif)$'
  AND NOT (
      lower(btrim(alt_text)) = 'add as favorite google source'
      OR lower(split_part(original_url, '?', 1)) ~ '/(close|preloader|loader|loading|spinner)([-_]?(icon|button))?[.](svg|avif|gif|jpe?g|png|webp)$'
      OR lower(split_part(original_url, '?', 1)) ~ '/(facebook|instagram|linkedin|pinterest|twitter|whatsapp|tiktok)([-_]?(logo|icon|share))?[.](svg|avif|gif|jpe?g|png|webp)$'
  );
