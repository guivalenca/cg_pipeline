-- A scheduler claim is durable across Python processes and machines.  The
-- stable scope/stage pair has at most one owner; a new token fences every
-- ownership generation so a recovered orphan cannot mutate its successor.

CREATE TABLE kc_pipeline_lease (
    scope_key    TEXT NOT NULL,
    stage        TEXT NOT NULL,
    token        TEXT NOT NULL,
    owner_id     TEXT NOT NULL,
    acquired_at  timestamptz NOT NULL,
    heartbeat_at timestamptz NOT NULL,
    expires_at   timestamptz NOT NULL,
    PRIMARY KEY (scope_key, stage),
    CONSTRAINT kc_pipeline_lease_scope_key_not_blank
        CHECK (btrim(scope_key) <> ''),
    CONSTRAINT kc_pipeline_lease_stage_not_blank
        CHECK (btrim(stage) <> ''),
    CONSTRAINT kc_pipeline_lease_token_not_blank
        CHECK (btrim(token) <> ''),
    CONSTRAINT kc_pipeline_lease_owner_not_blank
        CHECK (btrim(owner_id) <> ''),
    CONSTRAINT kc_pipeline_lease_expiration_after_heartbeat
        CHECK (expires_at > heartbeat_at)
);
