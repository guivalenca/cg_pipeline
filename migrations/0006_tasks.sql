-- Tasks: materialized interpretation, like passages. A task is one entry a
-- generation run reported for a passage, promoted to a row so later stages
-- can judge it, group it, and cite it one at a time.
--
-- Identity is positional: the run item that reported the task, plus its
-- position in that report. Unlike passage ranges, task texts almost never
-- collide across runs, so there is nothing to deduplicate by content; each
-- generation run's tasks stand as their own rows, and the run item already
-- says which run, model, and prompt produced them.
--
-- Rows are insert-only. A better generation is a new run whose tasks land
-- beside the old ones.

CREATE TABLE task (
    id          TEXT PRIMARY KEY,
    run_item_id TEXT NOT NULL REFERENCES run_item (id),
    passage_id  TEXT NOT NULL REFERENCES passage (id),
    seq         INTEGER NOT NULL,
    body        TEXT NOT NULL,
    answer      TEXT NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_item_id, seq)
);

CREATE INDEX task_passage_idx ON task (passage_id);

-- A run item may now be about one task, as the per-task stages are.
ALTER TABLE run_item ADD COLUMN task_id TEXT REFERENCES task (id);

CREATE INDEX run_item_task_idx ON run_item (task_id);
