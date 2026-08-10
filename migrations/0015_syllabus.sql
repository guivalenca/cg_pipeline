-- Upgrade the original flat syllabus rows to the explicit lesson/reference
-- model. Existing facts are projected into the new immutable structure before
-- the compatibility view takes the old table name.

ALTER TABLE syllabus_version
    ADD COLUMN input_format TEXT,
    ADD COLUMN file_mime TEXT,
    ADD COLUMN file_body BYTEA;

CREATE INDEX syllabus_version_syllabus_idx
    ON syllabus_version (syllabus_id, seq DESC);

ALTER TABLE syllabus_item RENAME TO syllabus_item_legacy;

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

-- Ordinary rows already are lessons in the former workbook projection.
INSERT INTO syllabus_lesson
    (id, version_id, week, seq, kind, title, description, fields, created_at)
SELECT id, version_id, week, coalesce(seq, 0), kind, title, description,
       fields, created_at
FROM syllabus_item_legacy
WHERE kind <> 'Autoestudo' OR source_id IS NULL;

-- A malformed legacy workbook may reference a missing parent lesson. Preserve
-- that material under an explicit synthetic lesson instead of dropping it.
INSERT INTO syllabus_lesson
    (id, version_id, week, seq, kind, title, description, fields, created_at)
SELECT item.id || ':lesson', item.version_id, item.week, coalesce(item.seq, 0),
       'Encontro', coalesce(nullif(item.parent_title, ''), 'Materiais'), NULL,
       '{}'::jsonb, item.created_at
FROM syllabus_item_legacy item
WHERE item.kind = 'Autoestudo' AND item.source_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM syllabus_lesson lesson
      WHERE lesson.version_id = item.version_id
        AND lesson.title = item.parent_title
        AND lesson.week IS NOT DISTINCT FROM item.week
  );

INSERT INTO syllabus_source_reference
    (id, version_id, lesson_id, seq, title, description, url, media_type,
     source_id, fields, created_at)
SELECT item.id, item.version_id,
       coalesce(parent.id, item.id || ':lesson'),
       coalesce(item.seq, 0), item.title, item.description, item.url,
       source.media_type, item.source_id, item.fields, item.created_at
FROM syllabus_item_legacy item
JOIN source ON source.id = item.source_id
LEFT JOIN LATERAL (
    SELECT lesson.id
    FROM syllabus_lesson lesson
    WHERE lesson.version_id = item.version_id
      AND lesson.title = item.parent_title
      AND lesson.week IS NOT DISTINCT FROM item.week
    ORDER BY lesson.seq, lesson.id
    LIMIT 1
) parent ON true
WHERE item.kind = 'Autoestudo';

-- The old table remains as an insert-compatible bridge for operational code
-- and older fixtures. Rows that were converted above are removed so the
-- projection does not duplicate them; all new authored versions use the
-- explicit tables.
DELETE FROM syllabus_item_legacy;

-- Transitional read-only projection for diagnostics that still consume the
-- original flat shape. New code uses the two explicit tables above.
CREATE VIEW syllabus_item AS
SELECT legacy.id, legacy.version_id, legacy.week, legacy.seq, legacy.kind,
       legacy.title, legacy.description, legacy.parent_title, legacy.url,
       legacy.source_id, legacy.fields, legacy.created_at
FROM syllabus_item_legacy legacy
UNION ALL
SELECT lesson.id, lesson.version_id, lesson.week, lesson.seq, lesson.kind,
       lesson.title, lesson.description, NULL::text AS parent_title,
       NULL::text AS url, NULL::text AS source_id, lesson.fields,
       lesson.created_at
FROM syllabus_lesson lesson
UNION ALL
SELECT reference.id, reference.version_id, lesson.week, reference.seq,
       'Autoestudo'::text, reference.title, reference.description,
       lesson.title, reference.url, reference.source_id, reference.fields,
       reference.created_at
FROM syllabus_source_reference reference
JOIN syllabus_lesson lesson ON lesson.id = reference.lesson_id;

CREATE FUNCTION syllabus_item_compat_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO syllabus_item_legacy
        (id, version_id, week, seq, kind, title, description, parent_title,
         url, source_id, fields, created_at)
    VALUES
        (NEW.id, NEW.version_id, NEW.week, NEW.seq, NEW.kind, NEW.title,
         NEW.description, NEW.parent_title, NEW.url, NEW.source_id,
         coalesce(NEW.fields, '{}'::jsonb), coalesce(NEW.created_at, now()));
    RETURN NEW;
END;
$$;

CREATE TRIGGER syllabus_item_compat_insert_trigger
INSTEAD OF INSERT ON syllabus_item
FOR EACH ROW EXECUTE FUNCTION syllabus_item_compat_insert();
