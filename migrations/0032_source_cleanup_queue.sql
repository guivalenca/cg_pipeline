-- One source-local cleanup follows a successful article acquisition through
-- blocks, passage cuts and the terminal triage/refine loop.  It is separate
-- operational state from the immutable acquisition and interpretation facts.
CREATE TABLE source_cleanup_job (
    id                    TEXT PRIMARY KEY,
    acquisition_job_id    TEXT NOT NULL UNIQUE REFERENCES acquisition_job (id),
    source_id             TEXT NOT NULL REFERENCES source (id),
    source_artifact_id    TEXT NOT NULL UNIQUE REFERENCES artifact (id),
    status                TEXT NOT NULL DEFAULT 'queued'
                          CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    attempt_count         INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at          timestamptz NOT NULL DEFAULT now(),
    claimed_at            timestamptz,
    lease_expires_at      timestamptz,
    claim_token           TEXT,
    cuts_run_id           TEXT REFERENCES run (id),
    cleanup_id            TEXT REFERENCES passage_cleanup (id),
    canonical_artifact_id TEXT UNIQUE REFERENCES artifact (id),
    failure_code          TEXT,
    diagnostics           JSONB NOT NULL DEFAULT '{}',
    created_at            timestamptz NOT NULL DEFAULT now(),
    finished_at           timestamptz,
    updated_at            timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_cleanup_job_state_shape CHECK (
        (status = 'queued' AND claim_token IS NULL AND finished_at IS NULL)
        OR (status = 'running' AND claim_token IS NOT NULL AND finished_at IS NULL)
        OR (status IN ('succeeded', 'failed')
            AND claim_token IS NULL AND finished_at IS NOT NULL)
    ),
    CONSTRAINT source_cleanup_job_terminal_shape CHECK (
        (status = 'succeeded' AND cleanup_id IS NOT NULL
            AND canonical_artifact_id IS NOT NULL AND failure_code IS NULL)
        OR (status = 'failed' AND canonical_artifact_id IS NULL
            AND failure_code IS NOT NULL)
        OR (status IN ('queued', 'running')
            AND canonical_artifact_id IS NULL AND failure_code IS NULL)
    )
);

CREATE UNIQUE INDEX source_cleanup_job_one_active_source_idx
    ON source_cleanup_job (source_id)
    WHERE status IN ('queued', 'running');

CREATE INDEX source_cleanup_job_claim_idx
    ON source_cleanup_job (available_at, created_at, id)
    WHERE status IN ('queued', 'running');

CREATE INDEX source_cleanup_job_source_idx
    ON source_cleanup_job (source_id, created_at DESC);
