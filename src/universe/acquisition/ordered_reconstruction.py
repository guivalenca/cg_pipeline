"""Deep ordered-page reconstruction over the structural PDF pipeline.

Callers provide ordered immutable page evidence.  This Module hides image
normalization, PDF transport packaging, durable Firecrawl parsing, exhaustive
figure placement, and the audit-only page ledger behind one Interface.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import psycopg
from PIL import Image, ImageOps, UnidentifiedImageError
from psycopg.types.json import Jsonb

from universe.acquisition.pdf_figure_recovery import (
    PdfDownloadedImage,
    PdfFigureLocalizationResult,
)
from universe.acquisition.pdfs import (
    PdfAcquisitionResult,
    PdfExtractionError,
    PdfPage,
    PdfParseResult,
    acquire_pdf_document,
    download_pdf_image,
    parse_pdf_with_firecrawl,
)
from universe.acquisition.source_images import SourceImageInput
from universe.assets import AssetStore
from universe.settings import private_pdf_figure_localization_enabled


ORDERED_RECONSTRUCTION_TOOL = "ordered-document-reconstruction"
ORDERED_RECONSTRUCTION_VERSION = "ordered-document-reconstruction.v1"
ORDERED_PDF_BUILDER_VERSION = "img2pdf-lossless.v1"
ORDERED_PDF_ORDINAL = 3_000_000
MAX_ORDERED_PAGES = 50
MAX_PAGE_PIXELS = 40_000_000
MAX_TRANSPORT_PDF_BYTES = 50 * 1024 * 1024
ORDERED_IMAGE_KINDS = {"screenshot", "image", "book_page"}
ORDERED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}


@dataclass(frozen=True)
class OrderedPageEvidence:
    asset_id: str
    ordinal: int
    filename: str
    mime_type: str
    body: bytes
    sha256: str
    exact_text: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OrderedReconstructionResult:
    raw_markdown: str
    enriched_markdown: str
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class _NormalizedPage:
    evidence: OrderedPageEvidence
    png_body: bytes
    width: int
    height: int
    reusable_render_asset_id: str | None


PdfBuilder = Callable[[Sequence[bytes]], bytes]
FigureLocator = Callable[
    [str, list[SourceImageInput]], PdfFigureLocalizationResult
]


def reconstruct_ordered_document(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    title: str,
    pages: Sequence[OrderedPageEvidence],
    input_mode: str,
    asset_store: AssetStore,
    document_parser: Callable[[bytes, str, str], PdfParseResult] = parse_pdf_with_firecrawl,
    image_downloader: Callable[[str], PdfDownloadedImage] = download_pdf_image,
    figure_locator: FigureLocator | None = None,
    pdf_builder: PdfBuilder | None = None,
) -> OrderedReconstructionResult:
    """Reconstruct one contiguous page sequence as rich canonical Markdown."""
    if input_mode not in {"ordered_images", "book_pages"}:
        raise ValueError("ordered reconstruction requires a known input mode")
    _validate_claim(conn, job)
    normalized = _validated_pages(conn, job, pages)
    if figure_locator is None and not private_pdf_figure_localization_enabled():
        raise PdfExtractionError(
            "ordered_figure_localization_disabled",
            "external_page_export_disabled",
        )

    manifest_sha = _manifest_sha(normalized)
    evidence_ids = [page.evidence.asset_id for page in normalized]
    transport = _existing_transport_pdf(
        conn,
        job=job,
        title=title,
        input_mode=input_mode,
        manifest_sha=manifest_sha,
        evidence_ids=evidence_ids,
        store=asset_store,
    )
    transport_reused = transport is not None
    if transport is None:
        transport_body = (pdf_builder or build_lossless_image_pdf)(
            [page.png_body for page in normalized]
        )
        _validate_transport_body(transport_body)
        transport = _persist_transport_pdf(
            conn,
            job=job,
            title=title,
            input_mode=input_mode,
            manifest_sha=manifest_sha,
            body=transport_body,
            evidence_ids=evidence_ids,
            store=asset_store,
        )
    else:
        transport_body = bytes(transport["body"])

    pdf_pages = [
        PdfPage(
            page_number=index,
            text=_normalize_text(page.evidence.exact_text),
            render_body=page.png_body,
            width=page.width,
            height=page.height,
            render_asset_id=page.reusable_render_asset_id,
        )
        for index, page in enumerate(normalized, 1)
    ]

    parser = document_parser
    if document_parser is parse_pdf_with_firecrawl:
        parser = lambda body, filename, mime_type: parse_pdf_with_firecrawl(
            body, filename, mime_type, mode="ocr"
        )
    acquired: PdfAcquisitionResult = acquire_pdf_document(
        conn,
        job=job,
        title=_markdown_inline(title),
        pdf_asset=transport,
        asset_store=asset_store,
        document_parser=parser,
        image_downloader=image_downloader,
        figure_locator=figure_locator,
        page_extractor=lambda _body: tuple(pdf_pages),
        document_mode="ocr",
        input_mode=input_mode,
        evidence_asset_ids=[page.evidence.asset_id for page in normalized],
        source_link_label=None,
        render_tool="ordered-page-evidence",
        render_tool_version=ORDERED_RECONSTRUCTION_VERSION,
    )
    diagnostics = {
        **acquired.diagnostics,
        "input_manifest_sha256": manifest_sha,
        "transport_asset_id": transport["id"],
        "total_bytes": sum(len(page.evidence.body) for page in normalized),
        "exact_text_pages": sum(
            bool(_normalize_text(page.evidence.exact_text)) for page in normalized
        ),
        "ordered_reconstruction": {
            "tool": ORDERED_RECONSTRUCTION_TOOL,
            "tool_version": ORDERED_RECONSTRUCTION_VERSION,
            "pdf_builder_version": ORDERED_PDF_BUILDER_VERSION,
            "transport_pdf_bytes": len(transport_body),
            "transport_reused": transport_reused,
            "page_count": len(normalized),
            "publication_role": "implementation_transport_only",
        },
        "tool_version": ORDERED_RECONSTRUCTION_VERSION,
    }
    return OrderedReconstructionResult(
        acquired.raw_markdown,
        acquired.enriched_markdown,
        diagnostics,
    )


def ordered_page_from_asset(
    asset: Mapping[str, Any], *, exact_text: str = ""
) -> OrderedPageEvidence:
    return OrderedPageEvidence(
        asset_id=str(asset["id"]),
        ordinal=int(asset["ordinal"]),
        filename=str(asset["filename"]),
        mime_type=str(asset["mime_type"]),
        body=bytes(asset["body"]),
        sha256=str(asset["sha256"]),
        exact_text=exact_text,
        metadata=dict(asset.get("metadata") or {}),
    )


def build_lossless_image_pdf(page_pngs: Sequence[bytes]) -> bytes:
    """Package decoded page pixels without a second lossy encoding."""
    if not page_pngs:
        raise PdfExtractionError("ordered_pages_missing", "missing_inputs")
    try:
        import img2pdf
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise PdfExtractionError(
            "ordered_pdf_builder_missing", "configuration"
        ) from exc
    try:
        body = img2pdf.convert(*page_pngs, rotation=img2pdf.Rotation.ifvalid)
    except Exception as exc:
        raise PdfExtractionError(
            "ordered_pdf_packaging_failed", "image_pdf_conversion_failed"
        ) from exc
    return bytes(body)


def _validate_claim(conn: psycopg.Connection, job: Mapping[str, Any]) -> None:
    if job.get("status") != "running" or not job.get("claim_token"):
        raise ValueError("ordered reconstruction requires a currently claimed job")
    row = conn.execute(
        "SELECT 1 FROM acquisition_job WHERE id = %s AND source_id = %s"
        " AND status = 'running' AND claim_token = %s",
        (job["id"], job["source_id"], job["claim_token"]),
    ).fetchone()
    if row is None:
        raise PdfExtractionError("ordered_reconstruction_lease_lost", "lease_lost")


def _validated_pages(
    conn: psycopg.Connection,
    job: Mapping[str, Any],
    pages: Sequence[OrderedPageEvidence],
) -> list[_NormalizedPage]:
    if not 1 <= len(pages) <= MAX_ORDERED_PAGES:
        raise PdfExtractionError("ordered_page_count_invalid", "invalid_inputs")
    if [page.ordinal for page in pages] != list(range(1, len(pages) + 1)):
        raise PdfExtractionError("ordered_page_order_invalid", "invalid_inputs")

    result: list[_NormalizedPage] = []
    seen: set[str] = set()
    for page in pages:
        if page.asset_id in seen:
            raise PdfExtractionError("ordered_page_duplicate", "invalid_inputs")
        seen.add(page.asset_id)
        if page.mime_type not in ORDERED_IMAGE_MIME_TYPES:
            raise PdfExtractionError("ordered_page_mime_invalid", "invalid_inputs")
        body_sha = hashlib.sha256(page.body).hexdigest()
        if body_sha != page.sha256:
            raise PdfExtractionError("ordered_page_hash_mismatch", "invalid_inputs")
        row = conn.execute(
            "SELECT ordinal, kind, mime_type, sha256, byte_size FROM source_asset"
            " WHERE id = %s AND acquisition_job_id = %s AND source_id = %s",
            (page.asset_id, job["id"], job["source_id"]),
        ).fetchone()
        if (
            row is None
            or row[0] != page.ordinal
            or row[1] not in ORDERED_IMAGE_KINDS
            or row[2] != page.mime_type
            or row[3] != page.sha256
            or row[4] != len(page.body)
        ):
            raise PdfExtractionError(
                "ordered_page_asset_mismatch", "immutable_evidence_mismatch"
            )
        png_body, width, height, reusable = _normalize_page(page)
        result.append(
            _NormalizedPage(
                page,
                png_body,
                width,
                height,
                page.asset_id if reusable else None,
            )
        )
    return result


def _normalize_page(page: OrderedPageEvidence) -> tuple[bytes, int, int, bool]:
    try:
        with Image.open(io.BytesIO(page.body)) as source:
            source.load()
            width, height = source.size
            if width < 1 or height < 1 or width * height > MAX_PAGE_PIXELS:
                raise PdfExtractionError(
                    "ordered_page_dimensions_invalid", "invalid_inputs"
                )
            orientation = source.getexif().get(274, 1)
            if (
                page.mime_type == "image/png"
                and source.format == "PNG"
                and orientation in {None, 1}
            ):
                return page.body, width, height, True
            image = ImageOps.exif_transpose(source)
            if image.mode in {"RGBA", "LA"} or (
                image.mode == "P" and "transparency" in image.info
            ):
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue(), image.width, image.height, False
    except PdfExtractionError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise PdfExtractionError(
            "ordered_page_decode_failed", "invalid_image_body"
        ) from exc


def _validate_transport_body(body: bytes) -> None:
    if (
        not isinstance(body, bytes)
        or not body.startswith(b"%PDF-")
        or len(body) > MAX_TRANSPORT_PDF_BYTES
    ):
        raise PdfExtractionError(
            "ordered_pdf_packaging_failed", "invalid_or_oversized_transport_pdf"
        )


def _transport_asset_id(job_id: str, manifest_sha: str) -> str:
    identity = hashlib.sha256(
        f"{job_id}:{manifest_sha}:{ORDERED_PDF_BUILDER_VERSION}".encode("utf-8")
    ).hexdigest()[:32]
    return f"asset-ordered-pdf-{identity}"


def _transport_filename(title: str) -> str:
    filename_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", title).strip("-.")[:80]
    return f"{filename_stem or 'ordered-document'}.pdf"


def _transport_metadata(
    *, input_mode: str, manifest_sha: str, evidence_ids: Sequence[str]
) -> dict[str, Any]:
    return {
        "derived_by": ORDERED_PDF_BUILDER_VERSION,
        "input_mode": input_mode,
        "input_manifest_sha256": manifest_sha,
        "evidence_asset_ids": list(evidence_ids),
        "publication_role": "implementation_transport_only",
    }


def _existing_transport_pdf(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    title: str,
    input_mode: str,
    manifest_sha: str,
    evidence_ids: Sequence[str],
    store: AssetStore,
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, source_id, ordinal, kind, filename, mime_type, sha256,"
        " byte_size, storage_key, metadata FROM source_asset"
        " WHERE acquisition_job_id = %s AND ordinal = %s",
        (job["id"], ORDERED_PDF_ORDINAL),
    ).fetchone()
    if row is None:
        return None
    expected = (
        _transport_asset_id(str(job["id"]), manifest_sha),
        job["source_id"],
        ORDERED_PDF_ORDINAL,
        "ordered_document_pdf",
        _transport_filename(title),
        "application/pdf",
    )
    metadata = _transport_metadata(
        input_mode=input_mode,
        manifest_sha=manifest_sha,
        evidence_ids=evidence_ids,
    )
    if row[:6] != expected or dict(row[9] or {}) != metadata:
        raise PdfExtractionError(
            "ordered_pdf_conflict", "immutable_transport_conflict"
        )
    try:
        body = store.get(str(row[8]))
    except Exception as exc:
        raise PdfExtractionError(
            "ordered_pdf_unavailable", "asset_storage_read_failed"
        ) from exc
    if len(body) != row[7] or hashlib.sha256(body).hexdigest() != row[6]:
        raise PdfExtractionError(
            "ordered_pdf_conflict", "immutable_transport_conflict"
        )
    _validate_transport_body(body)
    return {
        "id": row[0],
        "ordinal": row[2],
        "kind": row[3],
        "filename": row[4],
        "mime_type": row[5],
        "sha256": row[6],
        "byte_size": row[7],
        "storage_key": row[8],
        "metadata": row[9],
        "body": body,
    }


def _persist_transport_pdf(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    title: str,
    input_mode: str,
    manifest_sha: str,
    body: bytes,
    evidence_ids: Sequence[str],
    store: AssetStore,
) -> dict[str, Any]:
    body_sha = hashlib.sha256(body).hexdigest()
    asset_id = _transport_asset_id(str(job["id"]), manifest_sha)
    filename = _transport_filename(title)
    metadata = _transport_metadata(
        input_mode=input_mode,
        manifest_sha=manifest_sha,
        evidence_ids=evidence_ids,
    )
    existing_at_ordinal = conn.execute(
        "SELECT id, sha256 FROM source_asset"
        " WHERE acquisition_job_id = %s AND ordinal = %s",
        (job["id"], ORDERED_PDF_ORDINAL),
    ).fetchone()
    if existing_at_ordinal is not None and existing_at_ordinal != (asset_id, body_sha):
        raise PdfExtractionError(
            "ordered_pdf_conflict", "immutable_transport_conflict"
        )
    stored = store.put(body, sha256=body_sha)
    conn.execute(
        "INSERT INTO source_asset"
        " (id, acquisition_job_id, source_id, ordinal, kind, filename, mime_type,"
        " sha256, byte_size, storage_key, metadata)"
        " VALUES (%s, %s, %s, %s, 'ordered_document_pdf', %s,"
        " 'application/pdf', %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (
            asset_id,
            job["id"],
            job["source_id"],
            ORDERED_PDF_ORDINAL,
            filename,
            body_sha,
            len(body),
            stored.key,
            Jsonb(metadata),
        ),
    )
    row = conn.execute(
        "SELECT id, ordinal, kind, filename, mime_type, sha256, byte_size,"
        " storage_key, metadata FROM source_asset WHERE id = %s",
        (asset_id,),
    ).fetchone()
    if row is None or row[1:] != (
        ORDERED_PDF_ORDINAL,
        "ordered_document_pdf",
        filename,
        "application/pdf",
        body_sha,
        len(body),
        stored.key,
        metadata,
    ):
        raise PdfExtractionError(
            "ordered_pdf_conflict", "immutable_transport_conflict"
        )
    conn.commit()
    return {
        "id": row[0],
        "ordinal": row[1],
        "kind": row[2],
        "filename": row[3],
        "mime_type": row[4],
        "sha256": row[5],
        "byte_size": row[6],
        "storage_key": row[7],
        "metadata": row[8],
        "body": body,
    }


def _manifest_sha(pages: Sequence[_NormalizedPage]) -> str:
    value = "\n".join(
        f"{page.evidence.ordinal}:{page.evidence.asset_id}:{page.evidence.sha256}:"
        f"{hashlib.sha256(_normalize_text(page.evidence.exact_text).encode('utf-8')).hexdigest()}"
        for page in pages
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_text(value: str) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _markdown_inline(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().replace("#", "\\#")
