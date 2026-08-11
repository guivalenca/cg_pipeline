"""Manual source fallback tests. External extractors and models are always faked."""

import psycopg
import pytest
from psycopg.types.json import Jsonb

from universe.assets import LocalAssetStore, StoredAsset
from universe.acquisition.manual_uploads import (
    ManualAsset,
    acquire_manual_upload,
    create_manual_upload_job,
    list_manual_assets,
    manual_upload_outcome,
    validate_manual_assets,
)
from universe.acquisition.runner import claim_next_job
from universe.acquisition.pdfs import (
    PdfFigureLocalizationResult,
    PdfPage,
    PdfParseResult,
)
from universe.acquisition.source_images import (
    SourceImageAnalysis,
    SourceImageBatchResult,
    input_manifest_hash,
)


def png_bytes(width=20, height=10):
    return (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def no_pdf_figures(_context, _images):
    return PdfFigureLocalizationResult(
        regions=(),
        requested_model="fake/vision",
        response_model="fake/vision-resolved",
        provider="Fake Provider",
        usage={},
        duration_ms=1,
    )


def jpeg_bytes(width=30, height=15):
    return (
        b"\xff\xd8"
        + b"\xff\xc0\x00\x11\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
        + b"\xff\xd9"
    )


def webp_bytes(width=40, height=20):
    dimensions = (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    payload = b"VP8X" + (10).to_bytes(4, "little") + b"\x00\x00\x00\x00" + dimensions
    return b"RIFF" + (len(payload) + 4).to_bytes(4, "little") + b"WEBP" + payload


def pdf_text_only_batch(context, images):
    return SourceImageBatchResult(
        analyses={
            image.image_id: SourceImageAnalysis(
                image_id=image.image_id,
                retain=False,
                reason_code="no_unique_content",
                ocr=None,
                description=None,
                limitations=None,
            )
            for image in images
        },
        unresolved={},
        requested_model="fake/pdf-vision",
        response_model="fake/pdf-vision-resolved",
        provider="Fake Provider",
        usage={"total_tokens": 10},
        duration_ms=3,
        prompt_ref="pdf-page-analysis/v001",
        prompt_sha="a" * 64,
        input_manifest_hash=input_manifest_hash(context, images),
    )


def test_one_pdf_is_a_valid_manual_source_input():
    asset = ManualAsset(
        filename="lesson.pdf",
        mime_type="application/pdf",
        body=b"%PDF-1.7\nfixture",
        kind="pdf",
    )

    validated = validate_manual_assets([asset])

    assert len(validated) == 1
    assert validated[0].filename == "lesson.pdf"
    assert validated[0].ordinal == 1
    assert validated[0].sha256


def test_raster_inputs_keep_the_explicit_order_and_image_kind():
    assets = [
        ManualAsset("page-2.png", "image/png", png_bytes(), "screenshot"),
        ManualAsset("diagram.jpg", "image/jpeg", jpeg_bytes(), "image"),
        ManualAsset("page-3.webp", "image/webp", webp_bytes(), "screenshot"),
    ]

    validated = validate_manual_assets(assets)

    assert [(item.ordinal, item.filename, item.kind) for item in validated] == [
        (1, "page-2.png", "screenshot"),
        (2, "diagram.jpg", "image"),
        (3, "page-3.webp", "screenshot"),
    ]
    assert [item.mime_type for item in validated] == [
        "image/png",
        "image/jpeg",
        "image/webp",
    ]


def test_manual_upload_is_durable_and_ordered_before_processing(db, tmp_path):
    source_id = "source-manual-upload-ordered"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/interactive"}), "Interactive source"),
    )
    db.commit()

    store = LocalAssetStore(tmp_path / "assets")
    job = create_manual_upload_job(
        db,
        source_id,
        [
            ManualAsset("second.png", "image/png", png_bytes(), "screenshot"),
            ManualAsset("diagram.jpg", "image/jpeg", jpeg_bytes(), "image"),
        ],
        asset_store=store,
    )

    assert job["source_id"] == source_id
    assert job["status"] == "queued"
    assert job["provider"] == "manual-upload/v1"
    assert job["diagnostics"]["asset_count"] == 2
    assert job["diagnostics"]["input_mode"] == "images"
    assert len(job["diagnostics"]["input_manifest_sha256"]) == 64
    persisted = list_manual_assets(db, job["id"])
    assert [
        (asset["ordinal"], asset["kind"], asset["filename"], asset["byte_size"])
        for asset in persisted
    ] == [
        (1, "screenshot", "second.png", len(png_bytes())),
        (2, "image", "diagram.jpg", len(jpeg_bytes())),
    ]
    assert store.get(persisted[0]["storage_key"]) == png_bytes()
    columns = {
        row[0]
        for row in db.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = 'source_asset'"
        )
    }
    assert "storage_key" in columns
    assert "body" not in columns


def test_persisted_source_assets_cannot_be_edited_or_deleted(db, tmp_path):
    source_id = "source-manual-assets-immutable"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/immutable"}), "Immutable"),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    job = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("page.png", "image/png", png_bytes(), "screenshot")],
        asset_store=store,
    )
    asset_id = list_manual_assets(db, job["id"])[0]["id"]

    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        db.execute("UPDATE source_asset SET filename = 'changed.png' WHERE id = %s", (asset_id,))
    db.rollback()

    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        db.execute("DELETE FROM source_asset WHERE id = %s", (asset_id,))
    db.rollback()


def test_failed_transaction_never_deletes_a_shared_content_addressed_object(db):
    source_id = "source-manual-storage-rollback"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/rollback"}), "Rollback"),
    )
    db.commit()

    class InvalidKeyStore:
        def __init__(self):
            self.deleted = []

        def put(self, body, *, sha256=None):
            return StoredAsset("invalid-storage-key", sha256, True)

        def get(self, key):
            raise AssertionError("not read")

        def delete(self, key):
            self.deleted.append(key)

    store = InvalidKeyStore()

    with pytest.raises(psycopg.errors.CheckViolation):
        create_manual_upload_job(
            db,
            source_id,
            [ManualAsset("page.png", "image/png", png_bytes(), "screenshot")],
            asset_store=store,
        )

    # Another concurrent transaction may already reference the same digest.
    # Orphan reconciliation is safe; eager deletion is not.
    assert store.deleted == []
    assert db.execute(
        "SELECT count(*) FROM acquisition_job WHERE source_id = %s", (source_id,)
    ).fetchone()[0] == 0


def test_pdf_manual_acquisition_links_original_and_queues_canonical_cleanup(db, tmp_path):
    source_id = "source-manual-pdf-markdown"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/private-doc"}), "Private lesson"),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("private lesson.pdf", "application/pdf", b"%PDF-1.7\nfixture", "pdf")],
        asset_store=store,
    )
    extractor_calls = []

    def fake_pdf_pages(body):
        extractor_calls.append(body)
        return [
            PdfPage(
                1,
                "First paragraph.\n\nSecond paragraph.",
                png_bytes(),
                20,
                10,
            )
        ]

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=lambda *_args: PdfParseResult(
            markdown="First paragraph.\n\nSecond paragraph.\n",
            image_urls=(),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        ),
        pdf_figure_locator=no_pdf_figures,
        pdf_page_extractor=fake_pdf_pages,
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert extractor_calls == [b"%PDF-1.7\nfixture"]
    asset = list_manual_assets(db, job["id"])[0]
    artifact = db.execute(
        "SELECT kind, tool, tool_version, body FROM artifact WHERE id = %s",
        (job["artifact_id"],),
    ).fetchone()
    assert artifact[0:3] == (
        "markdown",
        "pdf-document-association",
        "firecrawl-pdf.v1",
    )
    assert f"[Open original PDF](/api/source-assets/{asset['id']})" in artifact[3]
    assert "## Page 1" not in artifact[3]
    assert "First paragraph." in artifact[3]
    assert "Second paragraph." in artifact[3]
    assert job["diagnostics"]["input_mode"] == "pdf"
    assert job["diagnostics"]["extractor"] == {
        "document_tool": "firecrawl-parse",
        "document_tool_version": "firecrawl-v2-parse.v1",
        "document_mode": "auto",
        "render_tool": "pdftoppm",
        "render_tool_version": "pdftoppm-png-144dpi.v1",
    }
    assert db.execute(
        "SELECT count(*) FROM block WHERE artifact_id = %s", (job["artifact_id"],)
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM passage WHERE artifact_id = %s", (job["artifact_id"],)
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT status FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone() == ("queued",)


def test_claimed_job_can_build_an_outcome_without_double_claim_or_finalization(db, tmp_path):
    source_id = "source-manual-claimed-outcome"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/manual"}), "Manual source"),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("source.pdf", "application/pdf", b"%PDF-1.7\nfixture", "pdf")],
        asset_store=store,
    )
    claimed = claim_next_job(db, job_id=queued["id"])

    outcome = manual_upload_outcome(
        db,
        claimed,
        pdf_document_parser=lambda *_args: PdfParseResult(
            markdown="Extracted text\n",
            image_urls=(),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        ),
        pdf_figure_locator=no_pdf_figures,
        pdf_page_extractor=lambda _body: [
            PdfPage(1, "Extracted text", png_bytes(), 20, 10)
        ],
        asset_store=store,
    )

    assert outcome.succeeded
    assert outcome.tool == "pdf-document-association"
    assert outcome.tool_version == "firecrawl-pdf.v1"
    assert "Extracted text" in outcome.markdown
    assert outcome.raw_markdown
    assert db.execute(
        "SELECT status, artifact_id FROM acquisition_job WHERE id = %s", (queued["id"],)
    ).fetchone() == ("running", None)
