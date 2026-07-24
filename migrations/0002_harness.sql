-- The harness: what happened when a versioned prompt met stored artifacts.
--
-- A run is one prompt version, one model, one set of artifacts. Its rows are
-- facts about an event that already happened: a better prompt is a new run
-- beside the old one, never an edit of it. The only mutation is the run's own
-- status closing from 'running' to its outcome.
--
-- prompt_sha is the hash of the prompt file as it was at run time, so a silent
-- edit without a version bump shows up as two runs claiming the same
-- prompt_ref with different hashes.

CREATE TABLE run (
    id          TEXT PRIMARY KEY,
    stage       TEXT NOT NULL,
    model       TEXT NOT NULL,
    prompt_ref  TEXT NOT NULL,
    prompt_sha  TEXT NOT NULL,
    params      JSONB NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL CHECK (status IN ('running', 'done', 'failed')),
    started_at  timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);

-- One call, one row. A call that failed is still a fact: the error text stands
-- where the response would have been.
CREATE TABLE run_item (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL REFERENCES run (id),
    artifact_id TEXT NOT NULL REFERENCES artifact (id),
    response    TEXT,
    usage       JSONB,
    duration_ms INTEGER,
    error       TEXT,
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT run_item_response_xor_error CHECK ((response IS NULL) <> (error IS NULL))
);

CREATE INDEX run_item_run_idx ON run_item (run_id);
CREATE INDEX run_item_artifact_idx ON run_item (artifact_id);
