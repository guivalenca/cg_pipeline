-- The exported graph identity belongs to a Syllabus. Lesson Subjects are a
-- projection of the latest Syllabus Version, not a second manually maintained
-- catalog. Course and Group remain outside the graph-package seam.

DROP TABLE syllabus_lesson_subject;
DROP TABLE lesson_subject;
DROP FUNCTION lesson_subject_identity_is_immutable();

ALTER TABLE syllabus
    DROP CONSTRAINT syllabus_metadata_shape,
    DROP COLUMN display_name,
    ADD COLUMN graph_id TEXT;

-- Preserve every valid graph identity exposed by the previous bridge when its
-- Institution was resolved. New Syllabi use the name-based domain generator;
-- unresolved legacy rows stay unexportable until an operator repairs them.
UPDATE syllabus AS current
SET graph_id = legacy.graph_id
FROM syllabus_legacy_graph_metadata AS legacy
WHERE legacy.syllabus_id = current.id
  AND current.institution_id IS NOT NULL
  AND legacy.graph_id ~ '^[a-z][a-z0-9_.-]{1,127}$';

ALTER TABLE syllabus
    ADD CONSTRAINT syllabus_graph_id_key UNIQUE (graph_id),
    ADD CONSTRAINT syllabus_graph_id_shape CHECK (
        graph_id IS NULL OR graph_id ~ '^[a-z][a-z0-9_.-]{1,127}$'
    );

CREATE FUNCTION syllabus_graph_identity_is_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.graph_id IS NOT NULL AND NEW.graph_id IS DISTINCT FROM OLD.graph_id THEN
        RAISE EXCEPTION 'Syllabus graph identity is immutable';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER syllabus_graph_identity_is_immutable_trigger
BEFORE UPDATE ON syllabus
FOR EACH ROW EXECUTE FUNCTION syllabus_graph_identity_is_immutable();
