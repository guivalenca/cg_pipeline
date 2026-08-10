-- Lesson visibility is authored Syllabus state. Like source-reference
-- visibility, it is copied into each immutable version and exported to XLSX.
ALTER TABLE syllabus_lesson
    ADD COLUMN is_hidden BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX syllabus_lesson_visible_idx
    ON syllabus_lesson (version_id, week, seq, id)
    WHERE NOT is_hidden;
