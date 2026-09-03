"""Durable ordered book-page capture behind a provider Adapter Interface.

This Module owns provider-neutral validation and persistence.  A Browserbase
Implementation may navigate a reader, but it can only publish pages through
``persist_page``; the acquisition ledger never depends on browser objects,
session identifiers, or temporary files.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg.types.json import Jsonb

from universe.assets import AssetStore, asset_store_from_env
from universe.acquisition.book_toc import parse_chapter_selector
from universe.acquisition.ordered_reconstruction import (
    ORDERED_RECONSTRUCTION_TOOL,
    ORDERED_RECONSTRUCTION_VERSION,
    FigureLocator,
    PdfBuilder,
    ordered_page_from_asset,
    reconstruct_ordered_document,
)
from universe.acquisition.pdf_figure_recovery import PdfDownloadedImage
from universe.acquisition.pdfs import (
    PdfExtractionError,
    PdfParseResult,
    download_pdf_image,
    parse_pdf_with_firecrawl,
)


BOOK_PROVIDER = "browserbase-book/v1"
BOOK_CAPTURE_TOOL = "browserbase-book-capture"
BOOK_TEXT_TOOL = "reader-accessibility-text"
BOOK_TEXT_TOOL_VERSION = "reader-accessibility-text.v1"
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_PAGE_BYTES = 30 * 1024 * 1024
MAX_PAGE_COUNT = 50
BOOK_SCOPE_KINDS = {"pages", "chapters"}


@dataclass(frozen=True)
class BookCaptureRequest:
    source_id: str
    title: str
    resource_code: str
    scope_kind: str
    scope_value: str


@dataclass(frozen=True)
class CapturedBookPage:
    ordinal: int
    printed_page_label: str
    reader_page_id: str
    image_body: bytes
    mime_type: str
    exact_text: str


@dataclass(frozen=True)
class CompletedBookPage:
    ordinal: int
    source_asset_id: str
    printed_page_label: str
    reader_page_id: str
    image_sha256: str
    exact_text_sha256: str


@dataclass(frozen=True)
class BookCaptureSummary:
    final_url: str
    original_library_url: str
    capture_version: str
    resolved_page_labels: tuple[str, ...]
    diagnostics: Mapping[str, Any]


@dataclass(frozen=True)
class BookOutcome:
    markdown: str | None
    failure_code: str | None
    provider: str
    tool: str
    tool_version: str | None
    diagnostics: dict[str, Any]
    content_hash: str | None = None
    raw_markdown: str | None = None
    retryable: bool = False
    retry_after_seconds: int = 0

    @property
    def succeeded(self) -> bool:
        return self.markdown is not None and self.failure_code is None


class BookCaptureAdapter(Protocol):
    """Resolve the requested page or chapter scope into ordered captured pages."""

    def capture(
        self,
        request: BookCaptureRequest,
        *,
        completed_pages: Sequence[CompletedBookPage],
        persist_page: Callable[[CapturedBookPage], CompletedBookPage],
    ) -> BookCaptureSummary: ...


class BookAcquisitionError(RuntimeError):
    def __init__(
        self,
        code: str,
        category: str,
        *,
        retriable: bool = False,
        retry_after_seconds: int = 0,
    ):
        self.code = code
        self.category = category
        self.retriable = retriable
        self.retry_after_seconds = max(0, int(retry_after_seconds))
        super().__init__(code)


def book_capture_outcome(
    conn: psycopg.Connection,
    claimed_job: Mapping[str, Any],
    *,
    adapter: BookCaptureAdapter | None,
    asset_store: AssetStore | None = None,
    document_parser: Callable[[bytes, str, str], PdfParseResult] = parse_pdf_with_firecrawl,
    image_downloader: Callable[[str], PdfDownloadedImage] = download_pdf_image,
    figure_locator: FigureLocator | None = None,
    pdf_builder: PdfBuilder | None = None,
) -> BookOutcome:
    """Capture a concrete book scope while preserving each completed page."""
    if claimed_job.get("provider") != BOOK_PROVIDER:
        raise ValueError("book_capture_outcome requires a Browserbase book job")
    if claimed_job.get("status") != "running" or not claimed_job.get("claim_token"):
        raise ValueError("book_capture_outcome requires a currently claimed job")

    source = conn.execute(
        "SELECT title, identity, media_type FROM source WHERE id = %s",
        (claimed_job["source_id"],),
    ).fetchone()
    if source is None or source[2] != "book":
        conn.commit()
        return _failure("invalid_book_source", "invalid_source")
    try:
        request = _request(
            source_id=str(claimed_job["source_id"]),
            title=str(source[0] or "Book source"),
            identity=dict(source[1] or {}),
        )
    except BookAcquisitionError as exc:
        conn.commit()
        return _failure(exc.code, exc.category)
    if adapter is None:
        from universe.acquisition.browserbase_book_adapter import (
            BrowserbaseBookAdapter,
        )

        adapter = BrowserbaseBookAdapter()

    store = asset_store or asset_store_from_env()
    completed = _completed_pages(conn, str(claimed_job["id"]))
    conn.commit()

    def persist_page(page: CapturedBookPage) -> CompletedBookPage:
        validated = _validate_page(page)
        return _persist_page(conn, claimed_job, validated, store)

    try:
        summary = adapter.capture(
            request,
            completed_pages=tuple(completed),
            persist_page=persist_page,
        )
        if not isinstance(summary, BookCaptureSummary):
            raise BookAcquisitionError(
                "book_capture_invalid_summary", "invalid_adapter_result"
            )
        completed = _completed_pages(conn, str(claimed_job["id"]))
        _validate_completion(request, completed, summary)
        rows = _page_rows(conn, str(claimed_job["id"]), store)
        conn.commit()
    except BookAcquisitionError as exc:
        conn.rollback()
        return _failure(
            exc.code,
            exc.category,
            retryable=exc.retriable,
            retry_after_seconds=exc.retry_after_seconds,
        )
    except PdfExtractionError as exc:
        conn.rollback()
        return _failure(
            exc.code,
            exc.category,
            diagnostics=exc.diagnostics,
            retryable=exc.retriable,
            retry_after_seconds=exc.retry_after_seconds,
        )
    except Exception as exc:
        conn.rollback()
        return BookOutcome(
            None,
            "book_capture_failed",
            BOOK_PROVIDER,
            BOOK_CAPTURE_TOOL,
            None,
            {
                "category": "adapter_error",
                "exception": type(exc).__name__,
                "scope_kind": request.scope_kind,
                "scope_value": request.scope_value,
            },
        )

    manifest_hash = _manifest_hash(completed)
    try:
        reconstruction = reconstruct_ordered_document(
            conn,
            job=claimed_job,
            title=request.title,
            pages=[
                ordered_page_from_asset(row, exact_text=str(row["exact_text"] or ""))
                for row in rows
            ],
            input_mode="book_pages",
            asset_store=store,
            document_parser=document_parser,
            image_downloader=image_downloader,
            figure_locator=figure_locator,
            pdf_builder=pdf_builder,
        )
    except PdfExtractionError as exc:
        return _failure(
            exc.code,
            exc.category,
            diagnostics=exc.diagnostics,
            retryable=exc.retriable,
            retry_after_seconds=exc.retry_after_seconds,
        )
    except Exception as exc:
        conn.rollback()
        return BookOutcome(
            None,
            "book_reconstruction_failed",
            BOOK_PROVIDER,
            ORDERED_RECONSTRUCTION_TOOL,
            ORDERED_RECONSTRUCTION_VERSION,
            {
                "category": "ordered_reconstruction_error",
                "exception": type(exc).__name__,
                "input_mode": "book_pages",
                "input_manifest_sha256": manifest_hash,
            },
        )
    diagnostics = {
        **reconstruction.diagnostics,
        "input_mode": "book_pages",
        "input_manifest_sha256": manifest_hash,
        "visual_source_kind": "book_pages",
        "resource_code": request.resource_code,
        "scope_kind": request.scope_kind,
        "scope_value": request.scope_value,
        "final_url": _public_url(summary.final_url),
        "original_library_url": _public_url(summary.original_library_url),
        "capture_version": _required_text(summary.capture_version, "capture_version"),
        "capture": _safe_diagnostics(summary.diagnostics),
    }
    return BookOutcome(
        reconstruction.enriched_markdown,
        None,
        BOOK_PROVIDER,
        ORDERED_RECONSTRUCTION_TOOL,
        ORDERED_RECONSTRUCTION_VERSION,
        diagnostics,
        manifest_hash,
        reconstruction.raw_markdown,
    )


def _request(*, source_id: str, title: str, identity: Mapping[str, Any]) -> BookCaptureRequest:
    resource_code = _required_text(identity.get("resource_code"), "resource_code")
    scope = identity.get("scope")
    if not isinstance(scope, Mapping):
        raise BookAcquisitionError("book_scope_required", "missing_concrete_scope")
    scope_kind = _required_text(scope.get("kind"), "scope.kind")
    scope_value = _required_text(scope.get("value"), "scope.value")
    if scope_kind not in BOOK_SCOPE_KINDS:
        raise BookAcquisitionError("book_scope_invalid", "missing_concrete_scope")
    if scope_kind == "pages" and book_page_labels(scope_value) is None:
        raise BookAcquisitionError("book_scope_invalid", "missing_concrete_scope")
    if scope_kind == "chapters" and parse_chapter_selector(scope_value) is None:
        raise BookAcquisitionError("book_scope_invalid", "missing_concrete_scope")
    return BookCaptureRequest(
        source_id=source_id,
        title=title,
        resource_code=resource_code,
        scope_kind=scope_kind,
        scope_value=scope_value,
    )


def _validate_page(page: CapturedBookPage) -> CapturedBookPage:
    if not isinstance(page, CapturedBookPage):
        raise BookAcquisitionError("book_page_invalid", "invalid_adapter_result")
    if not isinstance(page.ordinal, int) or not 1 <= page.ordinal <= MAX_PAGE_COUNT:
        raise BookAcquisitionError("book_page_ordinal_invalid", "invalid_adapter_result")
    label = _required_text(page.printed_page_label, "printed_page_label")
    reader_id = _required_text(page.reader_page_id, "reader_page_id")
    if page.mime_type not in IMAGE_MIME_TYPES:
        raise BookAcquisitionError("book_page_mime_invalid", "invalid_adapter_result")
    if not isinstance(page.image_body, bytes) or not 0 < len(page.image_body) <= MAX_PAGE_BYTES:
        raise BookAcquisitionError("book_page_bytes_invalid", "invalid_adapter_result")
    if not isinstance(page.exact_text, str):
        raise BookAcquisitionError("book_page_text_invalid", "invalid_adapter_result")
    return CapturedBookPage(
        ordinal=page.ordinal,
        printed_page_label=label,
        reader_page_id=reader_id,
        image_body=page.image_body,
        mime_type=page.mime_type,
        exact_text=page.exact_text.replace("\r\n", "\n").replace("\r", "\n").strip(),
    )


def _persist_page(
    conn: psycopg.Connection,
    job: Mapping[str, Any],
    page: CapturedBookPage,
    store: AssetStore,
) -> CompletedBookPage:
    owned = conn.execute(
        "SELECT 1 FROM acquisition_job WHERE id = %s AND status = 'running'"
        " AND claim_token = %s",
        (job["id"], job["claim_token"]),
    ).fetchone()
    if owned is None:
        conn.rollback()
        raise BookAcquisitionError("book_capture_lease_lost", "lease_lost")
    image_sha = hashlib.sha256(page.image_body).hexdigest()
    text_sha = hashlib.sha256(page.exact_text.encode("utf-8")).hexdigest()
    stored = store.put(page.image_body, sha256=image_sha)
    identity = hashlib.sha256(
        f"{job['id']}:{page.ordinal}:{image_sha}".encode("utf-8")
    ).hexdigest()[:32]
    asset_id = f"asset-book-{identity}"
    filename = f"book-page-{page.ordinal:04d}.{page.mime_type.split('/')[-1].replace('jpeg', 'jpg')}"
    conn.execute(
        "INSERT INTO source_asset"
        " (id, acquisition_job_id, source_id, ordinal, kind, filename, mime_type,"
        " sha256, byte_size, storage_key, metadata)"
        " VALUES (%s, %s, %s, %s, 'book_page', %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (acquisition_job_id, ordinal) DO NOTHING",
        (
            asset_id,
            job["id"],
            job["source_id"],
            page.ordinal,
            filename,
            page.mime_type,
            image_sha,
            len(page.image_body),
            stored.key,
            Jsonb(
                {
                    "printed_page_label": page.printed_page_label,
                    "reader_page_id": page.reader_page_id,
                }
            ),
        ),
    )
    existing = conn.execute(
        "SELECT id, sha256, metadata FROM source_asset"
        " WHERE acquisition_job_id = %s AND ordinal = %s",
        (job["id"], page.ordinal),
    ).fetchone()
    if existing is None or existing[1] != image_sha or dict(existing[2] or {}) != {
        "printed_page_label": page.printed_page_label,
        "reader_page_id": page.reader_page_id,
    }:
        conn.rollback()
        raise BookAcquisitionError("book_page_conflict", "capture_conflict")
    asset_id = existing[0]
    conn.execute(
        "INSERT INTO source_asset_text"
        " (source_asset_id, body, text_sha256, tool, tool_version, metadata)"
        " VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (
            asset_id,
            page.exact_text,
            text_sha,
            BOOK_TEXT_TOOL,
            BOOK_TEXT_TOOL_VERSION,
            Jsonb({"reader_page_id": page.reader_page_id}),
        ),
    )
    existing_text = conn.execute(
        "SELECT text_sha256 FROM source_asset_text WHERE source_asset_id = %s",
        (asset_id,),
    ).fetchone()
    if existing_text is None or existing_text[0] != text_sha:
        conn.rollback()
        raise BookAcquisitionError("book_page_text_conflict", "capture_conflict")
    conn.commit()
    return CompletedBookPage(
        page.ordinal,
        asset_id,
        page.printed_page_label,
        page.reader_page_id,
        image_sha,
        text_sha,
    )


def _completed_pages(conn: psycopg.Connection, job_id: str) -> list[CompletedBookPage]:
    rows = conn.execute(
        "SELECT a.ordinal, a.id, a.metadata->>'printed_page_label',"
        " a.metadata->>'reader_page_id', a.sha256, t.text_sha256"
        " FROM source_asset a JOIN source_asset_text t ON t.source_asset_id = a.id"
        " WHERE a.acquisition_job_id = %s AND a.kind = 'book_page'"
        " ORDER BY a.ordinal",
        (job_id,),
    ).fetchall()
    return [CompletedBookPage(*row) for row in rows]


def _page_rows(
    conn: psycopg.Connection, job_id: str, store: AssetStore
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT a.id, a.ordinal, a.filename, a.mime_type, a.sha256, a.byte_size,"
        " a.storage_key, a.metadata, t.body"
        " FROM source_asset a JOIN source_asset_text t ON t.source_asset_id = a.id"
        " WHERE a.acquisition_job_id = %s AND a.kind = 'book_page'"
        " ORDER BY a.ordinal",
        (job_id,),
    ).fetchall()
    result = []
    for row in rows:
        try:
            body = store.get(row[6])
        except Exception as exc:
            raise PdfExtractionError(
                "book_page_unavailable", "asset_storage_read_failed"
            ) from exc
        result.append(
            {
                "id": row[0],
                "ordinal": row[1],
                "filename": row[2],
                "mime_type": row[3],
                "sha256": row[4],
                "byte_size": row[5],
                "storage_key": row[6],
                "metadata": dict(row[7] or {}),
                "exact_text": row[8],
                "body": body,
            }
        )
    return result


def _validate_completion(
    request: BookCaptureRequest,
    pages: Sequence[CompletedBookPage],
    summary: BookCaptureSummary,
) -> None:
    plan = tuple(str(label or "").strip() for label in summary.resolved_page_labels)
    if (
        not plan
        or len(plan) > MAX_PAGE_COUNT
        or any(not label for label in plan)
        or len(set(plan)) != len(plan)
    ):
        raise BookAcquisitionError(
            "book_capture_invalid_summary", "invalid_adapter_result"
        )
    expected_ordinals = list(range(1, len(plan) + 1))
    if [page.ordinal for page in pages] != expected_ordinals:
        raise BookAcquisitionError("book_capture_incomplete", "missing_page")
    captured_labels = tuple(page.printed_page_label for page in pages)
    if captured_labels != plan:
        raise BookAcquisitionError("book_capture_scope_mismatch", "scope_mismatch")
    if request.scope_kind == "pages":
        labels = book_page_labels(request.scope_value)
        if labels is None:
            raise BookAcquisitionError("book_scope_invalid", "missing_concrete_scope")
        if plan != labels:
            raise BookAcquisitionError("book_capture_scope_mismatch", "scope_mismatch")


def book_page_labels(value: str) -> tuple[str, ...] | None:
    """Return one concrete, bounded printed-page scope for every Adapter."""
    normalized = str(value or "").strip().replace("–", "-").replace("—", "-")
    range_match = re.fullmatch(r"([0-9]+)\s*-\s*([0-9]+)", normalized)
    if range_match:
        start, end = map(int, range_match.groups())
        if start <= end and end - start + 1 <= MAX_PAGE_COUNT:
            return tuple(str(page) for page in range(start, end + 1))
        return None
    if re.fullmatch(r"[0-9]+(?:\s*,\s*[0-9]+)*", normalized):
        labels = [part.strip() for part in normalized.split(",")]
        if len(labels) <= MAX_PAGE_COUNT and len(set(labels)) == len(labels):
            return tuple(labels)
    return None


def _manifest_hash(pages: Sequence[CompletedBookPage]) -> str:
    manifest = "\n".join(
        f"{page.ordinal}:{page.printed_page_label}:{page.reader_page_id}:"
        f"{page.image_sha256}:{page.exact_text_sha256}"
        for page in pages
    )
    return hashlib.sha256(manifest.encode("utf-8")).hexdigest()


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BookAcquisitionError("book_scope_invalid", f"invalid_{field}")
    return value.strip()


def _public_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return ""
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _safe_diagnostics(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    allowed = {"session_restarts", "page_attempts", "reader_kind", "warnings"}
    return {key: value[key] for key in allowed if key in value}


def _failure(
    code: str,
    category: str,
    *,
    diagnostics: Mapping[str, Any] | None = None,
    retryable: bool = False,
    retry_after_seconds: int = 0,
) -> BookOutcome:
    return BookOutcome(
        None,
        code,
        BOOK_PROVIDER,
        BOOK_CAPTURE_TOOL,
        None,
        {"category": category, **dict(diagnostics or {})},
        retryable=retryable,
        retry_after_seconds=retry_after_seconds,
    )
