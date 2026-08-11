"""Ordered Reconstruction Module contracts with every external provider faked."""

import io

import pikepdf
from PIL import Image, ImageDraw
from psycopg.types.json import Jsonb

from universe.acquisition.book_acquisition import (
    BookAcquisitionError,
    BookCaptureSummary,
    CapturedBookPage,
)
from universe.acquisition.manual_uploads import (
    ManualAsset,
    acquire_manual_upload,
    create_manual_upload_job,
    list_manual_assets,
)
from universe.acquisition.pdfs import (
    PdfExtractionError,
    PdfFigureLocalizationResult,
    PdfParseResult,
)
from universe.acquisition.runner import enqueue_source, process_next_job
from universe.assets import LocalAssetStore


def _png(label: str, *, width: int = 320, height: int = 180) -> bytes:
    output = io.BytesIO()
    image = Image.new("RGB", (width, height), "white")
    ImageDraw.Draw(image).text((18, 18), label, fill="black")
    image.save(output, format="PNG")
    return output.getvalue()


def _empty_locator(calls):
    def locate(context, images):
        calls.append((context, tuple(images)))
        return PdfFigureLocalizationResult(
            regions=(),
            requested_model="fake/vision",
            response_model="fake/vision-resolved",
            provider="Fake Provider",
            usage={"total_tokens": 1},
            duration_ms=1,
        )

    return locate


def _parser(calls, *, markdown=None):
    def parse(body, filename, mime_type):
        with pikepdf.open(io.BytesIO(body)) as document:
            page_count = len(document.pages)
        calls.append((filename, mime_type, page_count, body))
        return PdfParseResult(
            markdown=(
                markdown
                or "## Ordered lesson\n\n"
                "The pages remain in reading order.\n\n"
                "| Variable | Value |\n| --- | ---: |\n| x | 2 |\n"
            ),
            image_urls=(),
            attempts=1,
            diagnostics={"estimated_credits": page_count},
        )

    return parse


def test_manual_ordered_images_use_one_ocr_document_and_original_page_evidence(
    db, tmp_path
):
    source_id = "source-ordered-manual-document"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Ordered screenshots', 'article')",
        (source_id, Jsonb({"canonical_url": "https://example.com/screenshots"})),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "ordered-manual-assets")
    job = create_manual_upload_job(
        db,
        source_id,
        [
            ManualAsset("page-1.png", "image/png", _png("first"), "screenshot"),
            ManualAsset("page-2.png", "image/png", _png("second"), "screenshot"),
        ],
        asset_store=store,
    )
    original_assets = list_manual_assets(db, job["id"])
    parse_calls = []
    locator_calls = []

    completed = acquire_manual_upload(
        db,
        job["id"],
        asset_store=store,
        pdf_document_parser=_parser(parse_calls),
        pdf_figure_locator=_empty_locator(locator_calls),
    )

    assert completed["status"] == "succeeded"
    assert completed["diagnostics"]["input_mode"] == "ordered_images"
    assert completed["diagnostics"]["extractor"]["document_mode"] == "ocr"
    assert completed["diagnostics"]["ordered_reconstruction"]["page_count"] == 2
    assert len(parse_calls) == 1
    assert parse_calls[0][1:3] == ("application/pdf", 2)
    assert parse_calls[0][3].startswith(b"%PDF-")
    assert len(locator_calls) == 1
    assert len(locator_calls[0][1]) == 2

    transport = db.execute(
        "SELECT id, kind, mime_type, metadata->>'publication_role'"
        " FROM source_asset WHERE acquisition_job_id = %s"
        " AND kind = 'ordered_document_pdf'",
        (job["id"],),
    ).fetchone()
    assert transport[1:] == (
        "ordered_document_pdf",
        "application/pdf",
        "implementation_transport_only",
    )
    pages = db.execute(
        "SELECT page_number, render_asset_id, text_layer_status"
        " FROM source_pdf_page WHERE acquisition_job_id = %s ORDER BY page_number",
        (job["id"],),
    ).fetchall()
    assert pages == [
        (1, original_assets[0]["id"], "empty"),
        (2, original_assets[1]["id"], "empty"),
    ]
    parse_options = db.execute(
        "SELECT options FROM pdf_document_parse_call WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()[0]
    assert parse_options["pdf_mode"] == "ocr"
    markdown = db.execute(
        "SELECT body FROM artifact WHERE id = %s", (completed["artifact_id"],)
    ).fetchone()[0]
    assert "| Variable | Value |" in markdown
    assert "Open original PDF" not in markdown
    assert all(f"/api/source-assets/{asset['id']}" not in markdown for asset in original_assets)
    assert db.execute(
        "SELECT status FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()[0] == "queued"


def test_book_adapter_feeds_the_same_module_and_preserves_exact_reader_text(
    db, tmp_path
):
    source_id = "source-ordered-book-document"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Integer programming', 'book')",
        (
            source_id,
            Jsonb(
                {
                    "kind": "book",
                    "resource_code": "9788522128303",
                    "scope": {"kind": "pages", "value": "198-199"},
                }
            ),
        ),
    )
    db.commit()
    events = []

    class FakeBookAdapter:
        def capture(self, request, *, completed_pages, persist_page):
            assert completed_pages == ()
            for ordinal, label in enumerate(("198", "199"), 1):
                persist_page(
                    CapturedBookPage(
                        ordinal=ordinal,
                        printed_page_label=label,
                        reader_page_id=str(209 + ordinal),
                        image_body=_png(f"printed page {label}"),
                        mime_type="image/png",
                        exact_text=f"Exact reader prose for printed page {label}.",
                    )
                )
                events.append(f"persist:{label}")
            events.append("capture:released")
            return BookCaptureSummary(
                final_url=(
                    "https://integrada.minhabiblioteca.com.br/reader/books/"
                    "9788522128303/pageid/211"
                ),
                original_library_url="https://philos.sophia.com.br/terminal/9418",
                capture_version="fake-browserbase-v1",
                diagnostics={"session_restarts": 0},
            )

    parse_calls = []

    def parse(*args):
        events.append("firecrawl:parse")
        return _parser(parse_calls, markdown="## Optimization\n\n$x \\le 2$\n")(*args)

    store = LocalAssetStore(tmp_path / "ordered-book-assets")
    queued = enqueue_source(db, source_id)
    completed = process_next_job(
        db,
        job_id=queued["id"],
        asset_store=store,
        book_adapter=FakeBookAdapter(),
        book_document_parser=parse,
        book_figure_locator=_empty_locator([]),
    )

    assert completed["status"] == "succeeded"
    assert completed["provider"] == "browserbase-book/v1"
    assert completed["diagnostics"]["input_mode"] == "book_pages"
    assert completed["diagnostics"]["exact_text_pages"] == 2
    assert events == [
        "persist:198",
        "persist:199",
        "capture:released",
        "firecrawl:parse",
    ]
    evidence = db.execute(
        "SELECT a.ordinal, a.kind, a.metadata->>'printed_page_label', t.body,"
        " p.text_body, p.render_asset_id = a.id"
        " FROM source_asset a"
        " JOIN source_asset_text t ON t.source_asset_id = a.id"
        " JOIN source_pdf_page p ON p.render_asset_id = a.id"
        " WHERE a.acquisition_job_id = %s ORDER BY a.ordinal",
        (queued["id"],),
    ).fetchall()
    assert evidence == [
        (1, "book_page", "198", "Exact reader prose for printed page 198.", "Exact reader prose for printed page 198.", True),
        (2, "book_page", "199", "Exact reader prose for printed page 199.", "Exact reader prose for printed page 199.", True),
    ]
    markdown = db.execute(
        "SELECT body, tool FROM artifact WHERE id = %s", (completed["artifact_id"],)
    ).fetchone()
    assert markdown[1] == "ordered-document-reconstruction"
    assert "$x \\le 2$" in markdown[0]
    assert "book-page" not in markdown[0]
    assert db.execute(
        "SELECT status FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()[0] == "queued"


def test_transient_book_capture_resumes_the_committed_page_prefix(db, tmp_path):
    source_id = "source-ordered-book-resume"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Resumable book', 'book')",
        (
            source_id,
            Jsonb(
                {
                    "kind": "book",
                    "resource_code": "book-42",
                    "scope": {"kind": "pages", "value": "10-11"},
                }
            ),
        ),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "resumable-book-assets")

    class InterruptedAdapter:
        def capture(self, request, *, completed_pages, persist_page):
            assert completed_pages == ()
            persist_page(
                CapturedBookPage(1, "10", "110", _png("page 10"), "image/png", "Page ten text.")
            )
            raise BookAcquisitionError(
                "book_capture_interrupted",
                "transient_browser",
                retriable=True,
            )

    queued = enqueue_source(db, source_id)
    retry = process_next_job(
        db,
        job_id=queued["id"],
        asset_store=store,
        book_adapter=InterruptedAdapter(),
    )
    assert retry["status"] == "queued"
    assert retry["diagnostics"]["retry_scheduled"] is True
    assert db.execute(
        "SELECT count(*) FROM source_asset WHERE acquisition_job_id = %s"
        " AND kind = 'book_page'",
        (queued["id"],),
    ).fetchone()[0] == 1

    seen_prefixes = []

    class ResumingAdapter:
        def capture(self, request, *, completed_pages, persist_page):
            seen_prefixes.append(tuple(completed_pages))
            persist_page(
                CapturedBookPage(2, "11", "111", _png("page 11"), "image/png", "Page eleven text.")
            )
            return BookCaptureSummary(
                final_url="https://reader.example/books/book-42/pageid/111",
                original_library_url="https://library.example/catalog",
                capture_version="fake-browserbase-v1",
                diagnostics={},
            )

    completed = process_next_job(
        db,
        job_id=queued["id"],
        asset_store=store,
        book_adapter=ResumingAdapter(),
        book_document_parser=_parser([]),
        book_figure_locator=_empty_locator([]),
    )
    assert completed["status"] == "succeeded"
    assert completed["attempt_count"] == 2
    assert len(seen_prefixes) == 1
    assert [(page.ordinal, page.printed_page_label) for page in seen_prefixes[0]] == [
        (1, "10")
    ]
    assert db.execute(
        "SELECT array_agg(ordinal ORDER BY ordinal) FROM source_asset"
        " WHERE acquisition_job_id = %s AND kind = 'book_page'",
        (queued["id"],),
    ).fetchone()[0] == [1, 2]


def test_transient_firecrawl_failure_retries_book_without_recapturing_pages(
    db, tmp_path
):
    source_id = "source-ordered-book-firecrawl-retry"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Retryable reconstruction', 'book')",
        (
            source_id,
            Jsonb(
                {
                    "kind": "book",
                    "resource_code": "book-retry",
                    "scope": {"kind": "pages", "value": "10"},
                }
            ),
        ),
    )
    db.commit()
    store = LocalAssetStore(tmp_path / "retryable-reconstruction-assets")
    completed_prefix_lengths = []

    class CompleteAdapter:
        def capture(self, request, *, completed_pages, persist_page):
            completed_prefix_lengths.append(len(completed_pages))
            if not completed_pages:
                persist_page(
                    CapturedBookPage(
                        1,
                        "10",
                        "110",
                        _png("page 10"),
                        "image/png",
                        "Page ten text.",
                    )
                )
            return BookCaptureSummary(
                final_url="https://reader.example/books/book-retry/pageid/110",
                original_library_url="https://library.example/catalog",
                capture_version="fake-browserbase-v1",
                diagnostics={},
            )

    parse_calls = []

    def parse(*args):
        parse_calls.append(1)
        if len(parse_calls) == 1:
            raise PdfExtractionError(
                "pdf_parse_failed",
                "firecrawl_retries_exhausted",
                {"http_status": 503},
                retriable=True,
                retry_after_seconds=0,
            )
        return _parser([], markdown="# Reconstructed\n")(*args)

    queued = enqueue_source(db, source_id)
    retry = process_next_job(
        db,
        job_id=queued["id"],
        asset_store=store,
        book_adapter=CompleteAdapter(),
        book_document_parser=parse,
        book_figure_locator=_empty_locator([]),
    )

    assert retry["status"] == "queued"
    assert retry["diagnostics"]["retry_scheduled"] is True

    completed = process_next_job(
        db,
        job_id=queued["id"],
        asset_store=store,
        book_adapter=CompleteAdapter(),
        book_document_parser=parse,
        book_figure_locator=_empty_locator([]),
    )

    assert completed["status"] == "succeeded"
    assert completed["attempt_count"] == 2
    assert completed_prefix_lengths == [0, 1]
    assert len(parse_calls) == 2
    assert db.execute(
        "SELECT count(*), sum(attempt_count), max(status)"
        " FROM pdf_document_parse_call WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone() == (1, 2, "succeeded")
