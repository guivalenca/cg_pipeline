-- Passages: materialized interpretation, not fact. A passage is a stretch of
-- adjacent blocks a model chose to take in as one unit. It is derived from a
-- stamped cuts run, it could always have been drawn differently, and it cannot
-- be factually wrong: only better or worse. So it sits outside the ingestion
-- ledger, even though it addresses content the same way ingestion does.
--
-- Identity is the range itself: artifact, blocker version, first and last
-- block. Two runs that happen to draw the same boundary therefore write the
-- same id, and agreement between runs deduplicates on insert instead of
-- paying for the same passage twice in every stage downstream. Which runs drew
-- a range is a separate fact, in passage_origin, and several origins per
-- passage are the expected case, not an anomaly.
--
-- Rows are insert-only. A better segmentation is a new run whose ranges land
-- beside the old ones, so a passage id cited yesterday still resolves to the
-- same blocks.

CREATE TABLE passage (
    id              TEXT PRIMARY KEY,
    artifact_id     TEXT NOT NULL REFERENCES artifact (id),
    blocker_version TEXT NOT NULL,
    first_seq       INTEGER NOT NULL,
    last_seq        INTEGER NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (artifact_id, blocker_version, first_seq, last_seq),
    CONSTRAINT passage_range_ordered CHECK (first_seq <= last_seq)
);

CREATE INDEX passage_artifact_idx ON passage (artifact_id);

-- The cuts run a passage came out of. The same passage reached from four runs
-- is four rows here and one row above.
CREATE TABLE passage_origin (
    passage_id TEXT NOT NULL REFERENCES passage (id),
    run_id     TEXT NOT NULL REFERENCES run (id),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (passage_id, run_id)
);

CREATE INDEX passage_origin_run_idx ON passage_origin (run_id);

-- A run item is about a whole artifact (NULL, as every run so far) or about
-- one passage of it, as the per-passage stages are.
ALTER TABLE run_item ADD COLUMN passage_id TEXT REFERENCES passage (id);

CREATE INDEX run_item_passage_idx ON run_item (passage_id);
