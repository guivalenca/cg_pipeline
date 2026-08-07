-- The kc-judge verdict ledger and composite KC snapshots (ADR 0011).
--
-- A verdict is a permanent fact: one model call judged one pair of unitary
-- KCs (tasks) in both directions on the 4-level surmise scale. A pair is
-- judged once and never re-asked; the unique index enforces it. The pair is
-- normalized task_a < task_b so the same two tasks cannot appear twice in
-- either order.
--
-- Judge run items are not about one artifact, so artifact_id loosens to
-- nullable; every existing stage keeps writing it.

ALTER TABLE run_item ALTER COLUMN artifact_id DROP NOT NULL;

CREATE TABLE kc_verdict (
    run_item_id TEXT PRIMARY KEY REFERENCES run_item (id),
    task_a_id   TEXT NOT NULL REFERENCES task (id),
    task_b_id   TEXT NOT NULL REFERENCES task (id),
    a_implies_b TEXT NOT NULL CHECK (a_implies_b IN ('clear_yes', 'likely', 'unlikely', 'clear_no')),
    b_implies_a TEXT NOT NULL CHECK (b_implies_a IN ('clear_yes', 'likely', 'unlikely', 'clear_no')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kc_verdict_pair_order CHECK (task_a_id < task_b_id)
);

CREATE UNIQUE INDEX kc_verdict_pair_idx ON kc_verdict (task_a_id, task_b_id);
CREATE INDEX kc_verdict_task_b_idx ON kc_verdict (task_b_id);

-- Composite KC snapshots: derived, re-mintable interpretations over the
-- verdict ledger (perfect cliques of mutual clear_yes). A grouping is one
-- computation event; its groups carry ids derived from their sorted member
-- sets, so an unchanged clique keeps its id across recomputations.
-- Singleton KCs are not materialized: a task in no group is its own KC.

CREATE TABLE kc_grouping (
    id          TEXT PRIMARY KEY,
    params      JSONB NOT NULL DEFAULT '{}',
    computed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE kc_group (
    grouping_id TEXT NOT NULL REFERENCES kc_grouping (id),
    id          TEXT NOT NULL,
    PRIMARY KEY (grouping_id, id)
);

CREATE TABLE kc_group_member (
    grouping_id TEXT NOT NULL,
    group_id    TEXT NOT NULL,
    task_id     TEXT NOT NULL REFERENCES task (id),
    PRIMARY KEY (grouping_id, group_id, task_id),
    FOREIGN KEY (grouping_id, group_id) REFERENCES kc_group (grouping_id, id)
);

CREATE INDEX kc_group_member_task_idx ON kc_group_member (task_id);
