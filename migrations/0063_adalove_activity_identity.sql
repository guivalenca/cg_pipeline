-- Keep the Adalove identity and both ordering keys beside every immutable
-- lesson/reference projection. UUIDs match the same activity across exported
-- snapshots even when its title, week, or neighbors change.

ALTER TABLE syllabus_lesson
    ADD COLUMN activity_uuid TEXT,
    ADD COLUMN folder_uuid TEXT,
    ADD COLUMN week_order INTEGER,
    ADD COLUMN activity_order INTEGER;

CREATE UNIQUE INDEX syllabus_lesson_adalove_activity_idx
    ON syllabus_lesson (version_id, activity_uuid)
    WHERE activity_uuid IS NOT NULL;

ALTER TABLE syllabus_source_reference
    ADD COLUMN activity_uuid TEXT,
    ADD COLUMN folder_uuid TEXT,
    ADD COLUMN week_order INTEGER,
    ADD COLUMN activity_order INTEGER,
    ADD COLUMN parent_activity_uuid TEXT,
    ADD COLUMN parent_inference TEXT;

CREATE INDEX syllabus_source_reference_adalove_activity_idx
    ON syllabus_source_reference (version_id, activity_uuid, seq, id)
    WHERE activity_uuid IS NOT NULL;
