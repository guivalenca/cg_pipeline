-- Operational founder review belongs to one immutable lesson version, but is
-- intentionally mutable: marking work done or changing its handling tag must
-- not create a new Syllabus version.
CREATE TABLE syllabus_lesson_review (
    lesson_id      TEXT PRIMARY KEY REFERENCES syllabus_lesson (id),
    is_validated   BOOLEAN NOT NULL DEFAULT FALSE,
    complexity     TEXT CHECK (complexity IN ('simple', 'complex')),
    updated_at     timestamptz NOT NULL DEFAULT now()
);
