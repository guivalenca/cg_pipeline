CREATE TABLE syllabus_source_review (
    reference_id TEXT PRIMARY KEY REFERENCES syllabus_source_reference(id),
    is_validated BOOLEAN NOT NULL DEFAULT FALSE,
    complexity TEXT CHECK (complexity IN ('simple', 'complex')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Preserve any markers authored during the brief lesson-level rollout by
-- applying them to the lesson's existing auto-studies. The legacy table stays
-- as an audit trail but is no longer read by the application.
INSERT INTO syllabus_source_review (reference_id, is_validated, complexity, updated_at)
SELECT sr.id, lr.is_validated, lr.complexity, lr.updated_at
FROM syllabus_lesson_review lr
JOIN syllabus_source_reference sr ON sr.lesson_id = lr.lesson_id
ON CONFLICT (reference_id) DO NOTHING;
