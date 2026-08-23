-- A syllabus owns the stable metadata needed to export one current Concept
-- Graph. Existing syllabi remain readable until an operator supplies it.

ALTER TABLE syllabus
    ADD COLUMN graph_id TEXT UNIQUE,
    ADD COLUMN display_name TEXT,
    ADD COLUMN institution_slug TEXT,
    ADD CONSTRAINT syllabus_graph_metadata_shape CHECK (
        (
            graph_id IS NULL
            AND display_name IS NULL
            AND institution_slug IS NULL
        )
        OR
        (
            graph_id ~ '^[a-z][a-z0-9_.-]{1,127}$'
            AND display_name = btrim(display_name)
            AND char_length(display_name) BETWEEN 1 AND 255
            AND display_name !~ '[[:cntrl:]]'
            AND institution_slug ~ '^[a-z][a-z0-9-]{1,63}$'
        )
    );
