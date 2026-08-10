-- Visibility belongs to a source's placement in one immutable Syllabus
-- version.  It does not mutate or delete the logical Source, its acquisition
-- attempts, assets, Markdown artifacts, or later interpretations.

ALTER TABLE syllabus_source_reference
    ADD COLUMN is_hidden BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX syllabus_source_reference_visible_idx
    ON syllabus_source_reference (version_id, lesson_id, seq, id)
    WHERE NOT is_hidden;
