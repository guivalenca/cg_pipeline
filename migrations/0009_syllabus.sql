-- The Syllabus: the teacher's real input, where sources enter the system
-- (ADR 0006). The received workbook is the first version; every fix or
-- re-upload authors the next version beside it. Nothing is overwritten.
--
-- Items carry the full workbook row verbatim in fields; the typed columns
-- are the ones the system navigates by. Row order in the workbook is
-- meaningless; (week, seq) is the teacher's ordering signal.
--
-- Curation events are the permanent record of human actions taken through
-- the dashboard (ADR 0005): who did what, to which records, when.

CREATE TABLE syllabus (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE syllabus_version (
    id          TEXT PRIMARY KEY,
    syllabus_id TEXT NOT NULL REFERENCES syllabus (id),
    seq         INTEGER NOT NULL,
    origin      TEXT NOT NULL CHECK (origin IN ('upload', 'curation')),
    file_name   TEXT,
    file_sha    TEXT,
    note        TEXT,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (syllabus_id, seq)
);

CREATE TABLE syllabus_item (
    id           TEXT PRIMARY KEY,
    version_id   TEXT NOT NULL REFERENCES syllabus_version (id),
    week         INTEGER,
    seq          INTEGER,
    kind         TEXT NOT NULL,
    title        TEXT NOT NULL,
    description  TEXT,
    parent_title TEXT,
    url          TEXT,
    source_id    TEXT REFERENCES source (id),
    fields       JSONB NOT NULL DEFAULT '{}',
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX syllabus_item_version_idx ON syllabus_item (version_id);
CREATE INDEX syllabus_item_source_idx ON syllabus_item (source_id);

CREATE TABLE curation_event (
    id         TEXT PRIMARY KEY,
    actor      TEXT NOT NULL,
    action     TEXT NOT NULL,
    subject    JSONB NOT NULL DEFAULT '{}',
    note       TEXT,
    created_at timestamptz NOT NULL DEFAULT now()
);
