-- Ordered raster evidence (manual screenshots or captured book pages) enters
-- the existing PDF document/figure pipeline through one derived transport PDF.
-- Original pages and exact reader text remain immutable source evidence.

ALTER TABLE source_asset DROP CONSTRAINT source_asset_kind_check;
ALTER TABLE source_asset ADD CONSTRAINT source_asset_kind_check CHECK (
    kind IN (
        'pdf', 'ordered_document_pdf', 'pdf_page', 'pdf_figure',
        'screenshot', 'image', 'article_image', 'book_page'
    )
);

ALTER TABLE source_asset DROP CONSTRAINT source_asset_kind_mime;
ALTER TABLE source_asset ADD CONSTRAINT source_asset_kind_mime CHECK (
    (kind IN ('pdf', 'ordered_document_pdf')
        AND mime_type = 'application/pdf')
    OR (kind IN (
        'pdf_page', 'pdf_figure', 'screenshot', 'image',
        'article_image', 'book_page'
    ) AND mime_type LIKE 'image/%')
);

ALTER TABLE source_asset DROP CONSTRAINT source_asset_byte_size_check;
ALTER TABLE source_asset ADD CONSTRAINT source_asset_byte_size_check CHECK (
    byte_size > 0 AND byte_size <= 52428800
);

CREATE TABLE source_asset_text (
    source_asset_id TEXT PRIMARY KEY REFERENCES source_asset (id),
    body            TEXT NOT NULL,
    text_sha256     TEXT NOT NULL CHECK (text_sha256 ~ '^[0-9a-f]{64}$'),
    tool            TEXT NOT NULL CHECK (btrim(tool) <> ''),
    tool_version    TEXT NOT NULL CHECK (btrim(tool_version) <> ''),
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER source_asset_text_immutable
BEFORE UPDATE OR DELETE ON source_asset_text
FOR EACH ROW EXECUTE FUNCTION reject_source_asset_mutation();
