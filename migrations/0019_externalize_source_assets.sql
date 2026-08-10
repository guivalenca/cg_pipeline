-- Transitional migration for development databases that applied the first
-- draft of 0012 while source bytes still lived in BYTEA.  No released branch
-- wrote production data in that shape, so refuse to guess a storage key if a
-- row exists.  Fresh databases already have storage_key and take the no-op.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'source_asset'
          AND column_name = 'body'
    ) THEN
        IF EXISTS (SELECT 1 FROM source_asset) THEN
            RAISE EXCEPTION
                'source_asset contains inline bytes; externalize them before applying 0013';
        END IF;

        ALTER TABLE source_asset
            ADD COLUMN IF NOT EXISTS storage_key TEXT;
        ALTER TABLE source_asset
            ALTER COLUMN storage_key SET NOT NULL;
        ALTER TABLE source_asset
            ADD CONSTRAINT source_asset_storage_key_shape CHECK (
                storage_key ~ '^sha256/[0-9a-f]{2}/[0-9a-f]{64}$'
            );
        ALTER TABLE source_asset
            DROP CONSTRAINT IF EXISTS source_asset_body_size;
        ALTER TABLE source_asset
            DROP COLUMN body;
    END IF;
END;
$$;
