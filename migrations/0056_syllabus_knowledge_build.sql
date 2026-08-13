-- A syllabus-level knowledge build is an explicit checkpoint over one
-- immutable Syllabus Version.  The referenced corpus manifest is already the
-- exact, content-addressed set of Source Publications; this row records who
-- requested interpreting that set together and safely schedules its four
-- shared KC stages.

CREATE TABLE syllabus_knowledge_build (
    id                  TEXT PRIMARY KEY,
    request_seq         BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE,
    version_id          TEXT NOT NULL REFERENCES syllabus_version (id),
    request_key         TEXT NOT NULL,
    requested_by        TEXT NOT NULL,
    manifest_id         TEXT NOT NULL REFERENCES kc_corpus_manifest (id),
    status              TEXT NOT NULL DEFAULT 'queued'
                            CHECK (status IN (
                                'queued', 'running', 'succeeded', 'failed'
                            )),
    stage               TEXT,
    last_launched_stage TEXT,
    failure_code        TEXT,
    diagnostics         JSONB NOT NULL DEFAULT '{}'::jsonb,
    available_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    claim_count         INTEGER NOT NULL DEFAULT 0 CHECK (claim_count >= 0),
    claimed_at          TIMESTAMPTZ,
    claim_token         TEXT,
    lease_expires_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (version_id, request_key),
    CONSTRAINT syllabus_knowledge_build_id_not_blank
        CHECK (btrim(id) <> ''),
    CONSTRAINT syllabus_knowledge_build_request_key_shape
        CHECK (btrim(request_key) <> '' AND length(request_key) <= 200),
    CONSTRAINT syllabus_knowledge_build_actor_shape
        CHECK (btrim(requested_by) <> '' AND length(requested_by) <= 200),
    CONSTRAINT syllabus_knowledge_build_stage_not_blank
        CHECK (stage IS NULL OR btrim(stage) <> ''),
    CONSTRAINT syllabus_knowledge_build_last_launch_not_blank
        CHECK (
            last_launched_stage IS NULL OR btrim(last_launched_stage) <> ''
        ),
    CONSTRAINT syllabus_knowledge_build_failure_shape CHECK (
        (
            status = 'failed'
            AND failure_code IS NOT NULL
            AND btrim(failure_code) <> ''
        )
        OR (status <> 'failed' AND failure_code IS NULL)
    ),
    CONSTRAINT syllabus_knowledge_build_diagnostics_object
        CHECK (jsonb_typeof(diagnostics) = 'object'),
    CONSTRAINT syllabus_knowledge_build_claim_shape CHECK (
        (
            claim_token IS NULL
            AND claimed_at IS NULL
            AND lease_expires_at IS NULL
        )
        OR (
            claim_token IS NOT NULL
            AND btrim(claim_token) <> ''
            AND claimed_at IS NOT NULL
            AND lease_expires_at > claimed_at
        )
    )
);

CREATE INDEX syllabus_knowledge_build_version_latest_idx
    ON syllabus_knowledge_build (version_id, request_seq DESC);

CREATE INDEX syllabus_knowledge_build_claim_idx
    ON syllabus_knowledge_build (available_at, created_at, id)
    WHERE status IN ('queued', 'running');
