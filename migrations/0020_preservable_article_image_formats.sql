-- Article pages increasingly use AVIF and SVG for both pedagogical visuals
-- and website chrome. The acquisition branch preserves these original bytes
-- even though the current visual model accepts only PNG, JPEG and WebP.

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
            'image/svg+xml'
        )
    );
