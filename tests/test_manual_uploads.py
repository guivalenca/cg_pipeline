"""Manual source fallback tests. External extractors and models are always faked."""

import psycopg
import pytest
from psycopg.types.json import Jsonb

from universe.assets import LocalAssetStore, StoredAsset
from universe.acquisition.manual_uploads import (
    IMAGE_DESCRIPTION_TOOL,
    ImageDescription,
    ManualAsset,
    OpenRouterImageDescriber,
    acquire_manual_upload,
    create_manual_upload_job,
    list_manual_assets,
    manual_upload_outcome,
    validate_manual_assets,
)
from universe.acquisition.runner import claim_next_job
from universe.acquisition.pdfs import PdfPage, PdfParseResult
from universe.acquisition.source_images import (
    SourceImageAnalysis,
    SourceImageBatchResult,
    input_manifest_hash,
)
from universe.blocks import split_blocks
from universe.model_client import ModelClient
from universe.web.app import _latest_source_state


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


def test_model_client_forces_exactly_one_named_tool_for_multimodal_messages():
    calls = []

    def transport(url, headers, payload, timeout):
        calls.append((url, headers, payload, timeout))
        return {
            "model": "provider/resolved-vision-model",
            "provider": "Example Provider",
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "describe_source_image",
                                    "arguments": '{"description":"A chart.","visible_text":"Revenue"}',
                                }
                            }
                        ]
                    }
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
        }

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe it"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
            ],
        }
    ]
    client = ModelClient(
        "requested/vision-model",
        api_base="https://openrouter.example/v1",
        api_key="test-key",
        transport=transport,
    )

    arguments, usage, duration_ms = client.call_tool(messages, IMAGE_DESCRIPTION_TOOL)

    payload = calls[0][2]
    assert payload["messages"] == messages
    assert payload["tools"] == [IMAGE_DESCRIPTION_TOOL]
    assert payload["tool_choice"] == {
        "type": "function",
        "function": {"name": "describe_source_image"},
    }
    assert payload["parallel_tool_calls"] is False
    assert arguments == {"description": "A chart.", "visible_text": "Revenue"}
    assert usage == {
        "prompt_tokens": 12,
        "completion_tokens": 4,
        "total_tokens": 16,
        "provider": "Example Provider",
        "response_model": "provider/resolved-vision-model",
    }
    assert duration_ms >= 0


def test_openrouter_image_description_sends_the_asset_as_a_data_url():
    payloads = []

    def transport(_url, _headers, payload, _timeout):
        payloads.append(payload)
        return {
            "model": "google/resolved-vision",
            "provider": "Google",
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "describe_source_image",
                                    "arguments": (
                                        '{"description":"Um diagrama de fluxo.",'
                                        '"visible_text":"Início → Resultado"}'
                                    ),
                                }
                            }
                        ]
                    }
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28},
        }

    client = ModelClient(
        "google/requested-vision",
        api_base="https://openrouter.example/v1",
        api_key="test-key",
        transport=transport,
    )
    asset = validate_manual_assets(
        [ManualAsset("flow.png", "image/png", png_bytes(), "image")]
    )[0]

    result = OpenRouterImageDescriber(client=client).describe(asset)

    content = payloads[0]["messages"][0]["content"]
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert result.description == "Um diagrama de fluxo."
    assert result.visible_text == "Início → Resultado"
    assert result.requested_model == "google/requested-vision"
    assert result.response_model == "google/resolved-vision"
    assert result.provider == "Google"
    assert result.usage == {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28}


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


def test_ordered_images_become_attached_described_transcribed_markdown(db, tmp_path):
    source_id = "source-manual-images-markdown"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/clickable"}), "Clickable lesson"),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [
            ManualAsset("screen-2.png", "image/png", png_bytes(), "screenshot"),
            ManualAsset("chart.jpg", "image/jpeg", jpeg_bytes(), "image"),
        ],
        asset_store=store,
    )

    class FakeDescriber:
        def __init__(self):
            self.calls = []

        def describe(self, asset):
            self.calls.append(asset.filename)
            number = len(self.calls)
            return ImageDescription(
                description=f"Visual explanation {number}.",
                visible_text=f"Visible text {number}",
                requested_model="fake/vision",
                response_model="fake/vision-resolved",
                provider="Fake Provider",
                usage={"prompt_tokens": 10 * number, "completion_tokens": number, "total_tokens": 11 * number},
                duration_ms=number,
            )

    describer = FakeDescriber()
    job = acquire_manual_upload(
        db, queued["id"], image_describer=describer, asset_store=store
    )

    assert job["status"] == "succeeded"
    assert describer.calls == ["screen-2.png", "chart.jpg"]
    assets = list_manual_assets(db, job["id"])
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    first_image = f"![Screenshot 1 — screen-2.png](/api/source-assets/{assets[0]['id']})"
    second_image = f"![Image 2 — chart.jpg](/api/source-assets/{assets[1]['id']})"
    assert markdown.index(first_image) < markdown.index(second_image)
    assert "Image summary: Visual explanation 1." in markdown
    assert "Visible text: Visible text 1" in markdown
    image_blocks = [block for block in split_blocks(markdown) if block.kind == "image"]
    assert len(image_blocks) == 2
    assert [block.image_state for block in image_blocks] == ["enriched", "enriched"]
    assert "Image summary: Visual explanation 1." in image_blocks[0].text
    assert "Visible text: Visible text 1" in image_blocks[0].text
    assert job["diagnostics"]["model"] == "fake/vision"
    assert job["diagnostics"]["prompt_version"] == "manual-source-image-description.v1"
    assert job["diagnostics"]["provider"] == "Fake Provider"
    assert job["diagnostics"]["usage"] == {
        "prompt_tokens": 30,
        "completion_tokens": 3,
        "total_tokens": 33,
    }
    assert [item["kind"] for item in job["diagnostics"]["images"]] == [
        "screenshot",
        "image",
    ]
    analyses = db.execute(
        "SELECT sa.ordinal, a.purpose, a.status, a.prompt_version, a.result"
        " FROM source_asset_analysis a"
        " JOIN source_asset sa ON sa.id = a.source_asset_id"
        " WHERE sa.acquisition_job_id = %s ORDER BY sa.ordinal",
        (job["id"],),
    ).fetchall()
    assert analyses == [
        (
            1,
            "manual_image_description",
            "succeeded",
            "manual-source-image-description.v1",
            {
                "description": "Visual explanation 1.",
                "visible_text": "Visible text 1",
            },
        ),
        (
            2,
            "manual_image_description",
            "succeeded",
            "manual-source-image-description.v1",
            {
                "description": "Visual explanation 2.",
                "visible_text": "Visible text 2",
            },
        ),
    ]


def test_visual_failure_preserves_the_manual_image_as_unresolved(db, tmp_path):
    source_id = "source-manual-image-unresolved"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, %s, 'article')",
        (
            source_id,
            Jsonb({"canonical_url": "https://example.com/unresolved-image"}),
            "Unresolved visual source",
        ),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("page.png", "image/png", png_bytes(), "screenshot")],
        asset_store=store,
    )

    class FailingDescriber:
        def describe(self, _asset):
            raise RuntimeError("provider response must not leak into diagnostics")

    job = acquire_manual_upload(
        db,
        queued["id"],
        image_describer=FailingDescriber(),
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    image_blocks = [block for block in split_blocks(markdown) if block.kind == "image"]
    assert len(image_blocks) == 1
    assert image_blocks[0].image_state == "unresolved"
    assert "Image analysis: unresolved." in image_blocks[0].text
    assert "/api/source-assets/" in image_blocks[0].text
    assert job["diagnostics"]["images"][0] == {
        "asset_id": list_manual_assets(db, job["id"])[0]["id"],
        "ordinal": 1,
        "kind": "screenshot",
        "status": "failed",
        "failure_code": "manual_image_description_failed",
        "diagnostics": {
            "category": "image_description_failed",
            "exception": "RuntimeError",
        },
    }
    assert "provider response" not in str(job["diagnostics"])
    state = _latest_source_state(db, [source_id])[source_id]
    assert state["pipeline"]["status"] == "attention"
    assert state["has_markdown"] is True
    assert state["markdown"]["artifact_id"] == job["artifact_id"]
    assert "evidência manual" in state["job"]["error"].lower()
    assert db.execute(
        "SELECT status, failure_code, result, diagnostics"
        " FROM source_asset_analysis WHERE source_asset_id = %s",
        (list_manual_assets(db, job["id"])[0]["id"],),
    ).fetchone() == (
        "failed",
        "manual_image_description_failed",
        {},
        {
            "ordinal": 1,
            "kind": "screenshot",
            "category": "image_description_failed",
            "exception": "RuntimeError",
        },
    )


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
