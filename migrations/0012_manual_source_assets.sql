-- Immutable manual acquisition inputs. A failed Firecrawl/browser acquisition
-- can be followed by a new source-local job whose evidence is one PDF or an
-- explicitly ordered set of raster images. The original Syllabus reference
-- and Source identity remain unchanged.

ALTER TABLE acquisition_job
    ADD CONSTRAINT acquisition_job_id_source_unique UNIQUE (id, source_id);

CREATE TABLE source_asset (
    id                 TEXT PRIMARY KEY,
    acquisition_job_id TEXT NOT NULL,
    source_id          TEXT NOT NULL,
    ordinal            INTEGER NOT NULL CHECK (ordinal BETWEEN 1 AND 50),
    kind               TEXT NOT NULL CHECK (kind IN ('pdf', 'screenshot', 'image')),
    filename           TEXT NOT NULL CHECK (btrim(filename) <> ''),
    mime_type          TEXT NOT NULL CHECK (
        mime_type IN ('application/pdf', 'image/png', 'image/jpeg', 'image/webp')
    ),
    sha256             TEXT NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    byte_size          INTEGER NOT NULL CHECK (byte_size > 0 AND byte_size <= 31457280),
    storage_key        TEXT NOT NULL CHECK (
        storage_key ~ '^sha256/[0-9a-f]{2}/[0-9a-f]{64}$'
    ),
    metadata           JSONB NOT NULL DEFAULT '{}',
    created_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (acquisition_job_id, ordinal),
    FOREIGN KEY (acquisition_job_id, source_id)
        REFERENCES acquisition_job (id, source_id),
    CONSTRAINT source_asset_kind_mime CHECK (
        (kind = 'pdf' AND mime_type = 'application/pdf')
        OR (kind IN ('screenshot', 'image') AND mime_type LIKE 'image/%')
    )
);

CREATE INDEX source_asset_job_idx
    ON source_asset (acquisition_job_id, ordinal);

CREATE INDEX source_asset_source_idx
    ON source_asset (source_id, created_at DESC);

CREATE FUNCTION reject_source_asset_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'source_asset rows are immutable';
END;
$$;

CREATE TRIGGER source_asset_immutable
BEFORE UPDATE OR DELETE ON source_asset
FOR EACH ROW EXECUTE FUNCTION reject_source_asset_mutation();
