-- Block version 3 makes enriched or unresolved images first-class atomic
-- elements.  Earlier block ledgers remain valid and keep a NULL image_state.
ALTER TABLE block ADD COLUMN image_state TEXT;

ALTER TABLE block ADD CONSTRAINT block_image_state_check CHECK (
    (image_state IS NULL
        OR (kind = 'image' AND image_state IN ('enriched', 'unresolved')))
    AND (blocker_version <> '3' OR kind <> 'image' OR image_state IS NOT NULL)
);

-- A revision is an immutable projection of one passage after a model reported
-- element numbers to remove.  The original passage and its blocks never move.
CREATE TABLE passage_revision (
    id                  TEXT PRIMARY KEY,
    passage_id          TEXT NOT NULL REFERENCES passage (id),
    parent_revision_id  TEXT,
    refine_run_item_id  TEXT NOT NULL UNIQUE REFERENCES run_item (id),
    iteration           INTEGER NOT NULL CHECK (iteration >= 1),
    body                TEXT NOT NULL,
    content_hash        TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    created_at          timestamptz NOT NULL DEFAULT now(),
    CHECK (parent_revision_id IS NULL OR parent_revision_id <> id),
    UNIQUE (id, passage_id),
    FOREIGN KEY (parent_revision_id, passage_id)
        REFERENCES passage_revision (id, passage_id)
);

CREATE INDEX passage_revision_passage_idx ON passage_revision (passage_id);
CREATE INDEX passage_revision_parent_idx ON passage_revision (parent_revision_id);

CREATE TABLE passage_revision_drop (
    revision_id TEXT NOT NULL REFERENCES passage_revision (id),
    block_id    TEXT NOT NULL REFERENCES block (id),
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (revision_id, block_id)
);

-- The revision on a run item is the exact input state seen by that call. NULL
-- means the raw passage. A refine item therefore points to its parent, while
-- the child revision points back to that refine item as its origin.
ALTER TABLE run_item ADD COLUMN passage_revision_id TEXT;

ALTER TABLE run_item ADD CONSTRAINT run_item_passage_revision_requires_passage
    CHECK (passage_revision_id IS NULL OR passage_id IS NOT NULL);

ALTER TABLE run_item ADD CONSTRAINT run_item_passage_revision_fk
    FOREIGN KEY (passage_revision_id, passage_id)
    REFERENCES passage_revision (id, passage_id);

CREATE INDEX run_item_passage_revision_idx ON run_item (passage_revision_id);

-- One cleanup session groups the several prompt runs needed by the loop. Its
-- terminal rows are the explicit gate consumed by canonical Markdown and task
-- generation; experiments from other sessions can never become "latest" by
-- accident.
CREATE TABLE passage_cleanup (
    id                    TEXT PRIMARY KEY,
    cuts_run_id           TEXT NOT NULL REFERENCES run (id),
    model                 TEXT NOT NULL,
    triage_prompt_ref     TEXT NOT NULL,
    refine_prompt_ref     TEXT NOT NULL,
    status                TEXT NOT NULL CHECK (status IN ('running', 'done', 'failed')),
    run_ids               JSONB NOT NULL DEFAULT '[]'
                          CHECK (jsonb_typeof(run_ids) = 'array'),
    created_at            timestamptz NOT NULL DEFAULT now(),
    finished_at           timestamptz,
    CONSTRAINT passage_cleanup_status_shape CHECK (
        (status = 'running' AND finished_at IS NULL)
        OR (status IN ('done', 'failed') AND finished_at IS NOT NULL)
    )
);

CREATE TABLE passage_cleanup_result (
    cleanup_id          TEXT NOT NULL REFERENCES passage_cleanup (id),
    passage_id          TEXT NOT NULL REFERENCES passage (id),
    passage_revision_id TEXT,
    decision_run_item_id TEXT UNIQUE REFERENCES run_item (id),
    verdict             TEXT NOT NULL CHECK (verdict IN ('keep', 'drop', 'unknown')),
    created_at          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (cleanup_id, passage_id),
    CHECK (decision_run_item_id IS NOT NULL OR verdict = 'unknown'),
    FOREIGN KEY (passage_revision_id, passage_id)
        REFERENCES passage_revision (id, passage_id)
);

CREATE INDEX passage_cleanup_result_revision_idx
    ON passage_cleanup_result (passage_revision_id);

CREATE TABLE passage_cleanup_artifact (
    cleanup_id           TEXT NOT NULL REFERENCES passage_cleanup (id),
    source_artifact_id   TEXT NOT NULL REFERENCES artifact (id),
    canonical_artifact_id TEXT NOT NULL UNIQUE REFERENCES artifact (id),
    created_at           timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (cleanup_id, source_artifact_id),
    CHECK (source_artifact_id <> canonical_artifact_id)
);
