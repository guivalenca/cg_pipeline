-- A lesson KC build is the durable, explicitly requested interpretation of
-- one immutable syllabus lesson.  It pins every active source reference in
-- syllabus order and creates local work only once per Source Publication.

CREATE TABLE lesson_knowledge_build (
    id           TEXT PRIMARY KEY,
    request_seq  BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE,
    version_id   TEXT NOT NULL,
    lesson_id    TEXT NOT NULL,
    request_key  TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (version_id, lesson_id)
        REFERENCES syllabus_lesson (version_id, id),
    UNIQUE (version_id, lesson_id, request_key),
    CONSTRAINT lesson_knowledge_build_id_not_blank
        CHECK (btrim(id) <> ''),
    CONSTRAINT lesson_knowledge_build_request_key_shape
        CHECK (btrim(request_key) <> '' AND length(request_key) <= 200),
    CONSTRAINT lesson_knowledge_build_actor_shape
        CHECK (btrim(requested_by) <> '' AND length(requested_by) <= 200)
);

CREATE INDEX lesson_knowledge_build_lesson_latest_idx
    ON lesson_knowledge_build (version_id, lesson_id, request_seq DESC);

CREATE TABLE lesson_knowledge_work (
    id                              TEXT PRIMARY KEY,
    build_id                        TEXT NOT NULL
                                        REFERENCES lesson_knowledge_build (id),
    seq                             INTEGER NOT NULL CHECK (seq >= 1),
    source_id                       TEXT NOT NULL REFERENCES source (id),
    snapshot_id                     TEXT NOT NULL REFERENCES source_snapshot (id),
    artifact_id                     TEXT NOT NULL REFERENCES artifact (id),
    content_hash                    TEXT NOT NULL,
    publication_is_previous_attempt BOOLEAN NOT NULL DEFAULT FALSE,
    status                          TEXT NOT NULL DEFAULT 'queued'
                                        CHECK (status IN (
                                            'queued', 'running',
                                            'succeeded', 'failed'
                                        )),
    stage                           TEXT,
    failure_code                    TEXT,
    diagnostics                     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (build_id, id),
    UNIQUE (build_id, seq),
    UNIQUE (build_id, artifact_id),
    CONSTRAINT lesson_knowledge_work_id_not_blank
        CHECK (btrim(id) <> ''),
    CONSTRAINT lesson_knowledge_work_content_hash_not_blank
        CHECK (btrim(content_hash) <> ''),
    CONSTRAINT lesson_knowledge_work_diagnostics_object
        CHECK (jsonb_typeof(diagnostics) = 'object')
);

CREATE INDEX lesson_knowledge_work_status_idx
    ON lesson_knowledge_work (status, created_at, id);

CREATE TABLE lesson_knowledge_reference (
    build_id    TEXT NOT NULL REFERENCES lesson_knowledge_build (id),
    seq         INTEGER NOT NULL CHECK (seq >= 1),
    reference_id TEXT NOT NULL REFERENCES syllabus_source_reference (id),
    work_id     TEXT NOT NULL,
    PRIMARY KEY (build_id, seq),
    UNIQUE (build_id, reference_id),
    FOREIGN KEY (build_id, work_id)
        REFERENCES lesson_knowledge_work (build_id, id)
);

CREATE INDEX lesson_knowledge_reference_work_idx
    ON lesson_knowledge_reference (build_id, work_id, seq);
