-- Freeze Lesson Build inputs and publish restart-safe creation checkpoints.

ALTER TABLE lesson_build
    ADD COLUMN manifest jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN manifest_sha256 text,
    ADD COLUMN lineage_id text,
    ADD COLUMN previous_build_id text REFERENCES lesson_build(id),
    ADD COLUMN status text NOT NULL DEFAULT 'queued',
    ADD COLUMN is_active boolean NOT NULL DEFAULT true,
    ADD COLUMN failure_code text,
    ADD COLUMN failure_message text,
    ADD COLUMN finished_at timestamptz;

ALTER TABLE lesson_build
    ADD CONSTRAINT lesson_build_manifest_object
        CHECK (jsonb_typeof(manifest) = 'object'),
    ADD CONSTRAINT lesson_build_manifest_hash_shape
        CHECK (manifest_sha256 IS NULL OR manifest_sha256 ~ '^[0-9a-f]{64}$'),
    ADD CONSTRAINT lesson_build_status_check
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed'));

-- DEV-76 permitted more than one historical request per Lesson. Derive their
-- terminal state before enforcing the single active-build invariant.
UPDATE lesson_build build
SET status = CASE
        WHEN EXISTS (
            SELECT 1 FROM lesson_build_work work
            WHERE work.build_id = build.id AND work.status = 'running'
        ) THEN 'running'
        WHEN EXISTS (
            SELECT 1 FROM lesson_build_work work
            WHERE work.build_id = build.id AND work.status = 'queued'
        ) THEN 'queued'
        WHEN EXISTS (
            SELECT 1 FROM lesson_build_work work
            WHERE work.build_id = build.id AND work.status = 'failed'
        ) THEN 'failed'
        ELSE 'succeeded'
    END,
    is_active = false;

WITH latest_pending AS (
    SELECT DISTINCT ON (version_id, lesson_id) id
    FROM lesson_build
    WHERE status IN ('queued', 'running')
    ORDER BY version_id, lesson_id, request_seq DESC
)
UPDATE lesson_build build
SET is_active = true
FROM latest_pending
WHERE build.id = latest_pending.id;

CREATE UNIQUE INDEX lesson_build_one_active_per_lesson_idx
    ON lesson_build(version_id, lesson_id) WHERE is_active;

CREATE TABLE lesson_build_reference (
    build_id text NOT NULL REFERENCES lesson_build(id),
    seq integer NOT NULL CHECK (seq >= 1),
    reference_id text NOT NULL REFERENCES syllabus_source_reference(id),
    work_id text NOT NULL REFERENCES lesson_build_work(id),
    PRIMARY KEY (build_id, reference_id),
    UNIQUE (build_id, seq)
);

CREATE TABLE lesson_build_checkpoint (
    id text PRIMARY KEY,
    build_id text NOT NULL REFERENCES lesson_build(id),
    stage text NOT NULL,
    family text NOT NULL CHECK (family IN (
        'candidate_concepts', 'lesson_concepts', 'lesson_segments',
        'knowledge_types', 'lesson_fragment', 'raw_artifacts'
    )),
    path text NOT NULL,
    body text NOT NULL,
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    stage_fingerprint text NOT NULL CHECK (stage_fingerprint ~ '^[0-9a-f]{64}$'),
    is_stage_result boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (build_id, stage, path)
);

CREATE INDEX lesson_build_checkpoint_family_idx
    ON lesson_build_checkpoint(build_id, family, created_at, id);

ALTER TABLE run_item
    ADD COLUMN lesson_build_id text REFERENCES lesson_build(id),
    ADD COLUMN lesson_id text,
    ADD COLUMN requested_model text,
    ADD COLUMN response_model text,
    ADD COLUMN provider text,
    ADD COLUMN generation_id text,
    ADD COLUMN outcome text,
    ADD COLUMN attempt_token text;

CREATE INDEX run_item_lesson_build_idx
    ON run_item(lesson_build_id, created_at, id)
    WHERE lesson_build_id IS NOT NULL;
