-- Replace the temporary graph metadata stored on a Syllabus with the durable
-- Institution and Lesson Subject model approved for the KC-native path.
--
-- The former graph fields are retained in an audit table. They are not copied
-- into the new model because graph display_name meant one subject, while the
-- Syllabus display_name now means the Institution's current curricular unit.

CREATE TABLE syllabus_legacy_graph_metadata (
    syllabus_id      TEXT PRIMARY KEY REFERENCES syllabus (id),
    graph_id         TEXT,
    display_name     TEXT,
    institution_slug TEXT,
    archived_at      timestamptz NOT NULL DEFAULT now()
);

INSERT INTO syllabus_legacy_graph_metadata
    (syllabus_id, graph_id, display_name, institution_slug)
SELECT id, graph_id, display_name, institution_slug
FROM syllabus
WHERE graph_id IS NOT NULL
   OR display_name IS NOT NULL
   OR institution_slug IS NOT NULL;

ALTER TABLE syllabus
    ADD COLUMN institution_id TEXT REFERENCES institution (id);

-- A group already records an Institution. Use it only when the old typed slug
-- agrees or is absent. Conflicts remain unresolved in the durable model and
-- stay visible in the archive for an operator to repair deliberately.
UPDATE syllabus AS selected
SET institution_id = grouped.institution_id
FROM study_group AS grouped
WHERE grouped.id = selected.group_id
  AND (
      selected.institution_slug IS NULL
      OR selected.institution_slug = grouped.institution_id
  );

-- An ungrouped Syllabus can reuse an old slug only when it already names a
-- real Institution record. The migration never invents an Institution.
UPDATE syllabus AS selected
SET institution_id = existing.id
FROM institution AS existing
WHERE selected.institution_id IS NULL
  AND selected.group_id IS NULL
  AND existing.id = selected.institution_slug;

ALTER TABLE syllabus
    DROP CONSTRAINT syllabus_graph_metadata_shape,
    DROP COLUMN graph_id,
    DROP COLUMN display_name,
    DROP COLUMN institution_slug;

ALTER TABLE syllabus
    ADD COLUMN display_name TEXT;

-- A migrated Syllabus with a known Institution uses its existing manual title
-- for the curricular-unit label. The old graph label remains in the archive.
UPDATE syllabus
SET display_name = title
WHERE institution_id IS NOT NULL
  AND title = btrim(title)
  AND char_length(title) BETWEEN 1 AND 255
  AND title !~ '[[:cntrl:]]';

ALTER TABLE syllabus
    ADD CONSTRAINT syllabus_metadata_shape CHECK (
        display_name IS NULL
        OR (
            display_name = btrim(display_name)
            AND char_length(display_name) BETWEEN 1 AND 255
            AND display_name !~ '[[:cntrl:]]'
        )
    ),
    ADD CONSTRAINT syllabus_id_institution_key UNIQUE (id, institution_id);

ALTER TABLE study_group
    ADD CONSTRAINT study_group_id_institution_key UNIQUE (id, institution_id);

ALTER TABLE syllabus
    ADD CONSTRAINT syllabus_group_institution_fkey
    FOREIGN KEY (group_id, institution_id)
    REFERENCES study_group (id, institution_id);

CREATE TABLE lesson_subject (
    id             TEXT PRIMARY KEY,
    institution_id TEXT NOT NULL REFERENCES institution (id),
    code           TEXT NOT NULL CHECK (code ~ '^[A-Z][A-Z0-9_-]{0,31}$'),
    display_name   TEXT NOT NULL CHECK (
        display_name = btrim(display_name)
        AND char_length(display_name) BETWEEN 1 AND 255
        AND display_name !~ '[[:cntrl:]]'
    ),
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution_id, code),
    UNIQUE (id, institution_id)
);

CREATE FUNCTION lesson_subject_identity_is_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.institution_id IS DISTINCT FROM OLD.institution_id
       OR NEW.code IS DISTINCT FROM OLD.code THEN
        RAISE EXCEPTION 'Lesson Subject identity is immutable';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER lesson_subject_identity_is_immutable_trigger
BEFORE UPDATE ON lesson_subject
FOR EACH ROW EXECUTE FUNCTION lesson_subject_identity_is_immutable();

CREATE TABLE syllabus_lesson_subject (
    syllabus_id       TEXT NOT NULL,
    lesson_subject_id TEXT NOT NULL,
    institution_id    TEXT NOT NULL,
    PRIMARY KEY (syllabus_id, lesson_subject_id),
    FOREIGN KEY (syllabus_id, institution_id)
        REFERENCES syllabus (id, institution_id),
    FOREIGN KEY (lesson_subject_id, institution_id)
        REFERENCES lesson_subject (id, institution_id)
);
