"""Public contracts for completing a scope-less authenticated book source."""

from __future__ import annotations

import io
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from adalove_workbook import activity, write_adalove_workbook
from universe.acquisition.book_acquisition import (
    BookCaptureSummary,
    CapturedBookPage,
)
from universe.acquisition.pdfs import PdfFigureLocalizationResult, PdfParseResult
from universe.acquisition.runner import process_next_job
from universe.assets import LocalAssetStore
from universe.web.app import create_app


INSTITUTION_ID = "book-scope-test"
RESOURCE_CODE = "9780000000001"
SAVED_SCOPE = "37-38"


def _app(database_url: str):
    return create_app(
        lambda: psycopg.connect(database_url),
        companion_namespace_provider=lambda: {
            "schema_version": "companion_graph_namespace.v1",
            "institutions": [
                {"slug": INSTITUTION_ID, "name": "Book Scope Test"},
            ],
            "graph_ids": [],
        },
    )


def _scope_less_book_workbook(path: Path) -> Path:
    lesson = activity(title="Authenticated book lesson")
    source = activity(
        week=1,
        order=2,
        kind="Self-study",
        title="Authenticated textbook",
        parent_uuid=lesson["Activity UUID"],
        parent_title=lesson["Title"],
        subject=None,
        description="Read the assigned pages.",
        url="https://philos.sophia.com.br/terminal/9418",
        resource_code=RESOURCE_CODE,
    )
    return write_adalove_workbook(
        path,
        [lesson, source],
        project="Book scope contract",
    )


def _upload(client: TestClient, workbook_path: Path, syllabus_name: str) -> dict:
    with workbook_path.open("rb") as workbook:
        response = client.post(
            "/api/syllabi/upload",
            data={"name": syllabus_name, "institution_id": INSTITUTION_ID},
            files={
                "file": (
                    workbook_path.name,
                    workbook,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    assert response.status_code == 201, response.text
    return response.json()


def _save_page_scope(
    client: TestClient,
    workbook_path: Path,
    syllabus_name: str,
) -> tuple[dict, dict, dict]:
    uploaded = _upload(client, workbook_path, syllabus_name)
    syllabus_id = uploaded["syllabus_id"]
    before_response = client.get(f"/api/syllabi/{syllabus_id}")
    assert before_response.status_code == 200
    before = before_response.json()
    source = before["lessons"][0]["sources"][0]
    assert source["media_type"] == "book"
    assert source["resource_code"] == RESOURCE_CODE
    assert source["scope"] is None
    assert source["source_id"] is None

    source["scope_kind"] = "pages"
    source["scope_value"] = SAVED_SCOPE
    curated_response = client.post(
        f"/api/syllabi/{syllabus_id}/curate",
        json={
            "base_version_id": before["version"]["id"],
            "note": "Define the assigned textbook pages.",
            "lessons": before["lessons"],
        },
    )
    assert curated_response.status_code == 201, curated_response.text

    reloaded_response = client.get(f"/api/syllabi/{syllabus_id}")
    assert reloaded_response.status_code == 200
    return before, curated_response.json(), reloaded_response.json()


def _png(label: str) -> bytes:
    output = io.BytesIO()
    image = Image.new("RGB", (320, 180), "white")
    ImageDraw.Draw(image).text((18, 18), label, fill="black")
    image.save(output, format="PNG")
    return output.getvalue()


def _parse_document(_body: bytes, _filename: str, _mime_type: str) -> PdfParseResult:
    return PdfParseResult(
        markdown="## Saved scope\n\nThe requested pages were captured.",
        image_urls=(),
        attempts=1,
        diagnostics={"estimated_credits": 1},
    )


def _locate_no_figures(_context, _images) -> PdfFigureLocalizationResult:
    return PdfFigureLocalizationResult(
        regions=(),
        requested_model="fake/vision",
        response_model="fake/vision-resolved",
        provider="Fake Provider",
        usage={"total_tokens": 1},
        duration_ms=1,
    )


def test_operator_curation_adds_missing_book_scope_as_a_new_audited_version(
    test_database_url,
    tmp_path,
):
    workbook_path = _scope_less_book_workbook(tmp_path / "scope-less-book.xlsx")

    with TestClient(_app(test_database_url)) as client:
        before, curated, reloaded = _save_page_scope(
            client,
            workbook_path,
            "Scope-less book curation",
        )
        historical_response = client.get(
            f"/api/syllabi/{curated['syllabus_id']}",
            params={"version_id": before["version"]["id"]},
        )

    assert curated["seq"] == 2
    assert curated["new_source_count"] == 1
    assert reloaded["version"]["id"] == curated["version_id"]
    saved_source = reloaded["lessons"][0]["sources"][0]
    assert saved_source["scope"] == {"kind": "pages", "value": SAVED_SCOPE}
    assert saved_source["source_id"]
    assert historical_response.status_code == 200
    historical_source = historical_response.json()["lessons"][0]["sources"][0]
    assert historical_source["scope"] is None
    assert historical_source["source_id"] is None

    with psycopg.connect(test_database_url) as conn:
        event = conn.execute(
            "SELECT action, subject, note FROM curation_event"
            " WHERE subject->>'version_id' = %s",
            (curated["version_id"],),
        ).fetchone()

    assert event[0] == "syllabus_curated"
    assert event[2] == "Define the assigned textbook pages."
    assert event[1]["syllabus_id"] == curated["syllabus_id"]
    assert event[1]["base_version_id"] == before["version"]["id"]
    scope_change = event[1]["diff"]["changed"][0]
    assert scope_change["before"]["scope_kind"] is None
    assert scope_change["before"]["scope_value"] is None
    assert scope_change["after"]["scope_kind"] == "pages"
    assert scope_change["after"]["scope_value"] == SAVED_SCOPE


def test_saved_book_page_scope_reaches_the_authenticated_capture_adapter(
    test_database_url,
    tmp_path,
):
    workbook_path = _scope_less_book_workbook(tmp_path / "acquired-book.xlsx")
    captured_requests = []

    class RecordingBookAdapter:
        def capture(self, request, *, completed_pages, persist_page):
            captured_requests.append(request)
            assert completed_pages == ()
            for ordinal, label in enumerate(("37", "38"), 1):
                persist_page(
                    CapturedBookPage(
                        ordinal=ordinal,
                        printed_page_label=label,
                        reader_page_id=str(136 + ordinal),
                        image_body=_png(f"printed page {label}"),
                        mime_type="image/png",
                        exact_text=f"Exact reader text for page {label}.",
                    )
                )
            return BookCaptureSummary(
                final_url=(
                    "https://integrada.minhabiblioteca.com.br/reader/books/"
                    f"{RESOURCE_CODE}/pageid/138"
                ),
                original_library_url="https://philos.sophia.com.br/terminal/9418",
                capture_version="fake-browserbase-v1",
                diagnostics={"session_restarts": 0},
            )

    with TestClient(_app(test_database_url)) as client:
        _, _, reloaded = _save_page_scope(
            client,
            workbook_path,
            "Saved scope acquisition",
        )
        source_id = reloaded["lessons"][0]["sources"][0]["source_id"]
        queued_response = client.post(f"/api/sources/{source_id}/queue")

    assert queued_response.status_code == 202, queued_response.text
    queued = queued_response.json()["job"]
    with psycopg.connect(test_database_url) as conn:
        completed = process_next_job(
            conn,
            job_id=queued["id"],
            asset_store=LocalAssetStore(tmp_path / "book-assets"),
            book_adapter=RecordingBookAdapter(),
            book_document_parser=_parse_document,
            book_figure_locator=_locate_no_figures,
        )

    assert completed["status"] == "succeeded"
    assert completed["provider"] == "browserbase-book/v1"
    assert len(captured_requests) == 1
    assert captured_requests[0].source_id == source_id
    assert captured_requests[0].resource_code == RESOURCE_CODE
    assert captured_requests[0].scope_kind == "pages"
    assert captured_requests[0].scope_value == SAVED_SCOPE
