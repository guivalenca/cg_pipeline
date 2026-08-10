-- Figures extracted by Firecrawl are source-local evidence, distinct from
-- full-page Poppler renders retained only for auditing.

ALTER TABLE source_asset DROP CONSTRAINT source_asset_kind_check;
ALTER TABLE source_asset ADD CONSTRAINT source_asset_kind_check CHECK (
    kind IN (
        'pdf', 'pdf_page', 'pdf_figure', 'screenshot', 'image', 'article_image'
    )
);

ALTER TABLE source_asset DROP CONSTRAINT source_asset_kind_mime;
ALTER TABLE source_asset ADD CONSTRAINT source_asset_kind_mime CHECK (
    (kind = 'pdf' AND mime_type = 'application/pdf')
    OR (kind IN (
        'pdf_page', 'pdf_figure', 'screenshot', 'image', 'article_image'
    ) AND mime_type LIKE 'image/%')
);
