-- Immutable outcome for every semantic region returned by a durable PDF
-- figure-localization call.  The row explains whether the region became an
-- anchored asset, an explicit unanchored fallback, a duplicate, or a failure.

CREATE TABLE pdf_figure_region_outcome (
    id                    TEXT PRIMARY KEY,
    localization_call_id  TEXT NOT NULL REFERENCES pdf_figure_localization_call (id),
    region_ordinal        INTEGER NOT NULL CHECK (region_ordinal > 0),
    page_id               TEXT NOT NULL REFERENCES source_pdf_page (id),
    model_bbox            JSONB NOT NULL CHECK (jsonb_typeof(model_bbox) = 'array'),
    final_bbox            JSONB NOT NULL CHECK (jsonb_typeof(final_bbox) = 'array'),
    description           TEXT NOT NULL,
    visible_text          TEXT NOT NULL DEFAULT '',
    anchor_id             TEXT NOT NULL DEFAULT '',
    status                TEXT NOT NULL CHECK (
        status IN ('placed', 'unanchored', 'duplicate', 'failed')
    ),
    source_asset_id       TEXT REFERENCES source_asset (id),
    diagnostics           JSONB NOT NULL DEFAULT '{}',
    created_at            timestamptz NOT NULL DEFAULT now(),
    UNIQUE (localization_call_id, region_ordinal),
    CONSTRAINT pdf_figure_region_asset_shape CHECK (
        (status IN ('placed', 'unanchored') AND source_asset_id IS NOT NULL)
        OR (status IN ('duplicate', 'failed') AND source_asset_id IS NULL)
    )
);

CREATE INDEX pdf_figure_region_outcome_call_idx
    ON pdf_figure_region_outcome (localization_call_id, region_ordinal);

CREATE INDEX pdf_figure_region_outcome_asset_idx
    ON pdf_figure_region_outcome (source_asset_id)
    WHERE source_asset_id IS NOT NULL;
