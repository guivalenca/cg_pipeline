-- Canonical phrasings belong to one composite in one grouping snapshot.
-- The model response stays in run_item; this table supplies the exact
-- snapshot/group identity that run_item's artifact/passage/task columns
-- cannot express.

CREATE TABLE kc_canonicalization (
    run_item_id TEXT PRIMARY KEY REFERENCES run_item (id),
    grouping_id TEXT NOT NULL,
    group_id    TEXT NOT NULL,
    FOREIGN KEY (grouping_id, group_id)
        REFERENCES kc_group (grouping_id, id)
);

CREATE INDEX kc_canonicalization_group_idx
    ON kc_canonicalization (grouping_id, group_id);
