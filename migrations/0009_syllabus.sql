-- The syllabus is the institution's versioned statement of what belongs in a
-- course.  Workbook files are evidence used to author versions; they are not
-- the identity of the syllabus itself.  A founder supplies that identity and
-- display name explicitly.
--
-- Every version is a complete, immutable projection.  Removing a lesson or a
-- source reference means omitting it from the next version.  It never deletes
-- the older version, the logical source, its snapshots, or its artifacts
-- (ADRs 0001 and 0006).

CREATE TABLE syllabus (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL CHECK (btrim(title) <> ''),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE syllabus_version (
    id           TEXT PRIMARY KEY,
    syllabus_id  TEXT NOT NULL REFERENCES syllabus (id),
    seq          INTEGER NOT NULL CHECK (seq > 0),
    origin       TEXT NOT NULL CHECK (origin IN ('upload', 'curation')),
    input_format TEXT,
    file_name    TEXT,
    file_mime    TEXT,
    file_sha     TEXT,
    file_body    BYTEA,
    note         TEXT,
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (syllabus_id, seq),
    CONSTRAINT syllabus_version_upload_file CHECK (
        origin = 'curation'
        OR (
            file_name IS NOT NULL
            AND file_mime IS NOT NULL
            AND file_sha IS NOT NULL
            AND file_body IS NOT NULL
        )
    )
);

CREATE INDEX syllabus_version_syllabus_idx
    ON syllabus_version (syllabus_id, seq DESC);

-- A lesson is the navigational parent of assigned source references.  All
-- workbook cells remain in fields so the typed columns can evolve without
-- losing facts received from the institution.
CREATE TABLE syllabus_lesson (
    id          TEXT PRIMARY KEY,
    version_id  TEXT NOT NULL REFERENCES syllabus_version (id),
    week        INTEGER,
    seq         INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    title       TEXT NOT NULL,
    subject     TEXT,
    lesson_date DATE,
    description TEXT,
    fields      JSONB NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (version_id, id)
);

CREATE INDEX syllabus_lesson_version_idx
    ON syllabus_lesson (version_id, week, seq, id);

-- A reference is the teacher's placement of one material in one lesson.  Its
-- URL, description and book scope remain facts of that syllabus version even
-- when they resolve to an already-known logical source.
CREATE TABLE syllabus_source_reference (
    id            TEXT PRIMARY KEY,
    version_id    TEXT NOT NULL REFERENCES syllabus_version (id),
    lesson_id     TEXT NOT NULL,
    seq           INTEGER NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    url           TEXT,
    media_type    TEXT NOT NULL CHECK (media_type IN ('article', 'video', 'book')),
    resource_code TEXT,
    scope_kind    TEXT,
    scope_value   TEXT,
    source_id     TEXT REFERENCES source (id),
    fields        JSONB NOT NULL DEFAULT '{}',
    created_at    timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (version_id, lesson_id)
        REFERENCES syllabus_lesson (version_id, id),
    CONSTRAINT syllabus_source_reference_scope_shape CHECK (
        (scope_kind IS NULL AND scope_value IS NULL)
        OR (scope_kind IS NOT NULL AND scope_value IS NOT NULL)
    )
);

CREATE INDEX syllabus_source_reference_version_idx
    ON syllabus_source_reference (version_id, lesson_id, seq, id);
CREATE INDEX syllabus_source_reference_source_idx
    ON syllabus_source_reference (source_id);

-- Founder actions are facts too.  A future HTML edit saves a complete new
-- syllabus_version and records the action here; it does not mutate a prior
-- version.
CREATE TABLE curation_event (
    id         TEXT PRIMARY KEY,
    actor      TEXT NOT NULL,
    action     TEXT NOT NULL,
    subject    JSONB NOT NULL DEFAULT '{}',
    note       TEXT,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Transitional read-only projection for older diagnostic code.  New code
-- should use the explicit lesson/reference tables above.
CREATE VIEW syllabus_item AS
SELECT
    lesson.id,
    lesson.version_id,
    lesson.week,
    lesson.seq,
    lesson.kind,
    lesson.title,
    lesson.description,
    NULL::text AS parent_title,
    NULL::text AS url,
    NULL::text AS source_id,
    lesson.fields,
    lesson.created_at
FROM syllabus_lesson AS lesson
UNION ALL
SELECT
    reference.id,
    reference.version_id,
    lesson.week,
    reference.seq,
    'Autoestudo'::text AS kind,
    reference.title,
    reference.description,
    lesson.title AS parent_title,
    reference.url,
    reference.source_id,
    reference.fields,
    reference.created_at
FROM syllabus_source_reference AS reference
JOIN syllabus_lesson AS lesson ON lesson.id = reference.lesson_id;
