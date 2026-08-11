-- The parsed VTT text is convenient for deterministic cue assembly, while
-- the downloaded bytes are the exact publisher evidence and hash input.
-- Nullable preserves already-recorded 0030 rows; all new Adapter writes
-- materialize this field.

ALTER TABLE video_caption_evidence
    ADD COLUMN vtt_bytes BYTEA;

ALTER TABLE video_caption_evidence
    ADD CONSTRAINT video_caption_evidence_bytes_shape CHECK (
        vtt_bytes IS NULL OR octet_length(vtt_bytes) > 0
    );
