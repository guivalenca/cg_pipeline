-- Provider-free YouTube readiness and immutable uploaded-caption transcript facts.
-- Paid STT work units are added separately when that vertical slice lands.

CREATE TABLE video_preflight (
    id                         TEXT PRIMARY KEY,
    source_id                  TEXT NOT NULL REFERENCES source (id),
    probe_version              TEXT NOT NULL,
    input_fingerprint          TEXT NOT NULL CHECK (input_fingerprint ~ '^[0-9a-f]{64}$'),
    status                     TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')),
    title                      TEXT,
    channel                    TEXT,
    duration_seconds           DOUBLE PRECISION CHECK (
        duration_seconds IS NULL OR duration_seconds >= 0
    ),
    uploaded_caption_languages JSONB NOT NULL DEFAULT '[]',
    selected_caption_language  TEXT,
    route                      TEXT CHECK (
        route IN ('uploaded_caption', 'automatic_stt', 'approval_required')
    ),
    failure_code               TEXT,
    diagnostics                JSONB NOT NULL DEFAULT '{}',
    created_at                 timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT video_preflight_terminal_shape CHECK (
        (status = 'succeeded' AND route IS NOT NULL AND failure_code IS NULL)
        OR (status = 'failed' AND route IS NULL AND failure_code IS NOT NULL)
    ),
    CONSTRAINT video_preflight_caption_shape CHECK (
        (route = 'uploaded_caption' AND selected_caption_language IS NOT NULL)
        OR (route IS DISTINCT FROM 'uploaded_caption'
            AND selected_caption_language IS NULL)
    )
);

CREATE INDEX video_preflight_source_idx
    ON video_preflight (source_id, created_at DESC, id DESC);

ALTER TABLE acquisition_job
    ADD COLUMN video_preflight_id TEXT REFERENCES video_preflight (id),
    ADD COLUMN request_input JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN input_fingerprint TEXT;

CREATE TABLE video_caption_evidence (
    id                 TEXT PRIMARY KEY,
    acquisition_job_id TEXT NOT NULL UNIQUE REFERENCES acquisition_job (id),
    source_id          TEXT NOT NULL REFERENCES source (id),
    snapshot_id        TEXT NOT NULL UNIQUE REFERENCES source_snapshot (id),
    preflight_id       TEXT NOT NULL REFERENCES video_preflight (id),
    language           TEXT NOT NULL CHECK (btrim(language) <> ''),
    origin             TEXT NOT NULL DEFAULT 'publisher_uploaded'
                       CHECK (origin = 'publisher_uploaded'),
    source_url         TEXT NOT NULL CHECK (source_url ~ '^https://www\.youtube\.com/watch\?v='),
    vtt_sha256         TEXT NOT NULL CHECK (vtt_sha256 ~ '^[0-9a-f]{64}$'),
    vtt_body           TEXT NOT NULL CHECK (btrim(vtt_body) <> ''),
    created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE video_transcript (
    id                   TEXT PRIMARY KEY,
    acquisition_job_id   TEXT NOT NULL UNIQUE REFERENCES acquisition_job (id),
    source_id            TEXT NOT NULL REFERENCES source (id),
    snapshot_id          TEXT NOT NULL UNIQUE REFERENCES source_snapshot (id),
    route                TEXT NOT NULL CHECK (route IN ('uploaded_caption', 'openrouter_stt')),
    language             TEXT,
    grouping_version     TEXT NOT NULL,
    segment_count        INTEGER NOT NULL CHECK (segment_count > 0),
    content_hash         TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    markdown_artifact_id TEXT NOT NULL UNIQUE REFERENCES artifact (id),
    visual_analysis      TEXT NOT NULL DEFAULT 'deferred' CHECK (visual_analysis = 'deferred'),
    metadata             JSONB NOT NULL DEFAULT '{}',
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE video_transcript_segment (
    transcript_id TEXT NOT NULL REFERENCES video_transcript (id),
    seq           INTEGER NOT NULL CHECK (seq > 0),
    start_ms      BIGINT NOT NULL CHECK (start_ms >= 0),
    end_ms        BIGINT NOT NULL CHECK (end_ms >= start_ms),
    text          TEXT NOT NULL CHECK (btrim(text) <> ''),
    source_kind   TEXT NOT NULL CHECK (source_kind IN ('caption_cue', 'stt_segment', 'stt_chunk')),
    source_ref    TEXT NOT NULL CHECK (btrim(source_ref) <> ''),
    created_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (transcript_id, seq)
);

CREATE FUNCTION reject_video_transcript_fact_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'video transcript fact rows are immutable';
END;
$$;

CREATE TRIGGER video_preflight_immutable
BEFORE UPDATE OR DELETE ON video_preflight
FOR EACH ROW EXECUTE FUNCTION reject_video_transcript_fact_mutation();

CREATE TRIGGER video_caption_evidence_immutable
BEFORE UPDATE OR DELETE ON video_caption_evidence
FOR EACH ROW EXECUTE FUNCTION reject_video_transcript_fact_mutation();

CREATE TRIGGER video_transcript_immutable
BEFORE UPDATE OR DELETE ON video_transcript
FOR EACH ROW EXECUTE FUNCTION reject_video_transcript_fact_mutation();

CREATE TRIGGER video_transcript_segment_immutable
BEFORE UPDATE OR DELETE ON video_transcript_segment
FOR EACH ROW EXECUTE FUNCTION reject_video_transcript_fact_mutation();
