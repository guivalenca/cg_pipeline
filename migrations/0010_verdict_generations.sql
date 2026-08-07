-- Judge verdicts are scoped per judge generation (founder decision
-- 2026-08-03, amending ADR 0011's "judged once per pair and never
-- re-asked"): a pair is judged once per (model, prompt version), and an
-- improved judge is a new generation of verdicts recorded beside the old
-- ones, exactly as every other stage versions its runs. The generation is
-- denormalized onto the verdict so the database itself enforces the rule;
-- it must match the judging run's own model and prompt_ref stamps.
--
-- Consumers (grouping, the universe view) read the newest verdict per
-- pair across generations; superseded verdicts remain as permanent
-- history.

ALTER TABLE kc_verdict ADD COLUMN judge_model TEXT NOT NULL;
ALTER TABLE kc_verdict ADD COLUMN judge_prompt TEXT NOT NULL;

DROP INDEX kc_verdict_pair_idx;
CREATE UNIQUE INDEX kc_verdict_pair_idx
    ON kc_verdict (task_a_id, task_b_id, judge_model, judge_prompt);
