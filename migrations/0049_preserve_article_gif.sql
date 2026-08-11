-- Public articles can contain pedagogical GIF diagrams. Preserve their
-- immutable original bytes while the grouped visual path analyzes a bounded
-- first-frame PNG/JPEG representation. Keep every MIME admitted by 0026.

ALTER TABLE source_asset
    DROP CONSTRAINT source_asset_mime_type_check;

ALTER TABLE source_asset
    ADD CONSTRAINT source_asset_mime_type_check CHECK (
        mime_type IN (
            'application/pdf',
            'image/png',
            'image/jpeg',
            'image/webp',
            'image/avif',
            'image/svg+xml',
            'image/gif'
        )
    );
