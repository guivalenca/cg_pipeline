-- A completed judge run certifies the exact verdict facts selected for the
-- grouped stage. Verdicts may be reused from an older build, so this cannot be
-- reconstructed from run_item.run_id or kc_verdict.build_key.

CREATE TABLE kc_judge_manifest (
    judge_run_id TEXT NOT NULL REFERENCES run (id),
    seq          INTEGER NOT NULL CHECK (seq >= 1),
    run_item_id  TEXT NOT NULL REFERENCES kc_verdict (run_item_id),
    PRIMARY KEY (judge_run_id, seq),
    UNIQUE (judge_run_id, run_item_id)
);

CREATE INDEX kc_judge_manifest_item_idx
    ON kc_judge_manifest (run_item_id);
