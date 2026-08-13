-- Operational claims are short scheduler leases over lesson-local work.  They
-- do not replace the child-owned kc_pipeline stage lease: a scheduler releases
-- its claim after launching or observing exactly one stage.

ALTER TABLE lesson_knowledge_work
    ADD COLUMN available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN claim_count INTEGER NOT NULL DEFAULT 0 CHECK (claim_count >= 0),
    ADD COLUMN claimed_at TIMESTAMPTZ,
    ADD COLUMN claim_token TEXT,
    ADD COLUMN lease_expires_at TIMESTAMPTZ,
    ADD COLUMN last_launched_stage TEXT,
    ADD CONSTRAINT lesson_knowledge_work_claim_shape CHECK (
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
    ),
    ADD CONSTRAINT lesson_knowledge_work_last_launch_not_blank CHECK (
        last_launched_stage IS NULL OR btrim(last_launched_stage) <> ''
    ),
    ADD CONSTRAINT lesson_knowledge_work_failure_shape CHECK (
        (status = 'failed' AND failure_code IS NOT NULL
            AND btrim(failure_code) <> '')
        OR (status <> 'failed' AND failure_code IS NULL)
    );

CREATE INDEX lesson_knowledge_work_claim_idx
    ON lesson_knowledge_work (available_at, created_at, id)
    WHERE status IN ('queued', 'running');
