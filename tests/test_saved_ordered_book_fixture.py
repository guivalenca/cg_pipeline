"""Saved real-book acceptance without Browserbase, Firecrawl, or model traffic."""

import io
import json
import os
from pathlib import Path

import pikepdf
import pytest
from PIL import Image
from psycopg.types.json import Jsonb

from universe.acquisition import source_cleanup_jobs
from universe.acquisition.book_acquisition import BookCaptureSummary, CapturedBookPage
from universe.acquisition.pdfs import PdfFigureLocalizationResult, PdfParseResult
from universe.acquisition.runner import enqueue_source, process_next_job
from universe.assets import LocalAssetStore
from universe.harness import PROMPTS_DIR, load_tool
from universe.model_client import ModelClient
from universe.web.app import _latest_source_state


FIXTURE = os.getenv("SAVED_BROWSERBASE_BOOK_FIXTURE", "").strip()
pytestmark = pytest.mark.skipif(
    not FIXTURE,
    reason="set SAVED_BROWSERBASE_BOOK_FIXTURE to an existing local capture",
)


def _reader_text(path: Path) -> str:
    body = path.read_text(encoding="utf-8")
    marker = "### Reader text\n\n"
    assert marker in body
    return body.split(marker, 1)[1].strip()


def _assert_lossless_pages(pdf_body: bytes, originals: list[bytes]) -> None:
    with pikepdf.open(io.BytesIO(pdf_body)) as document:
        assert len(document.pages) == len(originals)
        for page, original in zip(document.pages, originals, strict=True):
            xobjects = page.Resources.get("/XObject", {})
            image_objects = [
                value for value in xobjects.values() if value.get("/Subtype") == "/Image"
            ]
            assert len(image_objects) == 1
            embedded = pikepdf.PdfImage(image_objects[0]).as_pil_image().convert("RGB")
            with Image.open(io.BytesIO(original)) as source:
                expected = source.convert("RGB")
                assert embedded.size == expected.size
                assert embedded.tobytes() == expected.tobytes()


def _tool_response(name: str, arguments: dict) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": name,
                                "arguments": json.dumps(arguments),
                            }
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        "provider": "local-fixture",
    }


def _client(arguments: dict, stage: str, tool: str) -> ModelClient:
    def transport(_url, _headers, payload, _timeout):
        name = payload["tools"][0]["function"]["name"]
        return _tool_response(name, arguments)

    return ModelClient(
        "local/fixture",
        api_base="https://example.invalid/v1",
        transport=transport,
        extra=load_tool(str(PROMPTS_DIR / stage / tool)),
    )


def test_saved_real_book_pages_form_one_lossless_ordered_document(db, tmp_path):
    fixture = Path(FIXTURE).resolve()
    manifest = json.loads((fixture / "page_manifest.json").read_text())
    assert [item["requested_label"] for item in manifest["pages"]] == [
        str(page) for page in range(198, 206)
    ]
    source_id = "source-saved-ordered-book-fixture"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Programação linear inteira', 'book')",
        (
            source_id,
            Jsonb(
                {
                    "kind": "book",
                    "resource_code": "9788522128303",
                    "scope": {"kind": "pages", "value": "198-205"},
                }
            ),
        ),
    )
    db.commit()
    original_images = [
        (fixture / item["image"]).read_bytes() for item in manifest["pages"]
    ]
    events = []

    class SavedCaptureAdapter:
        def capture(self, request, *, completed_pages, persist_page):
            assert completed_pages == ()
            for item, image in zip(manifest["pages"], original_images, strict=True):
                exact_text = _reader_text(fixture / item["markdown"])
                assert len(exact_text.split()) >= item["reader_word_count"]
                persist_page(
                    CapturedBookPage(
                        ordinal=item["page_index"],
                        printed_page_label=item["requested_label"],
                        reader_page_id=item["reader_pageid"],
                        image_body=image,
                        mime_type="image/png",
                        exact_text=exact_text,
                    )
                )
            events.append("browserbase_released")
            return BookCaptureSummary(
                final_url=(
                    "https://integrada.minhabiblioteca.com.br/reader/books/"
                    "9788522128303/pageid/217"
                ),
                original_library_url="https://philos.sophia.com.br/terminal/9418",
                capture_version="saved-browserbase-fixture-v1",
                diagnostics={"warnings": []},
            )

    def parse(pdf_body, _filename, _mime_type):
        assert events == ["browserbase_released"]
        _assert_lossless_pages(pdf_body, original_images)
        events.append("firecrawl_parse")
        return PdfParseResult(
            markdown=(
                "## Programação linear inteira\n\n"
                "Um modelo pode impor condições de integralidade.\n\n"
                "| Variável | Condição |\n| --- | --- |\n| $X_1$ | inteira |\n"
            ),
            image_urls=(),
            attempts=1,
            diagnostics={"estimated_credits": 8},
        )

    localized = []

    def locate(_context, images):
        assert events == ["browserbase_released", "firecrawl_parse"]
        localized.extend(images)
        events.append("gemini_localization")
        return PdfFigureLocalizationResult(
            regions=(),
            requested_model="local/fixture",
            response_model="local/fixture",
            provider="local-fixture",
            usage={},
            duration_ms=0,
        )

    store = LocalAssetStore(tmp_path / "saved-book-assets")
    queued = enqueue_source(db, source_id)
    completed = process_next_job(
        db,
        job_id=queued["id"],
        asset_store=store,
        book_adapter=SavedCaptureAdapter(),
        book_document_parser=parse,
        book_figure_locator=locate,
    )

    assert completed["status"] == "succeeded", (
        completed["failure_code"],
        completed["diagnostics"],
        events,
    )
    assert events == [
        "browserbase_released",
        "firecrawl_parse",
        "gemini_localization",
    ]
    assert completed["diagnostics"]["page_count"] == 8
    assert completed["diagnostics"]["exact_text_pages"] == 8
    assert completed["diagnostics"]["extractor"]["document_mode"] == "ocr"
    assert len(localized) == 8
    assert all(
        image.source_url.startswith("/api/source-assets/asset-book-")
        for image in localized
    )
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (completed["artifact_id"],)
    ).fetchone()[0]
    assert "| Variável | Condição |" in markdown
    assert "![PDF page" not in markdown
    assert "asset-book-" not in markdown
    cleanup_job_id, cleanup_status = db.execute(
        "SELECT id, status FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()
    assert cleanup_status == "queued"

    cleanup = source_cleanup_jobs.process_next_source_cleanup(
        db,
        job_id=cleanup_job_id,
        cuts_client=_client({"cuts": []}, "passage-cuts", "tool-v001.json"),
        triage_client=_client(
            {"verdict": "keep"}, "passage-triage", "tool-v003.json"
        ),
        atomic_triage_client=_client(
            {"verdict": "keep"},
            "passage-triage",
            "tool-v003-atomic.json",
        ),
        refine_client=_client(
            {"drop_elements": []}, "passage-refine", "tool-v002.json"
        ),
    )
    assert cleanup["status"] == "succeeded", cleanup
    canonical = db.execute(
        "SELECT body, tool FROM artifact WHERE id = %s",
        (cleanup["canonical_artifact_id"],),
    ).fetchone()
    assert canonical[1] == "passage-cleanup"
    assert "| Variável | Condição |" in canonical[0]
    state = _latest_source_state(db, [source_id])[source_id]
    assert state["pipeline"]["status"] == "ready"
    assert state["markdown"]["artifact_id"] == cleanup["canonical_artifact_id"]
