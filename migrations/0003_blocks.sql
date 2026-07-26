-- Blocks: the deterministic split of an artifact into the units markdown
-- already delimits. No model is involved, so the segmentation is a fact and
-- the last link of the ingestion chain; everything downstream (passages,
-- tasks, grains) addresses content by block id.
--
-- body is always exactly artifact.body[start_char:end_char] with Python slice
-- semantics: start_char inclusive, end_char exclusive, offsets in characters
-- of the decoded text. The blocker asserts that round-trip before it writes.
--
-- Rows are facts: inserted, never updated or deleted. A better blocker is a
-- new blocker_version whose whole set of rows is inserted beside the old one,
-- so an id that was cited yesterday still resolves to the same characters.

CREATE TABLE block (
    id              TEXT PRIMARY KEY,
    artifact_id     TEXT NOT NULL REFERENCES artifact (id),
    blocker_version TEXT NOT NULL,
    seq             INTEGER NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('paragraph','heading','code_block','list_item','image','table','blockquote')),
    start_char      INTEGER NOT NULL,
    end_char        INTEGER NOT NULL,
    body            TEXT NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (artifact_id, blocker_version, seq)
);

CREATE INDEX block_artifact_idx ON block (artifact_id);
