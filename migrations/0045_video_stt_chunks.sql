-- Resumable OpenRouter speech-to-text work. Chunk work is keyed independently
-- of an acquisition job so a later source-local retry can reuse paid success.

CREATE TABLE video_stt_chunk (
    id                  TEXT PRIMARY KEY,
    source_id           TEXT NOT NULL REFERENCES source (id),
    audio_sha256        TEXT NOT NULL CHECK (audio_sha256 ~ '^[0-9a-f]{64}$'),
    chunk_sha256        TEXT NOT NULL CHECK (chunk_sha256 ~ '^[0-9a-f]{64}$'),
    window_start_ms     BIGINT NOT NULL CHECK (window_start_ms >= 0),
    window_end_ms       BIGINT NOT NULL CHECK (window_end_ms > window_start_ms),
    requested_model     TEXT NOT NULL,
    fallback_model      TEXT,
    language            TEXT,
    operation_version   TEXT NOT NULL,
    model_route_hash    TEXT NOT NULL CHECK (model_route_hash ~ '^[0-9a-f]{64}$'),
    status              TEXT NOT NULL DEFAULT 'queued'
                        CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    attempt_count       INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at        timestamptz NOT NULL DEFAULT now(),
    claimed_at          timestamptz,
    lease_expires_at    timestamptz,
    claim_token         TEXT,
    text                TEXT,
    segments            JSONB NOT NULL DEFAULT '[]',
    response_language   TEXT,
    response_model      TEXT,
    provider            TEXT,
    usage               JSONB NOT NULL DEFAULT '{}',
    duration_ms         INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    generation_id       TEXT,
    failure_code        TEXT,
    diagnostics         JSONB NOT NULL DEFAULT '{}',
    created_at          timestamptz NOT NULL DEFAULT now(),
    finished_at         timestamptz,
    updated_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (
        source_id, audio_sha256, chunk_sha256, window_start_ms, window_end_ms,
        model_route_hash, operation_version
    ),
    CONSTRAINT video_stt_chunk_state_shape CHECK (
        (status = 'queued' AND claim_token IS NULL AND finished_at IS NULL)
        OR (status = 'running' AND claim_token IS NOT NULL AND finished_at IS NULL)
        OR (status IN ('succeeded', 'failed')
            AND claim_token IS NULL AND finished_at IS NOT NULL)
    ),
    CONSTRAINT video_stt_chunk_result_shape CHECK (
        (status = 'succeeded' AND text IS NOT NULL AND btrim(text) <> ''
            AND failure_code IS NULL)
        OR (status = 'failed' AND text IS NULL AND failure_code IS NOT NULL)
        OR (status IN ('queued', 'running') AND text IS NULL AND failure_code IS NULL)
    )
);

CREATE INDEX video_stt_chunk_claim_idx
    ON video_stt_chunk (available_at, created_at, id)
    WHERE status IN ('queued', 'running', 'failed');

CREATE TABLE video_stt_job_chunk (
    acquisition_job_id TEXT NOT NULL REFERENCES acquisition_job (id),
    chunk_id            TEXT NOT NULL REFERENCES video_stt_chunk (id),
    ordinal             INTEGER NOT NULL CHECK (ordinal > 0),
    created_at          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (acquisition_job_id, ordinal),
    UNIQUE (acquisition_job_id, chunk_id)
);

CREATE TABLE video_stt_attempt (
    id                TEXT PRIMARY KEY,
    chunk_id          TEXT NOT NULL REFERENCES video_stt_chunk (id),
    attempt_no        INTEGER NOT NULL CHECK (attempt_no > 0),
    requested_model   TEXT NOT NULL,
    operation_version TEXT NOT NULL,
    status            TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')),
    response_model    TEXT,
    provider          TEXT,
    generation_id     TEXT,
    language          TEXT,
    usage             JSONB NOT NULL DEFAULT '{}',
    duration_ms       INTEGER NOT NULL CHECK (duration_ms >= 0),
    failure_code      TEXT,
    diagnostics       JSONB NOT NULL DEFAULT '{}',
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (chunk_id, attempt_no),
    CONSTRAINT video_stt_attempt_result_shape CHECK (
        (status = 'succeeded' AND failure_code IS NULL)
        OR (status = 'failed' AND failure_code IS NOT NULL)
    )
);

CREATE TRIGGER video_stt_attempt_immutable
BEFORE UPDATE OR DELETE ON video_stt_attempt
FOR EACH ROW EXECUTE FUNCTION reject_video_transcript_fact_mutation();
