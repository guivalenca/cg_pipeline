"""Page-aware PDF acquisition contracts. External tools and models are faked."""

import io
import re
from pathlib import Path

from PIL import Image, ImageDraw
from psycopg.types.json import Jsonb

from universe.acquisition.manual_uploads import (
    ManualAsset,
    acquire_manual_upload,
    create_manual_upload_job,
    list_manual_assets,
)
from universe.acquisition import pdfs
from universe.acquisition import pdf_figure_recovery as pdf_figures
from universe.acquisition.pdfs import PdfPage
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


def _figure_page_png_bytes() -> bytes:
    page = Image.new("RGB", (1000, 1000), "white")
    draw = ImageDraw.Draw(page)
    draw.rectangle((250, 620, 750, 880), outline="black", width=4)
    draw.line((500, 880, 500, 924), fill="black", width=4)
    draw.rectangle((130, 960, 870, 967), fill="black")
    output = io.BytesIO()
    page.save(output, format="PNG")
    return output.getvalue()


def _black_page_png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (1000, 1000), "black").save(output, format="PNG")
    return output.getvalue()


def _empty_figure_result(_context, _images):
    return pdfs.PdfFigureLocalizationResult(
        regions=(),
        requested_model="fake/vision",
        response_model="fake/vision-resolved",
        provider="Fake Provider",
        usage={"total_tokens": 1},
        duration_ms=1,
    )


def test_pdf_figure_prompt_requires_exhaustive_page_accounting_and_anchors():
    prompt = (
        Path(__file__).resolve().parents[1]
        / "prompts"
        / "pdf-figure-localization"
        / "v004.md"
    ).read_text(encoding="utf-8")

    assert pdfs.PDF_FIGURE_PROMPT_REF == "pdf-figure-localization/v004"
    assert "every supplied page" in prompt
    assert "zero, one, or multiple" in prompt
    assert "anchor_id" in prompt


def test_figure_batches_cap_multi_page_localization_for_coordinate_reliability():
    pages = [
        {"id": f"page-{number}", "text_body": f"Page {number}"}
        for number in range(1, 18)
    ]
    bodies = {str(page["id"]): b"render" for page in pages}

    assert [
        len(batch) for batch in pdf_figures._page_batches(pages, bodies)
    ] == [8, 8, 1]


def test_region_page_guard_rejects_strong_cross_page_ocr_evidence():
    pages = [
        {
            "id": "page-1",
            "text_body": "General methodology discussion without diagram labels.",
            "text_layer_status": "usable",
        },
        {
            "id": "page-2",
            "text_body": (
                "Start phase discovery decision commercial software criteria output end"
            ),
            "text_layer_status": "usable",
        },
    ]
    region = pdfs.PdfFigureRegion(
        page_id="page-1",
        bbox=(100, 100, 900, 500),
        description="A workflow.",
        visible_text=(
            "Start phase discovery decision commercial software criteria output end"
        ),
    )

    mismatch = pdf_figures._region_page_mismatch(region, pages)

    assert mismatch["reason"] == "visible_text_matches_another_page"
    assert mismatch["best_page_id"] == "page-2"


def test_multi_region_geometry_assigns_ordered_whitespace_between_prose_lines():
    first = pdfs.PdfFigureRegion(
        page_id="page-1",
        bbox=(350, 110, 650, 190),
        description="A stacked diagram.",
        visible_text="p1 t1 p2",
        anchor_id="anchor-1",
    )
    second = pdfs.PdfFigureRegion(
        page_id="page-1",
        bbox=(350, 250, 650, 320),
        description="A second stacked diagram.",
        visible_text="p3 t2 p4",
        anchor_id="anchor-2",
    )
    page = {
        "text_lines_1000": (
            ("The first paragraph introduces the first diagram clearly.", 100, 100, 850, 120),
            ("p1 t1 p2", 400, 160, 600, 175),
            ("The middle paragraph explains the first result and introduces another.", 100, 240, 850, 260),
            ("p3 t2 p4", 400, 300, 600, 315),
            ("The final paragraph explains the second result in detail.", 100, 380, 850, 400),
        )
    }

    assigned = pdf_figures._multi_region_text_gap_bboxes(
        [first, second], page=page
    )

    assert assigned == {
        first.bbox: (350, 126, 650, 234),
        second.bbox: (350, 266, 650, 374),
    }


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
                            "anchor_id": "md-block-0002-abc123",
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

    monkeypatch.setattr(pdf_figures, "ModelClient", FakeModelClient)
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
    assert result.regions[0].anchor_id == "md-block-0002-abc123"
    bbox_schema = captured["tool"]["function"]["parameters"]["properties"][
        "regions"
    ]["items"]["properties"]["bbox"]
    assert bbox_schema["type"] == "object"
    assert list(bbox_schema["properties"]) == ["left", "top", "right", "bottom"]
    prompt_text = captured["messages"][0]["content"][0]["text"]
    assert "complete connected" in prompt_text
    assert "structure with a small margin" in prompt_text
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
    text_lines = pdfs._text_lines_from_bbox_xml(bbox_xml, 1)
    completed = pdf_figures._complete_figure_bbox(
        (268, 89, 730, 399), caption_top_1000=caption_tops[0]
    )

    assert caption_tops == [549]
    assert text_lines == [(("Figure 1: Methodology", 140, 549, 860, 562),)]
    assert completed == (268, 89, 730, 539)
    assert pdf_figures._complete_figure_bbox(
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
    locator_calls = []

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

    def locate_figures(context, images):
        locator_calls.append((context, images))
        return _empty_figure_result(context, images)

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=parse_document,
        pdf_figure_locator=locate_figures,
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
    assert len(locator_calls) == 1
    assert len(job["diagnostics"]["visual_calls"]) == 1
    assert job["diagnostics"]["visual_calls"][0]["region_count"] == 0
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


def test_disabled_all_page_localization_is_an_explicit_attention_outcome(
    db, tmp_path, monkeypatch
):
    monkeypatch.delenv("OPENROUTER_ALLOW_PRIVATE_PDF_PAGE_UPLOADS", raising=False)
    source_id = "source-pdf-localization-disabled"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Disabled PDF localization', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/disabled-vision"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\noff", "pdf")],
        asset_store=store,
    )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=lambda *_args: pdfs.PdfParseResult(
            markdown="# Lesson\n\nUseful text.\n",
            image_urls=(),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        ),
        pdf_page_extractor=lambda _body: [
            PdfPage(1, "Useful text.", _png_bytes(), 20, 10)
        ],
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert job["diagnostics"]["visual_incomplete"] is True
    assert job["diagnostics"]["document_parse"]["image_failures"] == [
        {
            "category": "figure_localization_disabled",
            "failure_code": "pdf_figure_localization_disabled",
            "page_count": 1,
        }
    ]
    assert db.execute(
        "SELECT count(*) FROM source_cleanup_job WHERE acquisition_job_id = %s",
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
        figure_locator=_empty_figure_result,
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
        figure_locator=lambda *_args: (_ for _ in ()).throw(
            AssertionError("a paid localization must not be repeated")
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
    assert second.diagnostics["visual_calls"][0]["reused"] is True


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
    locator_calls = []

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

    def locate_remaining_figures(context, images):
        locator_calls.append((context, images))
        anchor_id = re.search(
            r"## anchor_id: (md-block-[^\n]+)\nkind: paragraph\n\n"
            r"The workflow separates discovery, conformance, and extension\.",
            context,
        ).group(1)
        return pdfs.PdfFigureLocalizationResult(
            regions=(
                pdfs.PdfFigureRegion(
                    page_id=images[0].image_id,
                    bbox=(100, 600, 900, 900),
                    description="A second informative diagram missed by Firecrawl.",
                    visible_text="A → B",
                    anchor_id=anchor_id,
                ),
            ),
            requested_model="fake/vision",
            response_model="fake/vision-resolved",
            provider="Fake Provider",
            usage={"total_tokens": 5},
            duration_ms=2,
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=parse_document,
        pdf_image_downloader=download_figure,
        pdf_figure_locator=locate_remaining_figures,
        pdf_page_extractor=lambda _body: [
            PdfPage(1, "Method workflow", _real_png_bytes(), 1000, 1000)
        ],
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert len(locator_calls) == 1
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    assert figure_url not in markdown
    figure = db.execute(
        "SELECT id, kind, mime_type, original_url, metadata"
        " FROM source_asset WHERE acquisition_job_id = %s AND kind = 'pdf_figure'"
        " AND original_url IS NOT NULL",
        (job["id"],),
    ).fetchone()
    assert figure[1:4] == ("pdf_figure", "image/png", figure_url)
    assert figure[4]["width"] == 400
    assert f"![Three-stage process-mining workflow](/api/source-assets/{figure[0]})" in markdown
    image_blocks = [block for block in split_blocks(markdown) if block.kind == "image"]
    assert len(image_blocks) == 2
    assert image_blocks[0].image_state == "enriched"
    assert "Image description: Three-stage process-mining workflow" in image_blocks[0].text
    assert job["diagnostics"]["document_parse"]["extracted_image_count"] == 2
    recovered_id = db.execute(
        "SELECT id FROM source_asset WHERE acquisition_job_id = %s"
        " AND kind = 'pdf_figure' AND original_url IS NULL",
        (job["id"],),
    ).fetchone()[0]
    assert markdown.index(f"![PDF figure 2](/api/source-assets/{recovered_id})") < (
        markdown.index("The workflow separates discovery, conformance, and extension.")
    )
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

    calls.clear()
    pdfs.parse_pdf_with_firecrawl(
        b"%PDF-1.7\nordered", "ordered.pdf", "application/pdf", mode="ocr"
    )
    ordered_options = __import__("json").loads(calls[0][3]["options"])
    assert ordered_options["parsers"] == [{"type": "pdf", "mode": "ocr"}]


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
        pdf_figure_locator=_empty_figure_result,
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
        anchor_id = re.search(
            r"## anchor_id: (md-block-[^\n]+)\nkind: paragraph\n\n"
            r"Figure 1\. Three-stage process-mining workflow\.",
            context,
        ).group(1)
        return pdfs.PdfFigureLocalizationResult(
            regions=(
                pdfs.PdfFigureRegion(
                    page_id=images[0].image_id,
                    bbox=(100, 600, 900, 900),
                    description=(
                        "A workflow connects Discovery to Conformance and Extension."
                    ),
                    visible_text="Discovery → Conformance → Extension",
                    anchor_id=anchor_id,
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
                _figure_page_png_bytes(),
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
    assert figure[2]["bbox_1000"] == [100, 600, 900, 928]
    assert figure[2]["model_bbox_1000"] == [100, 600, 900, 900]
    assert figure[2]["bbox_adjustment"] == "pixel_gutter_adaptive"
    assert figure[2]["width"] == 800
    assert figure[2]["height"] == 328
    assert figure[2]["placement"] == "before_markdown_block"
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    assert f"![PDF figure 1](/api/source-assets/{figure[0]})" in markdown
    assert "A workflow connects Discovery to Conformance and Extension." in markdown
    assert "OCR: Discovery → Conformance → Extension" in markdown
    assert "![PDF page" not in markdown
    assert "## Extracted figures" not in markdown
    assert markdown.index(f"![PDF figure 1](/api/source-assets/{figure[0]})") < (
        markdown.index("Figure 1. Three-stage process-mining workflow.")
    )
    assert job["diagnostics"]["visual_calls"][0]["usage"]["cost"] == 0.001
    assert db.execute(
        "SELECT status, source_asset_id FROM pdf_figure_region_outcome"
        " WHERE page_id = (SELECT id FROM source_pdf_page"
        " WHERE acquisition_job_id = %s)",
        (job["id"],),
    ).fetchone() == ("placed", figure[0])


def test_figure_without_pixel_gutter_is_an_explicit_attention_outcome(db, tmp_path):
    source_id = "source-pdf-no-figure-gutter"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'No figure gutter', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/no-gutter"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\nblack", "pdf")],
        asset_store=store,
    )

    def locate_figures(_context, images):
        return pdfs.PdfFigureLocalizationResult(
            regions=(
                pdfs.PdfFigureRegion(
                    page_id=images[0].image_id,
                    bbox=(300, 300, 700, 700),
                    description="A figure indistinguishable from surrounding content.",
                    visible_text="Dense content",
                ),
            ),
            requested_model="fake/vision",
            response_model="fake/vision-resolved",
            provider="Fake Provider",
            usage={"total_tokens": 1},
            duration_ms=1,
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=lambda *_args: pdfs.PdfParseResult(
            markdown="# Dense lesson\n\nDense content.\n",
            image_urls=(),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        ),
        pdf_figure_locator=locate_figures,
        pdf_page_extractor=lambda _body: [
            PdfPage(1, "Dense content", _black_page_png_bytes(), 1000, 1000)
        ],
        asset_store=store,
    )

    assert job["status"] == "succeeded"
    assert job["diagnostics"]["visual_incomplete"] is True
    assert job["diagnostics"]["document_parse"]["image_failures"] == [
        {
            "batch_ordinal": 1,
            "region_ordinal": 1,
            "page_id": db.execute(
                "SELECT id FROM source_pdf_page WHERE acquisition_job_id = %s",
                (job["id"],),
            ).fetchone()[0],
            "category": "figure_crop_failed",
            "failure_code": "pdf_figure_crop_failed",
            "exception": "FigureCropUnresolved",
        }
    ]
    assert db.execute(
        "SELECT status, diagnostics FROM pdf_figure_region_outcome"
        " WHERE page_id = (SELECT id FROM source_pdf_page"
        " WHERE acquisition_job_id = %s)",
        (job["id"],),
    ).fetchone() == ("failed", {"exception": "FigureCropUnresolved"})
    assert db.execute(
        "SELECT count(*) FROM source_asset"
        " WHERE acquisition_job_id = %s AND kind = 'pdf_figure'",
        (job["id"],),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()[0] == 0


def test_multiple_regions_are_sorted_and_unmatched_regions_use_explicit_fallback(
    db, tmp_path
):
    source_id = "source-pdf-multiple-figure-regions"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Multiple PDF figures', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.test/multiple-figures"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "assets")
    queued = create_manual_upload_job(
        db,
        source_id,
        [ManualAsset("lesson.pdf", "application/pdf", b"%PDF-1.7\nmulti", "pdf")],
        asset_store=store,
    )

    def locator(context, images):
        anchor_id = re.search(
            r"## anchor_id: (md-block-[^\n]+)\nkind: paragraph\n\n"
            r"Diagram A is explained here\.",
            context,
        ).group(1)
        return pdfs.PdfFigureLocalizationResult(
            regions=(
                pdfs.PdfFigureRegion(
                    page_id=images[0].image_id,
                    bbox=(100, 650, 700, 900),
                    description="An informative diagram without a text anchor.",
                    visible_text="C → D",
                ),
                pdfs.PdfFigureRegion(
                    page_id=images[0].image_id,
                    bbox=(100, 100, 500, 300),
                    description="The first informative diagram on the page.",
                    visible_text="A → B",
                    anchor_id=anchor_id,
                ),
            ),
            requested_model="fake/vision",
            response_model="fake/vision-resolved",
            provider="Fake Provider",
            usage={"total_tokens": 8},
            duration_ms=3,
        )

    job = acquire_manual_upload(
        db,
        queued["id"],
        pdf_document_parser=lambda *_args: pdfs.PdfParseResult(
            markdown="# Lesson\n\nDiagram A is explained here.\n\nClosing.\n",
            image_urls=(),
            attempts=1,
            diagnostics={"category": "success", "num_pages": 1},
        ),
        pdf_figure_locator=locator,
        pdf_page_extractor=lambda _body: [
            PdfPage(1, "Diagram A is explained here.", _real_png_bytes(), 1000, 1000)
        ],
        asset_store=store,
    )

    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (job["artifact_id"],)
    ).fetchone()[0]
    assert markdown.index("![PDF figure 1]") < markdown.index(
        "Diagram A is explained here."
    )
    assert "## Extracted figures (unanchored)" in markdown
    assert markdown.index("## Extracted figures (unanchored)") < markdown.index(
        "![PDF figure 2]"
    )
    assert db.execute(
        "SELECT array_agg(status ORDER BY region_ordinal)"
        " FROM pdf_figure_region_outcome"
        " WHERE localization_call_id = (SELECT id"
        " FROM pdf_figure_localization_call WHERE acquisition_job_id = %s)",
        (job["id"],),
    ).fetchone()[0] == ["placed", "unanchored"]


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
        anchor_id = re.search(
            r"## anchor_id: (md-block-[^\n]+)\nkind: paragraph\n\n"
            r"Figure 1\. Durable workflow\.",
            _context,
        ).group(1)
        return pdfs.PdfFigureLocalizationResult(
            regions=(
                pdfs.PdfFigureRegion(
                    page_id=images[0].image_id,
                    bbox=(100, 600, 900, 900),
                    description="A durable workflow crop.",
                    visible_text="A → B",
                    anchor_id=anchor_id,
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
