-- A KC corpus is the immutable, exact set of Canonical Source Publications
-- interpreted together.  Its identity is derived only from the ordered
-- source/artifact members; origin records why the first creator sealed it.

CREATE TABLE kc_corpus_manifest (
    id              TEXT PRIMARY KEY,
    manifest_sha256 TEXT NOT NULL UNIQUE,
    origin          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kc_corpus_manifest_id_not_blank
        CHECK (btrim(id) <> ''),
    CONSTRAINT kc_corpus_manifest_sha256_shape
        CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT kc_corpus_manifest_origin_object
        CHECK (jsonb_typeof(origin) = 'object')
);

CREATE TABLE kc_corpus_manifest_member (
    manifest_id TEXT NOT NULL REFERENCES kc_corpus_manifest (id),
    seq         INTEGER NOT NULL CHECK (seq >= 1),
    source_id   TEXT NOT NULL REFERENCES source (id),
    artifact_id TEXT NOT NULL REFERENCES artifact (id),
    PRIMARY KEY (manifest_id, seq),
    UNIQUE (manifest_id, source_id),
    UNIQUE (manifest_id, artifact_id)
);

CREATE INDEX kc_corpus_manifest_member_source_idx
    ON kc_corpus_manifest_member (source_id);

CREATE INDEX kc_corpus_manifest_member_artifact_idx
    ON kc_corpus_manifest_member (artifact_id);
