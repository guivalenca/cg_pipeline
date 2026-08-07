-- A grouping snapshot records the exact verdict facts it used.  This matters
-- when a larger build safely reuses still-valid pair judgments from an older
-- run: the snapshot is a manifest, not merely a pointer to one run.

ALTER TABLE kc_verdict ADD COLUMN input_key TEXT;
UPDATE kc_verdict SET input_key = build_key;
ALTER TABLE kc_verdict ALTER COLUMN input_key SET NOT NULL;
ALTER TABLE kc_verdict ALTER COLUMN input_key SET DEFAULT 'legacy';

DROP INDEX kc_verdict_pair_idx;
CREATE UNIQUE INDEX kc_verdict_pair_idx
    ON kc_verdict (task_a_id, task_b_id, input_key);
CREATE INDEX kc_verdict_input_idx ON kc_verdict (input_key);

CREATE TABLE kc_grouping_verdict (
    grouping_id TEXT NOT NULL REFERENCES kc_grouping (id),
    run_item_id TEXT NOT NULL REFERENCES kc_verdict (run_item_id),
    PRIMARY KEY (grouping_id, run_item_id)
);

CREATE INDEX kc_grouping_verdict_item_idx
    ON kc_grouping_verdict (run_item_id);

-- Reconstruct old manifests exactly as the old grouping code read them:
-- newest recorded verdict per pair at the instant of the snapshot.
INSERT INTO kc_grouping_verdict (grouping_id, run_item_id)
SELECT g.id, selected.run_item_id
FROM kc_grouping g
JOIN LATERAL (
    SELECT DISTINCT ON (v.task_a_id, v.task_b_id) v.run_item_id
    FROM kc_verdict v
    WHERE v.created_at <= g.computed_at
    ORDER BY v.task_a_id, v.task_b_id, v.created_at DESC, v.run_item_id DESC
) selected ON true;
