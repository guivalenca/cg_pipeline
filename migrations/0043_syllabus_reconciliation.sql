-- An uploaded workbook is reviewed before it becomes a SyllabusVersion.
-- The durable reconciliation keeps the institution's evidence, the computed
-- three-way plan and the founder's final decisions without exposing an
-- unapproved workbook as the current syllabus.

CREATE TABLE syllabus_reconciliation (
    id                 TEXT PRIMARY KEY,
    syllabus_id        TEXT NOT NULL REFERENCES syllabus(id),
    base_version_id    TEXT NOT NULL REFERENCES syllabus_version(id),
    status             TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'applied')),
    input_format       TEXT NOT NULL,
    file_name          TEXT NOT NULL,
    file_mime          TEXT NOT NULL,
    file_sha           TEXT NOT NULL,
    file_body          BYTEA NOT NULL,
    incoming           JSONB NOT NULL,
    plan               JSONB NOT NULL,
    decisions          JSONB,
    created_version_id TEXT REFERENCES syllabus_version(id),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    applied_at         TIMESTAMPTZ,
    UNIQUE (syllabus_id, base_version_id, file_sha),
    CONSTRAINT syllabus_reconciliation_applied_shape CHECK (
        (status = 'pending' AND created_version_id IS NULL AND applied_at IS NULL)
        OR
        (status = 'applied' AND created_version_id IS NOT NULL AND applied_at IS NOT NULL)
    )
);

CREATE INDEX syllabus_reconciliation_syllabus_idx
    ON syllabus_reconciliation (syllabus_id, created_at DESC, id);

CREATE INDEX syllabus_reconciliation_applied_idx
    ON syllabus_reconciliation (syllabus_id, applied_at DESC, id)
    WHERE status = 'applied';
