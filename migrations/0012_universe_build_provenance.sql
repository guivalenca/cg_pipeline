-- A Universe snapshot must be one coherent build, never a mixture of the
-- latest value from unrelated runs.  The build key fingerprints the exact
-- statement/axis/embedding/judge inputs used for a verdict generation.

ALTER TABLE kc_verdict ADD COLUMN build_key TEXT;

-- Historical judge retries with the same inputs receive the same key.  The
-- jsonb text representation is canonical, so field ordering cannot change it.
UPDATE run
SET params = params || jsonb_build_object(
    'build_key', md5(jsonb_build_object(
        'model', model,
        'prompt_ref', prompt_ref,
        'prompt_sha', prompt_sha,
        'params', params
    )::text)
)
WHERE stage = 'kc-judge' AND NOT (params ? 'build_key');

UPDATE kc_verdict v
SET build_key = r.params->>'build_key'
FROM run_item i
JOIN run r ON r.id = i.run_id
WHERE i.id = v.run_item_id;

ALTER TABLE kc_verdict ALTER COLUMN build_key SET NOT NULL;
ALTER TABLE kc_verdict ALTER COLUMN build_key SET DEFAULT 'legacy';

DROP INDEX kc_verdict_pair_idx;
CREATE UNIQUE INDEX kc_verdict_pair_idx
    ON kc_verdict (task_a_id, task_b_id, build_key);

CREATE INDEX kc_verdict_build_idx ON kc_verdict (build_key);

-- Existing grouping snapshots predate explicit provenance.  Pin each one to
-- the newest completed judge build that existed when it was computed.  This
-- preserves the exact historical graph while allowing the UI to stop reading
-- newer labels and verdicts into it.
WITH chosen AS (
    SELECT
        g.id AS grouping_id,
        r.model,
        r.prompt_ref,
        r.prompt_sha,
        r.params
    FROM kc_grouping g
    JOIN LATERAL (
        SELECT r.model, r.prompt_ref, r.prompt_sha, r.params
        FROM run r
        WHERE r.stage = 'kc-judge'
          AND r.status = 'done'
          AND coalesce(r.finished_at, r.started_at) <= g.computed_at
        ORDER BY coalesce(r.finished_at, r.started_at) DESC, r.id DESC
        LIMIT 1
    ) r ON true
)
UPDATE kc_grouping g
SET params = g.params || jsonb_strip_nulls(jsonb_build_object(
    'build_key', c.params->>'build_key',
    'statements_from', c.params->'statements_from',
    'embedding_run', c.params->'embedding_run',
    'modality_runs', c.params->'modality_runs',
    'knowledge_runs', c.params->'knowledge_runs',
    'judge_model', c.model,
    'judge_prompt', c.prompt_ref,
    'judge_prompt_sha', c.prompt_sha
))
FROM chosen c
WHERE g.id = c.grouping_id;
