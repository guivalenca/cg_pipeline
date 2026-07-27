-- embeddings are stamped model output like any run; the vector column has no fixed dimension on purpose, because different embedding models coexist in one table (4096, 3072, 1536 dims) and at this scale exact scan beats any index.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE task_embedding (
    run_item_id TEXT PRIMARY KEY REFERENCES run_item (id),
    task_id     TEXT NOT NULL REFERENCES task (id),
    model       TEXT NOT NULL,
    input_sha   TEXT NOT NULL,
    dims        INTEGER NOT NULL,
    embedding   vector NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX task_embedding_task_idx ON task_embedding (task_id);
