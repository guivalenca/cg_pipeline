-- YouTube frames reuse the shared immutable visual-evidence ledger without
-- narrowing any of the ordered-document, PDF, article, or book evidence kinds.

ALTER TABLE source_asset
    DROP CONSTRAINT source_asset_kind_check;

ALTER TABLE source_asset
    ADD CONSTRAINT source_asset_kind_check CHECK (
        kind IN (
            'pdf', 'ordered_document_pdf', 'pdf_page', 'pdf_figure',
            'screenshot', 'image', 'article_image', 'book_page', 'video_frame'
        )
    );

ALTER TABLE source_asset
    DROP CONSTRAINT source_asset_kind_mime;

ALTER TABLE source_asset
    ADD CONSTRAINT source_asset_kind_mime CHECK (
        (kind IN ('pdf', 'ordered_document_pdf')
            AND mime_type = 'application/pdf')
        OR (kind IN (
            'pdf_page', 'pdf_figure', 'screenshot', 'image',
            'article_image', 'book_page', 'video_frame'
        ) AND mime_type LIKE 'image/%')
    );

ALTER TABLE video_preflight
    DROP CONSTRAINT video_preflight_route_check;

ALTER TABLE video_preflight
    ADD CONSTRAINT video_preflight_route_check CHECK (
        route IN (
            'uploaded_caption', 'automatic_stt', 'visual_only', 'approval_required'
        )
    );

ALTER TABLE video_transcript
    DROP CONSTRAINT video_transcript_visual_analysis_check;

ALTER TABLE video_transcript
    ADD CONSTRAINT video_transcript_visual_analysis_check CHECK (
        visual_analysis IN ('deferred', 'pending', 'complete')
    );
