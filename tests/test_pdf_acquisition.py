"""Page-aware PDF acquisition contracts. External tools and models are faked."""

import io
from pathlib import Path

from PIL import Image
from psycopg.types.json import Jsonb

from universe.acquisition.manual_uploads import (
    ManualAsset,
    acquire_manual_upload,
    create_manual_upload_job,
    list_manual_assets,
)
from universe.acquisition import pdfs
from universe.acquisition.pdfs import PdfPage, text_layer_markdown
from universe.acquisition.source_images import (
    SourceImageAnalysis,
    SourceImageBatchResult,
    input_manifest_hash,
)
from universe.assets import LocalAssetStore
from universe.blocks import split_blocks


def _png_bytes(width: int = 20, height: int = 10) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def _real_png_bytes(width: int = 1000, height: int = 1000) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    return output.getvalue()


def _batch(context, images, analyses):
    return SourceImageBatchResult(
        analyses=analyses,
        unresolved={},
        requested_model="fake/pdf-vision",
        response_model="fake/pdf-vision-resolved",
        provider="Fake Provider",
        usage={"prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25},
        duration_ms=7,
        prompt_ref="pdf-page-analysis/v001",
        prompt_sha="a" * 64,
        input_manifest_hash=input_manifest_hash(context, images),
    )


def test_pdf_text_layer_splits_attached_section_heading_from_its_paragraph():
    markdown = text_layer_markdown(
        "5.     Conclusions\n"
        "This paper compares commercial tools and their capabilities.\n"
        "It then identifies future research directions.\n\n"
        "References\n"
        "Agrawal, R. et al. (1998), Mining process models."
    )

    assert markdown == (
        "### 5. Conclusions\n\n"
        "This paper compares commercial tools and their capabilities. "
        "It then identifies future research directions.\n\n"
        "### References\n\n"
        "Agrawal, R. et al. (1998), Mining process models."
    )


def test_pdf_visual_prompt_requires_visible_support_for_table_structure_claims():
    prompt = (
        Path(__file__).resolve().parents[1]
        / "prompts"
        / "pdf-page-analysis"
        / "v002.md"
    ).read_text(encoding="utf-8")

    assert pdfs.PDF_PROMPT_REF == "pdf-page-analysis/v002"
    assert "verify every named header or category" in prompt
    assert "omit it rather than infer it" in prompt


def test_figure_locator_uses_named_coordinates_and_requires_complete_visual(
    monkeypatch,
):
    captured = {}

    class FakeModelClient:
        def __init__(self, model, **_kwargs):
            self.model = model

        def call_tool(self, messages, tool):
            captured["messages"] = messages
            captured["tool"] = tool
            return (
                {
                    "regions": [
                        {
                            "page_id": "page-8",
                            "bbox": {
                                "left": 230,
                                "top": 85,
                                "right": 685,
                                "bottom": 535,
                            },
                            "description": "A complete connected workflow.",
                            "visible_text": "Start, Phase 1, Phase 2, Phase 3, End",
                        }
                    ]
                },
                {
                    "response_model": "fake/vision-resolved",
                    "provider": "Fake Provider",
                    "total_tokens": 10,
                },
                4,
            )

    monkeypatch.setattr(pdfs, "ModelClient", FakeModelClient)
    image = pdfs.SourceImageInput(
        image_id="page-8",
        alt_text="PDF page 8",
        source_url="/api/source-assets/page-8",
        model_image_url="data:image/png;base64,fixture",
        asset_sha256="a" * 64,
        model_input_sha256="b" * 64,
    )

    result = pdfs.default_pdf_figure_locator("Figure 1. Workflow.", [image])

    assert result.regions[0].bbox == (230, 85, 685, 535)
    bbox_schema = captured["tool"]["function"]["parameters"]["properties"][
        "regions"
    ]["items"]["properties"]["bbox"]
    assert bbox_schema["type"] == "object"
    assert list(bbox_schema["properties"]) == ["left", "top", "right", "bottom"]
    prompt_text = captured["messages"][0]["content"][0]["text"]
    assert "entire connected visual" in prompt_text
    assert "top-left corner" in prompt_text


def test_caption_position_extends_a_partial_figure_box_without_publishing_caption():
    bbox_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml"><body><doc>
      <page width="595.32" height="841.92">
        <flow><block><line xMin="83.16" yMin="462.38" xMax="512.04" yMax="473.48">
          <word xMin="83.16" yMin="462.38" xMax="117.07" yMax="473.48">Figure</word>
          <word xMin="120.48" yMin="462.38" xMax="130.53" yMax="473.48">1:</word>
          <word xMin="133.92" yMin="462.38" xMax="202.56" yMax="473.48">Methodology</word>
        </line></block></flow>
      </page>
    </doc></body></html>"""

    caption_tops = pdfs._figure_caption_tops_from_bbox_xml(bbox_xml, 1)
    completed = pdfs._complete_figure_bbox(
        (268, 89, 730, 399), caption_top_1000=caption_tops[0]
    )

    assert caption_tops == [549]
    assert completed == (268, 89, 730, 539)
    assert pdfs._complete_figure_bbox(
        (268, 89, 730, 560), caption_top_1000=caption_tops[0]
    ) == (268, 89, 730, 560)


def test_firecrawl_markdown_is_canonical_and_page_renders_are_audit_only(db, tmp_path):
    source_id = "source-pdf-firecrawl-structure"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Structured PDF', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/structured-pdf"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\nfixture", "pdf")],
        asset_store=store,
    )
    parse_calls = []

    def parse_document(body, filename, mime_type):
        parse_calls.append((body, filename, mime_type))
        return pdfs.PdfParseResult(
            markdown=(
                "# Process mining\n\n"
                "| Capability | Tool A | Tool B |\n"
                "| --- | --- | --- |\n"
                "| Discovery | Yes | No |\n"
            ),
            image_urls=(),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=parse_document,
        pdf_page_extractor=lambda _body: [
            PdfPage(
                1,
                "Capability Tool A Tool B Discovery Yes No",
                _png_bytes(),
                20,
                10,
            )
        ],
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert parse_calls == [
        (b"%PDF-1.7\nfixture", "lesson.pdf", "application/pdf")
    ]
    assert job["diagnostics"]["extractor"]["document_tool"] == "firecrawl-parse"
    assert job["diagnostics"]["visual_calls"] == []
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    assert "| Capability | Tool A | Tool B |" in markdown
    assert [block.kind for block in split_blocks(markdown)].count("table") == 1
    assert "![PDF page" not in markdown
    assert db.execute(
        "SELECT count(*) FROM source_asset_analysis a"
        " JOIN source_pdf_page p ON p.id = a.pdf_page_id"
        " WHERE p.acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()[0] == 0


def test_firecrawl_parse_result_is_reused_for_the_same_durable_job(db, tmp_path):
    source_id = "source-pdf-firecrawl-idempotent"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Idempotent PDF', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/idempotent-pdf"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\nonce", "pdf")],
        asset_store=store,
    )
    pdf_asset = list_manual_assets(db, queued["id"], include_body=True, asset_store=store)[0]
    parser_calls = []

    def parse_document(body, filename, mime_type):
        parser_calls.append((body, filename, mime_type))
        return pdfs.PdfParseResult(
            markdown="# Parsed once\n",
            image_urls=(),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        )

    def extract_pages(_body):
        return [PdfPage(1, "Parsed once", _png_bytes(), 20, 10)]

    first = pdfs.acquire_pdf_document(
        db,
        job=queued,
        title="Idempotent PDF",
        pdf_asset=pdf_asset,
        asset_store=store,
        document_parser=parse_document,
        page_extractor=extract_pages,
    )
    second = pdfs.acquire_pdf_document(
        db,
        job=queued,
        title="Idempotent PDF",
        pdf_asset=pdf_asset,
        asset_store=store,
        document_parser=lambda *_args: (_ for _ in ()).throw(
            AssertionError("a paid parse must not be repeated")
        ),
        page_extractor=extract_pages,
    )

    assert second.raw_markdown == first.raw_markdown
    assert len(parser_calls) == 1
    assert db.execute(
        "SELECT count(*), sum(attempt_count), max(status)"
        " FROM pdf_document_parse_call WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone() == (1, 1, "succeeded")
    assert second.diagnostics["document_parse"]["reused"] is True


def test_firecrawl_figure_is_localized_as_an_atomic_asset(db, tmp_path):
    source_id = "source-pdf-firecrawl-figure"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'PDF with figure', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/pdf-figure"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\nfigure", "pdf")],
        asset_store=store,
    )
    figure_url = "https://firecrawl.example/figure-1.png"
    figure_body = _png_bytes(400, 240)

    def parse_document(_body, _filename, _mime_type):
        return pdfs.PdfParseResult(
            markdown=(
                "# Method\n\n"
                "![Three-stage process-mining workflow]"
                f"({figure_url})\n\n"
                "The workflow separates discovery, conformance, and extension.\n"
            ),
            image_urls=(figure_url,),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        )

    def download_figure(url):
        assert url == figure_url
        return pdfs.PdfDownloadedImage(
            body=figure_body,
            mime_type="image/png",
            filename="figure-1.png",
            final_url=url,
            width=400,
            height=240,
            sha256=__import__("hashlib").sha256(figure_body).hexdigest(),
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=parse_document,
        pdf_image_downloader=download_figure,
        pdf_page_extractor=lambda _body: [
            PdfPage(1, "Method workflow", _png_bytes(), 20, 10)
        ],
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    assert figure_url not in markdown
    figure = db.execute(
        "SELECT id, kind, mime_type, original_url, metadata"
        " FROM source_asset WHERE acquisition_job_id = %s AND kind = 'pdf_figure'",
        (job["id"],),
    ).fetchone()
    assert figure[1:4] == ("pdf_figure", "image/png", figure_url)
    assert figure[4]["width"] == 400
    assert f"![Three-stage process-mining workflow](/api/source-assets/{figure[0]})" in markdown
    image_blocks = [block for block in split_blocks(markdown) if block.kind == "image"]
    assert len(image_blocks) == 1
    assert image_blocks[0].image_state == "enriched"
    assert "Image description: Three-stage process-mining workflow" in image_blocks[0].text
    assert job["diagnostics"]["document_parse"]["extracted_image_count"] == 1
    assert "![PDF page" not in markdown


def test_firecrawl_parse_upload_uses_structural_formats_and_auto_pdf_mode(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "success": True,
                "data": {
                    "markdown": "| A | B |\n| --- | --- |\n| 1 | 2 |",
                    "images": ["https://cdn.example/figure.png"],
                    "metadata": {"numPages": 3, "totalPages": 3},
                },
            }

    def post(url, *, headers, files, data, timeout):
        calls.append((url, headers, files, data, timeout))
        return Response()

    monkeypatch.setenv("FIRECRAWL_ALLOW_PRIVATE_PDF_UPLOADS", "1")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr(pdfs.httpx, "post", post)

    result = pdfs.parse_pdf_with_firecrawl(
        b"%PDF-1.7\nfixture", "lesson.pdf", "application/pdf"
    )

    assert len(calls) == 1
    url, headers, files, data, timeout = calls[0]
    assert url == "https://api.firecrawl.dev/v2/parse"
    assert headers == {"Authorization": "Bearer test-key"}
    assert files == {
        "file": ("lesson.pdf", b"%PDF-1.7\nfixture", "application/pdf")
    }
    options = __import__("json").loads(data["options"])
    assert options["formats"] == ["markdown", "images"]
    assert options["parsers"] == [{"type": "pdf", "mode": "auto"}]
    assert options["removeBase64Images"] is False
    assert timeout == 315.0
    assert result.image_urls == ("https://cdn.example/figure.png",)
    assert result.diagnostics["estimated_credits"] == 3


def test_failed_firecrawl_figure_requires_attention_without_publishing_a_page(db, tmp_path):
    source_id = "source-pdf-firecrawl-image-failure"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'PDF image failure', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/pdf-image-failure"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\nfail", "pdf")],
        asset_store=store,
    )
    figure_url = "https://firecrawl.example/expired.png"

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=lambda *_args: pdfs.PdfParseResult(
            markdown=(
                "# Content survives\n\n"
                f"![Important diagram]({figure_url})\n\n"
                "| Phase | Meaning |\n| --- | --- |\n| A | Discovery |\n"
            ),
            image_urls=(figure_url,),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        ),
        pdf_image_downloader=lambda _url: (_ for _ in ()).throw(
            pdfs.PdfExtractionError("pdf_image_download_failed", "image_http_error")
        ),
        pdf_page_extractor=lambda _body: [
            PdfPage(1, "Content survives", _png_bytes(), 20, 10)
        ],
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert job["diagnostics"]["visual_incomplete"] is True
    assert job["diagnostics"]["document_parse"]["image_failures"][0][
        "category"
    ] == "image_http_error"
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    assert "| Phase | Meaning |" in markdown
    assert "![PDF page" not in markdown
    assert db.execute(
        "SELECT count(*) FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()[0] == 0


def test_vector_diagram_fallback_publishes_only_the_located_crop(db, tmp_path):
    source_id = "source-pdf-vector-diagram-crop"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Vector diagram PDF', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/vector-diagram"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\nvector", "pdf")],
        asset_store=store,
    )
    locator_calls = []

    def locate_figures(context, images):
        locator_calls.append((context, images))
        assert "| Capability | Tool A | Tool B |" in context
        assert [image.alt_text for image in images] == ["PDF page 1"]
        return pdfs.PdfFigureLocalizationResult(
            regions=(
                pdfs.PdfFigureRegion(
                    page_id=images[0].image_id,
                    bbox=(100, 600, 900, 900),
                    description=(
                        "A workflow connects Discovery to Conformance and Extension."
                    ),
                    visible_text="Discovery → Conformance → Extension",
                ),
            ),
            requested_model="fake/vision",
            response_model="fake/vision-resolved",
            provider="Fake Provider",
            usage={"total_tokens": 20, "cost": 0.001},
            duration_ms=5,
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=lambda *_args: pdfs.PdfParseResult(
            markdown=(
                "# Report\n\n"
                "| Capability | Tool A | Tool B |\n"
                "| --- | --- | --- |\n"
                "| Discovery | Yes | No |\n\n"
                "Figure 1. Three-stage process-mining workflow.\n"
            ),
            image_urls=(),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        ),
        pdf_figure_locator=locate_figures,
        pdf_page_extractor=lambda _body: [
            PdfPage(
                1,
                "Figure 1. Three-stage process-mining workflow.",
                _real_png_bytes(),
                1000,
                1000,
            )
        ],
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert len(locator_calls) == 1
    figure = db.execute(
        "SELECT id, kind, metadata FROM source_asset"
        " WHERE acquisition_job_id = %s AND kind = 'pdf_figure'",
        (job["id"],),
    ).fetchone()
    assert figure[1] == "pdf_figure"
    assert figure[2]["page_number"] == 1
    assert figure[2]["bbox_1000"] == [100, 600, 900, 900]
    assert figure[2]["width"] == 800
    assert figure[2]["height"] == 300
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    assert f"![PDF figure 1](/api/source-assets/{figure[0]})" in markdown
    assert "A workflow connects Discovery to Conformance and Extension." in markdown
    assert "OCR: Discovery → Conformance → Extension" in markdown
    assert "![PDF page" not in markdown
    assert job["diagnostics"]["visual_calls"][0]["usage"]["cost"] == 0.001


def test_vector_figure_localization_is_reused_for_the_same_job(db, tmp_path):
    source_id = "source-pdf-vector-locator-idempotent"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Durable vector locator', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/vector-idempotent"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\nvector-once", "pdf")],
        asset_store=store,
    )
    pdf_asset = list_manual_assets(db, queued["id"], include_body=True, asset_store=store)[0]
    locator_calls = []

    def locator(_context, images):
        locator_calls.append(images)
        return pdfs.PdfFigureLocalizationResult(
            regions=(
                pdfs.PdfFigureRegion(
                    page_id=images[0].image_id,
                    bbox=(100, 600, 900, 900),
                    description="A durable workflow crop.",
                    visible_text="A → B",
                ),
            ),
            requested_model="fake/vision",
            response_model="fake/vision-resolved",
            provider="Fake Provider",
            usage={"total_tokens": 10},
            duration_ms=4,
        )

    parser = lambda *_args: pdfs.PdfParseResult(
        markdown="Figure 1. Durable workflow.\n",
        image_urls=(),
        attempts=1,
        diagnostics={"category": "success", "num_pages": 1},
    )
    page_extractor = lambda _body: [
        PdfPage(1, "Figure 1. Durable workflow.", _real_png_bytes(), 1000, 1000)
    ]
    first = pdfs.acquire_pdf_document(
        db,
        job=queued,
        title="Durable vector locator",
        pdf_asset=pdf_asset,
        asset_store=store,
        document_parser=parser,
        figure_locator=locator,
        page_extractor=page_extractor,
    )
    second = pdfs.acquire_pdf_document(
        db,
        job=queued,
        title="Durable vector locator",
        pdf_asset=pdf_asset,
        asset_store=store,
        document_parser=lambda *_args: (_ for _ in ()).throw(AssertionError()),
        figure_locator=lambda *_args: (_ for _ in ()).throw(
            AssertionError("a paid localization must not be repeated")
        ),
        page_extractor=page_extractor,
    )

    assert len(locator_calls) == 1
    assert second.enriched_markdown == first.enriched_markdown
    assert second.diagnostics["visual_calls"][0]["reused"] is True
    assert db.execute(
        "SELECT count(*), sum(attempt_count), max(status)"
        " FROM pdf_figure_localization_call WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone() == (1, 1, "succeeded")


def obsolete_textual_pdf_builds_page_aware_artifacts_and_queues_cleanup(db, tmp_path):
    source_id = "source-pdf-textual"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Textual PDF', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/textual-pdf"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\nfixture", "pdf")],
        asset_store=store,
    )
    calls = []

    def extract_pages(body):
        assert body == b"%PDF-1.7\nfixture"
        return [
            PdfPage(
                page_number=1,
                text="1. Introduction\n\nFirst wrapped\nparagraph.",
                render_body=_png_bytes(),
                width=20,
                height=10,
            )
        ]

    def analyze_pages(context, images):
        calls.append((context, images))
        image = images[0]
        return _batch(
            context,
            images,
            {
                image.image_id: SourceImageAnalysis(
                    image_id=image.image_id,
                    retain=False,
                    reason_code="no_unique_content",
                    ocr=None,
                    description=None,
                    limitations=None,
                )
            },
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_page_extractor=extract_pages,
        pdf_page_analyzer=analyze_pages,
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert job["diagnostics"]["pipeline_requires_cleanup"] is True
    assert job["diagnostics"]["visual_incomplete"] is False
    assert job["diagnostics"]["page_count"] == 1
    assert len(calls) == 1
    assert calls[0][0].count("First wrapped") == 1
    assert len(calls[0][1]) == 1

    artifacts = db.execute(
        "SELECT id, kind, tool, body, metadata FROM artifact"
        " WHERE snapshot_id = (SELECT snapshot_id FROM artifact WHERE id = %s)"
        " ORDER BY kind, id",
        (job["artifact_id"],),
    ).fetchall()
    raw = next(row for row in artifacts if row[1] == "raw-markdown")
    enriched = next(row for row in artifacts if row[0] == job["artifact_id"])
    assert raw[2] == "pdftotext-page-layer"
    assert "<!-- pdf-page:" in raw[3]
    assert enriched[2] == "pdf-page-association"
    assert "## Page 1" in enriched[3]
    assert "First wrapped paragraph." in enriched[3]
    assert "![" not in enriched[3]
    assert "\f" not in enriched[3]
    assert enriched[4]["raw_artifact_id"] == raw[0]

    page = db.execute(
        "SELECT page_number, text_body, text_layer_status, render_asset_id"
        " FROM source_pdf_page WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()
    assert page[0:3] == (1, "1. Introduction\n\nFirst wrapped\nparagraph.", "usable")
    assert db.execute(
        "SELECT kind, mime_type, metadata->>'page_number' FROM source_asset WHERE id = %s",
        (page[3],),
    ).fetchone() == ("pdf_page", "image/png", "1")
    assert db.execute(
        "SELECT status, result->>'reason_code' FROM source_asset_analysis"
        " WHERE source_asset_id = %s",
        (page[3],),
    ).fetchone() == ("succeeded", "no_unique_content")

    cleanup = db.execute(
        "SELECT status, source_artifact_id FROM source_cleanup_job"
        " WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()
    assert cleanup == ("queued", job["artifact_id"])


def obsolete_mixed_pdf_keeps_page_order_and_attaches_one_diagram_atom(db, tmp_path):
    source_id = "source-pdf-mixed"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Mixed PDF', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/mixed-pdf"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("mixed.pdf", "application/pdf", b"%PDF-1.7\nmixed", "pdf")],
        asset_store=store,
    )
    calls = []

    def extract_pages(_body):
        return [
            PdfPage(1, "1. First section\n\nText on page one.", _png_bytes(20, 10), 20, 10),
            PdfPage(2, "2. Method\n\nThe method has three phases.", _png_bytes(30, 15), 30, 15),
        ]

    def analyze_pages(context, images):
        calls.append((context, images))
        first, second = images
        return _batch(
            context,
            images,
            {
                second.image_id: SourceImageAnalysis(
                    image_id=second.image_id,
                    retain=True,
                    reason_code="information",
                    ocr=None,
                    description=(
                        "A flowchart links Phase 1 to Phase 2 and Phase 3, "
                        "with decision loops returning to earlier phases."
                    ),
                    limitations=None,
                ),
                first.image_id: SourceImageAnalysis(
                    image_id=first.image_id,
                    retain=False,
                    reason_code="no_unique_content",
                    ocr=None,
                    description=None,
                    limitations=None,
                ),
            },
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_page_extractor=extract_pages,
        pdf_page_analyzer=analyze_pages,
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert len(calls) == 1
    context, images = calls[0]
    assert context.index("## Page 1") < context.index("## Page 2")
    assert [image.alt_text for image in images] == ["PDF page 1", "PDF page 2"]
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    assert markdown.index("## Page 1") < markdown.index("## Page 2")
    assert "A flowchart links Phase 1 to Phase 2 and Phase 3" in markdown
    image_blocks = [block for block in split_blocks(markdown) if block.kind == "image"]
    assert len(image_blocks) == 1
    assert image_blocks[0].image_state == "enriched"
    assert "PDF page 2" in image_blocks[0].text
    assert "PDF page 1" not in image_blocks[0].text
    assert db.execute(
        "SELECT count(*) FROM source_asset_analysis a"
        " JOIN source_pdf_page p ON p.id = a.pdf_page_id"
        " WHERE p.acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()[0] == 2


def obsolete_scanned_pdf_page_uses_render_as_primary_ocr_evidence(db, tmp_path):
    source_id = "source-pdf-scanned"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Scanned PDF', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/scanned-pdf"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("scan.pdf", "application/pdf", b"%PDF-1.7\nscan", "pdf")],
        asset_store=store,
    )

    def analyze_pages(context, images):
        assert "(no extractable text layer)" in context
        image = images[0]
        return _batch(
            context,
            images,
            {
                image.image_id: SourceImageAnalysis(
                    image_id=image.image_id,
                    retain=True,
                    reason_code="information",
                    ocr="Discovery → Conformance checking → Extension",
                    description="A scanned diagram presents three process-mining types in sequence.",
                    limitations="The smallest footer is illegible.",
                )
            },
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_page_extractor=lambda _body: [PdfPage(1, "", _png_bytes(), 20, 10)],
        pdf_page_analyzer=analyze_pages,
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert job["diagnostics"]["scanned_pages"] == 1
    assert job["diagnostics"]["visual_incomplete"] is False
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    assert "OCR: Discovery → Conformance checking → Extension" in markdown
    assert "A scanned diagram presents three process-mining types" in markdown
    assert "Image limitations: The smallest footer is illegible." in markdown
    image = next(block for block in split_blocks(markdown) if block.kind == "image")
    assert image.image_state == "enriched"
    assert db.execute(
        "SELECT status FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone() == ("queued",)


def obsolete_pdf_visual_calls_batch_only_for_request_limits_and_refresh_is_idempotent(
    db, tmp_path, monkeypatch
):
    source_id = "source-pdf-batched"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Batched PDF', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/batched-pdf"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("batch.pdf", "application/pdf", b"%PDF-1.7\nbatch", "pdf")],
        asset_store=store,
    )
    monkeypatch.setattr(pdfs, "MAX_MULTIMODAL_REQUEST_BYTES", 100)
    calls = []

    def extract_pages(_body):
        return [
            PdfPage(number, f"Page {number} text.", _png_bytes(), 20, 10)
            for number in range(1, 4)
        ]

    def analyze_pages(context, images):
        calls.append((context, [image.image_id for image in images]))
        return _batch(
            context,
            images,
            {
                image.image_id: SourceImageAnalysis(
                    image_id=image.image_id,
                    retain=False,
                    reason_code="no_unique_content",
                    ocr=None,
                    description=None,
                    limitations=None,
                )
                for image in reversed(images)
            },
        )

    first = acquire_manual_upload(
        db,
        queued["id"],
        pdf_page_extractor=extract_pages,
        pdf_page_analyzer=analyze_pages,
        asset_store=store,
    )
    second = acquire_manual_upload(
        db,
        queued["id"],
        pdf_page_extractor=lambda _body: (_ for _ in ()).throw(AssertionError()),
        pdf_page_analyzer=lambda _context, _images: (_ for _ in ()).throw(AssertionError()),
        asset_store=store,
    )

    assert second["id"] == first["id"]
    assert len(calls) == 2
    assert [len(ids) for _context, ids in calls] == [2, 1]
    assert "Page 3 text." not in calls[0][0]
    assert "Page 1 text." not in calls[1][0]
    assert db.execute(
        "SELECT count(*), sum(attempt_count) FROM pdf_page_analysis_call"
        " WHERE acquisition_job_id = %s",
        (first["id"],),
    ).fetchone() == (2, 2)
    assert db.execute(
        "SELECT count(*) FROM source_asset WHERE acquisition_job_id = %s",
        (first["id"],),
    ).fetchone()[0] == 4


def obsolete_one_missing_page_result_preserves_siblings_and_requires_attention(db, tmp_path):
    source_id = "source-pdf-page-attention"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Incomplete PDF', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/incomplete-pdf"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("incomplete.pdf", "application/pdf", b"%PDF-1.7\nincomplete", "pdf")],
        asset_store=store,
    )

    def analyze_pages(context, images):
        first, second = images
        result = _batch(
            context,
            images,
            {
                first.image_id: SourceImageAnalysis(
                    image_id=first.image_id,
                    retain=True,
                    reason_code="information",
                    ocr=None,
                    description="A complete pedagogical diagram.",
                    limitations=None,
                )
            },
        )
        return SourceImageBatchResult(
            **{
                **result.__dict__,
                "unresolved": {second.image_id: "missing_result"},
            }
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_page_extractor=lambda _body: [
            PdfPage(1, "Page one text.", _png_bytes(20, 10), 20, 10),
            PdfPage(2, "Page two text.", _png_bytes(30, 15), 30, 15),
        ],
        pdf_page_analyzer=analyze_pages,
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert job["diagnostics"]["visual_incomplete"] is True
    assert db.execute(
        "SELECT count(*) FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()[0] == 0
    outcomes = db.execute(
        "SELECT p.page_number, a.status, a.failure_code, a.diagnostics->>'reason'"
        " FROM source_pdf_page p JOIN source_asset_analysis a ON a.pdf_page_id = p.id"
        " WHERE p.acquisition_job_id = %s ORDER BY p.page_number",
        (job["id"],),
    ).fetchall()
    assert outcomes == [
        (1, "succeeded", None, None),
        (2, "failed", "pdf_page_analysis_unresolved", "missing_result"),
    ]
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    image_blocks = [block for block in split_blocks(markdown) if block.kind == "image"]
    assert [block.image_state for block in image_blocks] == ["enriched", "unresolved"]
    assert "A complete pedagogical diagram." in image_blocks[0].text
    assert "PDF page 2" in image_blocks[1].text
