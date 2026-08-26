-- Final Syllabus metadata for a fresh installation. Concept Universe data is
-- disposable before deployment, so this migration contains no repair or
-- compatibility path for the temporary metadata models that preceded it.

ALTER TABLE study_group
    ADD CONSTRAINT study_group_id_institution_key
    UNIQUE (id, institution_id);

ALTER TABLE syllabus
    ADD COLUMN institution_id TEXT REFERENCES institution (id),
    ADD COLUMN graph_id TEXT,
    ADD CONSTRAINT syllabus_id_institution_key UNIQUE (id, institution_id),
    ADD CONSTRAINT syllabus_graph_id_key UNIQUE (graph_id),
    ADD CONSTRAINT syllabus_graph_id_shape CHECK (
        graph_id IS NULL OR graph_id ~ '^[a-z][a-z0-9_.-]{1,127}$'
    );

ALTER TABLE syllabus
    ADD CONSTRAINT syllabus_group_institution_fkey
    FOREIGN KEY (group_id, institution_id)
    REFERENCES study_group (id, institution_id);

ALTER TABLE syllabus_lesson
    ADD COLUMN subjects TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[];

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
