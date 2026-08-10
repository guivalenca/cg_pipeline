-- One explicit acquisition request is one durable, source-local job.
--
-- The queue is operational state, unlike source_snapshot and artifact, which
-- are permanent facts.  A job is committed before a provider is contacted so
-- a web request can return immediately and another process can safely claim
-- the work.  Only one queued/running job may exist for a source: a double
-- click returns the existing job rather than paying for the same fetch twice.

CREATE TABLE acquisition_job (
    id               TEXT PRIMARY KEY,
    source_id        TEXT NOT NULL REFERENCES source (id),
    status           TEXT NOT NULL DEFAULT 'queued'
                     CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    provider         TEXT NOT NULL,
    attempt_count    INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at     timestamptz NOT NULL DEFAULT now(),
    claimed_at       timestamptz,
    lease_expires_at timestamptz,
    finished_at      timestamptz,
    artifact_id      TEXT REFERENCES artifact (id),
    failure_code     TEXT,
    diagnostics      JSONB NOT NULL DEFAULT '{}',
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT acquisition_job_terminal_shape CHECK (
        (status = 'succeeded' AND artifact_id IS NOT NULL AND failure_code IS NULL)
        OR (status = 'failed' AND artifact_id IS NULL AND failure_code IS NOT NULL)
        OR (status IN ('queued', 'running') AND artifact_id IS NULL AND failure_code IS NULL)
    )
);

CREATE UNIQUE INDEX acquisition_job_one_active_source_idx
    ON acquisition_job (source_id)
    WHERE status IN ('queued', 'running');

CREATE INDEX acquisition_job_claim_idx
    ON acquisition_job (available_at, created_at)
    WHERE status IN ('queued', 'running');

CREATE INDEX acquisition_job_source_idx
    ON acquisition_job (source_id, created_at DESC);
