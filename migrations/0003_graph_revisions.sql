-- Record whole-Lesson decisions and assemble immutable Subject Graph Revisions.

CREATE FUNCTION reject_immutable_fact_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% rows are immutable', TG_TABLE_NAME;
END;
$$;

ALTER TABLE lesson_build
    ADD COLUMN syllabus_id text REFERENCES syllabus(id);

UPDATE lesson_build build
SET syllabus_id = version.syllabus_id
FROM syllabus_version version
WHERE version.id = build.version_id;

ALTER TABLE lesson_build
    ALTER COLUMN syllabus_id SET NOT NULL;

ALTER TABLE syllabus_version
    ADD CONSTRAINT syllabus_version_id_syllabus_id_key UNIQUE (id, syllabus_id);

ALTER TABLE lesson_build
    ADD CONSTRAINT lesson_build_version_syllabus_fkey
    FOREIGN KEY (version_id, syllabus_id)
    REFERENCES syllabus_version(id, syllabus_id);

CREATE FUNCTION fill_lesson_build_syllabus_id() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.syllabus_id IS NULL THEN
        SELECT version.syllabus_id INTO NEW.syllabus_id
        FROM syllabus_version version
        WHERE version.id = NEW.version_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER lesson_build_fill_syllabus_id
BEFORE INSERT ON lesson_build
FOR EACH ROW EXECUTE FUNCTION fill_lesson_build_syllabus_id();

DROP INDEX lesson_build_one_active_per_lesson_idx;

WITH ranked_active AS (
    SELECT build.id,
        row_number() OVER (
            PARTITION BY build.syllabus_id, build.lesson_id
            ORDER BY build.request_seq DESC
        ) AS position
    FROM lesson_build build
    WHERE build.is_active
)
UPDATE lesson_build build
SET status = 'failed',
    is_active = false,
    failure_code = 'superseded_active_build',
    failure_message = 'A newer active build for this stable Lesson already exists.',
    finished_at = now()
FROM ranked_active ranked
WHERE build.id = ranked.id AND ranked.position > 1;

CREATE UNIQUE INDEX lesson_build_one_active_per_lesson_idx
    ON lesson_build(syllabus_id, lesson_id) WHERE is_active;

CREATE TABLE whole_lesson_review (
    build_id text PRIMARY KEY REFERENCES lesson_build(id),
    decision text NOT NULL CHECK (decision IN ('accepted', 'rejected')),
    actor text NOT NULL CHECK (btrim(actor) <> '' AND length(actor) <= 200),
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE graph_revision (
    id text PRIMARY KEY,
    graph_id text NOT NULL REFERENCES syllabus_subject(graph_id),
    revision_number integer NOT NULL CHECK (revision_number >= 1),
    graph_body text NOT NULL,
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    created_by_build_id text NOT NULL UNIQUE REFERENCES lesson_build(id),
    accepted_by text NOT NULL CHECK (
        btrim(accepted_by) <> '' AND length(accepted_by) <= 200
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (graph_id, revision_number),
    UNIQUE (graph_id, id)
);

CREATE TABLE accepted_lesson_ref (
    graph_id text NOT NULL REFERENCES syllabus_subject(graph_id),
    lesson_id text NOT NULL,
    build_id text NOT NULL UNIQUE REFERENCES lesson_build(id),
    checkpoint_id text NOT NULL UNIQUE REFERENCES lesson_build_checkpoint(id),
    week_order integer,
    activity_order integer,
    lesson_seq integer,
    accepted_by text NOT NULL CHECK (
        btrim(accepted_by) <> '' AND length(accepted_by) <= 200
    ),
    accepted_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (graph_id, lesson_id)
);

CREATE TABLE graph_revision_lesson (
    revision_id text NOT NULL REFERENCES graph_revision(id),
    seq integer NOT NULL CHECK (seq >= 1),
    lesson_id text NOT NULL,
    build_id text NOT NULL REFERENCES lesson_build(id),
    checkpoint_id text NOT NULL REFERENCES lesson_build_checkpoint(id),
    fragment_sha256 text NOT NULL CHECK (fragment_sha256 ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (revision_id, lesson_id),
    UNIQUE (revision_id, seq)
);

CREATE TABLE graph_current_revision (
    graph_id text PRIMARY KEY,
    revision_id text NOT NULL UNIQUE,
    updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (graph_id, revision_id) REFERENCES graph_revision(graph_id, id)
);

CREATE TRIGGER whole_lesson_review_immutable
BEFORE UPDATE OR DELETE ON whole_lesson_review
FOR EACH ROW EXECUTE FUNCTION reject_immutable_fact_mutation();

CREATE TRIGGER lesson_build_checkpoint_immutable
BEFORE UPDATE OR DELETE ON lesson_build_checkpoint
FOR EACH ROW EXECUTE FUNCTION reject_immutable_fact_mutation();

CREATE TRIGGER graph_revision_immutable
BEFORE UPDATE OR DELETE ON graph_revision
FOR EACH ROW EXECUTE FUNCTION reject_immutable_fact_mutation();

CREATE TRIGGER graph_revision_lesson_immutable
BEFORE UPDATE OR DELETE ON graph_revision_lesson
FOR EACH ROW EXECUTE FUNCTION reject_immutable_fact_mutation();
