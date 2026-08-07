-- Organizational structure: institutions, courses, and groups, inherited
-- from Companion's hierarchy. Institutions own courses (academic identity
-- only) and groups; THE GROUP is the sole content authority — a syllabus
-- attaches to a group, never to a course. There is no semester or period
-- entity, on purpose.
--
-- Founder decisions recorded here:
--   * Nothing is ever auto-derived from file names. A "2026-2A" in a
--     workbook filename is NOT a group name.
--   * The founder creates institutions, courses, and groups manually and
--     manually selects which group a syllabus belongs to.
--   * A group MAY reference a course (Companion groups often align to
--     one), but the group, not the course, is where content lives.
--
-- Identity rules come from Companion: an institution's id is its immutable
-- human slug; a course id is lowercase text composed from the institution
-- slug plus the normalized course name; group names are free text, unique
-- per institution case-insensitively.

CREATE TABLE institution (
    id         TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]{1,63}$'),
    name       TEXT NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE course (
    id             TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]{1,127}$'),
    institution_id TEXT NOT NULL REFERENCES institution (id),
    name           TEXT NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, institution_id)
);

-- Named study_group because GROUP is a reserved word; the dashboard says
-- simply "group".
CREATE TABLE study_group (
    id             TEXT PRIMARY KEY,
    institution_id TEXT NOT NULL REFERENCES institution (id),
    name           TEXT NOT NULL,
    course_id      TEXT REFERENCES course (id),
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX study_group_institution_name_key
    ON study_group (institution_id, lower(name));

-- A syllabus is assigned to a group by the founder; NULL means the founder
-- has not selected a group yet, and the dashboard says exactly that.
ALTER TABLE syllabus ADD COLUMN group_id TEXT REFERENCES study_group (id);
