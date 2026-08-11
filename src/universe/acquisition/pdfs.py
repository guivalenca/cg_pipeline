"""Structural PDF parsing with immutable page evidence and figure placement."""

from __future__ import annotations

import base64
import hashlib
import io
import ipaddress
import json
import os
import re
import socket
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import unquote, urljoin, urlsplit

import httpx
import psycopg
from PIL import Image, UnidentifiedImageError
from psycopg.types.json import Jsonb

from universe.acquisition.source_images import SourceImageInput
from universe.acquisition.pdf_figure_recovery import (
    PDF_FIGURE_PROMPT_REF,
    PdfDownloadedImage,
    PdfFigureLocalizationResult,
    PdfFigureRegion,
    default_pdf_figure_locator,
    place_pdf_figures,
)
from universe.assets import AssetStore
from universe.settings import (
    firecrawl_api_key,
    private_pdf_figure_localization_enabled,
)


PDF_PAGE_TOOL = "pdf-document-association"
PDF_PAGE_TOOL_VERSION = "firecrawl-pdf.v1"
PDF_TEXT_TOOL = "firecrawl-parse"
PDF_TEXT_TOOL_VERSION = "firecrawl-v2-parse.v1"
PDF_RENDER_TOOL_VERSION = "pdftoppm-png-144dpi.v1"
DERIVED_PAGE_ORDINAL_BASE = 1_000_000
MAX_PDF_FIGURE_BYTES = 10 * 1024 * 1024
MAX_PDF_FIGURE_REDIRECTS = 4
FIRECRAWL_PARSE_URL = "https://api.firecrawl.dev/v2/parse"
FIRECRAWL_PARSE_RETRY_SECONDS = (2.0, 6.0, 18.0)
FIRECRAWL_PARSE_RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}
FIGURE_CAPTION = re.compile(
    r"(?im)^\s*(?:fig(?:ure|ura)?\.?|diagram(?:a)?|chart|gr[aá]fico)\s*\d+"
)


@dataclass(frozen=True)
class PdfPage:
    page_number: int
    text: str
    render_body: bytes
    width: int
    height: int
    render_mime_type: str = "image/png"
    figure_caption_top_1000: int | None = None
    text_lines_1000: tuple[tuple[str, int, int, int, int], ...] = ()
    render_asset_id: str | None = None


@dataclass(frozen=True)
class PdfAcquisitionResult:
    raw_markdown: str
    enriched_markdown: str
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class PdfParseResult:
    markdown: str
    image_urls: tuple[str, ...]
    attempts: int
    diagnostics: dict[str, Any]


class PdfExtractionError(RuntimeError):
    def __init__(self, code: str, category: str):
        self.code = code
        self.category = category
        super().__init__(code)


def _private_pdf_export_enabled() -> bool:
    return os.environ.get("FIRECRAWL_ALLOW_PRIVATE_PDF_UPLOADS", "").strip() == "1"


def _ordered_image_urls(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        url = item.strip()
        if url and url not in seen:
            result.append(url)
            seen.add(url)
    return tuple(result)


def parse_pdf_with_firecrawl(
    body: bytes,
    filename: str,
    mime_type: str,
    *,
    mode: str = "auto",
) -> PdfParseResult:
    """Parse a private PDF only after the deployment explicitly enables export."""
    if not _private_pdf_export_enabled():
        raise PdfExtractionError(
            "private_pdf_export_disabled", "external_document_export_disabled"
        )
    api_key = firecrawl_api_key()
    if not api_key:
        raise PdfExtractionError("missing_credentials", "configuration")
    if not body or mime_type != "application/pdf":
        raise PdfExtractionError("manual_pdf_extraction_failed", "invalid_pdf_body")

    if mode not in {"auto", "ocr", "fast"}:
        raise ValueError("unsupported Firecrawl PDF mode")
    options = {
        "formats": ["markdown", "images"],
        "onlyMainContent": True,
        "timeout": 300_000,
        "parsers": [{"type": "pdf", "mode": mode}],
        "removeBase64Images": False,
    }
    for attempt in range(len(FIRECRAWL_PARSE_RETRY_SECONDS) + 1):
        try:
            response = httpx.post(
                FIRECRAWL_PARSE_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, body, mime_type)},
                data={"options": json.dumps(options, separators=(",", ":"))},
                timeout=315.0,
            )
        except httpx.TransportError as exc:
            if attempt < len(FIRECRAWL_PARSE_RETRY_SECONDS):
                time.sleep(FIRECRAWL_PARSE_RETRY_SECONDS[attempt])
                continue
            raise PdfExtractionError(
                "pdf_parse_failed", "firecrawl_transport_error"
            ) from exc
        if response.status_code in FIRECRAWL_PARSE_RETRYABLE_STATUSES:
            if attempt < len(FIRECRAWL_PARSE_RETRY_SECONDS):
                time.sleep(FIRECRAWL_PARSE_RETRY_SECONDS[attempt])
                continue
            raise PdfExtractionError("pdf_parse_failed", "firecrawl_retries_exhausted")
        if response.status_code != 200:
            categories = {
                401: "provider_authentication",
                402: "insufficient_credits",
                413: "payload_too_large",
                429: "rate_limited",
            }
            raise PdfExtractionError(
                "pdf_parse_failed",
                categories.get(response.status_code, "firecrawl_provider_error"),
            )
        try:
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("success") is False:
                raise KeyError("unsuccessful response")
            data = payload["data"]
            if not isinstance(data, dict):
                raise KeyError("invalid data")
            markdown = data["markdown"]
            metadata = data.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            if not isinstance(markdown, str) or not markdown.strip():
                raise KeyError("empty markdown")
        except (TypeError, ValueError, KeyError) as exc:
            raise PdfExtractionError(
                "pdf_parse_failed", "invalid_provider_response"
            ) from exc
        image_urls = _ordered_image_urls(data.get("images"))
        num_pages = metadata.get("numPages")
        total_pages = metadata.get("totalPages")
        diagnostics = {
            "category": "success",
            "http_status": 200,
            "markdown_chars": len(markdown),
            "image_count": len(image_urls),
            **({"num_pages": num_pages} if isinstance(num_pages, int) else {}),
            **({"total_pages": total_pages} if isinstance(total_pages, int) else {}),
        }
        if isinstance(num_pages, int):
            diagnostics["estimated_credits"] = num_pages
        return PdfParseResult(
            markdown.rstrip() + "\n",
            image_urls,
            attempt + 1,
            diagnostics,
        )
    raise AssertionError("Firecrawl retry loop terminated unexpectedly")


def _public_image_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    hostname = parsed.hostname.casefold().rstrip(".")
    if hostname == "localhost" or hostname.endswith((".localhost", ".local")):
        return False
    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        }
    except (socket.gaierror, ValueError):
        return False
    return bool(addresses) and all(
        not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        )
        for address in addresses
    )


def _pdf_image_mime(body: bytes) -> str | None:
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp"
    return None


def _validated_pdf_image(body: bytes, final_url: str) -> PdfDownloadedImage:
    if not body or len(body) > MAX_PDF_FIGURE_BYTES:
        raise PdfExtractionError("pdf_image_download_failed", "invalid_image_size")
    mime_type = _pdf_image_mime(body)
    if mime_type is None:
        raise PdfExtractionError("pdf_image_download_failed", "invalid_image_type")
    try:
        with Image.open(io.BytesIO(body)) as image:
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise PdfExtractionError(
            "pdf_image_download_failed", "invalid_image_body"
        ) from exc
    if width < 1 or height < 1 or width * height > 40_000_000:
        raise PdfExtractionError("pdf_image_download_failed", "invalid_image_dimensions")
    suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[
        mime_type
    ]
    name = unquote(Path(urlsplit(final_url).path).name).strip()
    name = re.sub(r"[\x00-\x1f\x7f/]", "-", name)[:220]
    if not name or name in {".", ".."}:
        name = f"pdf-figure{suffix}"
    elif not Path(name).suffix:
        name += suffix
    return PdfDownloadedImage(
        body=body,
        mime_type=mime_type,
        filename=name,
        final_url=final_url,
        width=width,
        height=height,
        sha256=hashlib.sha256(body).hexdigest(),
    )


def download_pdf_image(url: str) -> PdfDownloadedImage:
    """Resolve one Firecrawl figure immediately, before any signed URL expires."""
    if url.startswith("data:image/"):
        match = re.fullmatch(
            r"data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=\r\n]+)", url
        )
        if match is None:
            raise PdfExtractionError("pdf_image_download_failed", "invalid_data_url")
        try:
            encoded = re.sub(r"\s+", "", match.group(2))
            body = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise PdfExtractionError(
                "pdf_image_download_failed", "invalid_data_url"
            ) from exc
        suffix = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
        }[match.group(1)]
        image = _validated_pdf_image(body, f"embedded{suffix}")
        if image.mime_type != match.group(1):
            raise PdfExtractionError(
                "pdf_image_download_failed", "invalid_image_type"
            )
        return image

    current = url
    with httpx.Client(follow_redirects=False, timeout=30.0) as client:
        for redirect_count in range(MAX_PDF_FIGURE_REDIRECTS + 1):
            if not _public_image_url(current):
                raise PdfExtractionError(
                    "pdf_image_download_failed", "invalid_image_url"
                )
            try:
                with client.stream(
                    "GET",
                    current,
                    headers={
                        "User-Agent": "ConceptUniversePdfAcquisition/1.0",
                        "Accept": "image/*",
                    },
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location or redirect_count >= MAX_PDF_FIGURE_REDIRECTS:
                            raise PdfExtractionError(
                                "pdf_image_download_failed", "invalid_image_redirect"
                            )
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise PdfExtractionError(
                            "pdf_image_download_failed", "image_http_error"
                        )
                    declared = response.headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > MAX_PDF_FIGURE_BYTES:
                        raise PdfExtractionError(
                            "pdf_image_download_failed", "invalid_image_size"
                        )
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_PDF_FIGURE_BYTES:
                            raise PdfExtractionError(
                                "pdf_image_download_failed", "invalid_image_size"
                            )
                        chunks.append(chunk)
                    return _validated_pdf_image(b"".join(chunks), current)
            except PdfExtractionError:
                raise
            except httpx.TransportError as exc:
                raise PdfExtractionError(
                    "pdf_image_download_failed", "image_transport_error"
                ) from exc
    raise PdfExtractionError("pdf_image_download_failed", "invalid_image_redirect")


def _figure_caption_tops_from_bbox_xml(
    body: bytes, page_count: int
) -> list[int | None]:
    """Return the normalized top edge of the first figure caption on each page."""
    tops: list[int | None] = [None] * page_count
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return tops
    pages = [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "page"
    ]
    for index, page in enumerate(pages[:page_count]):
        try:
            page_height = float(page.attrib["height"])
        except (KeyError, TypeError, ValueError):
            continue
        if page_height <= 0:
            continue
        for line in page.iter():
            if line.tag.rsplit("}", 1)[-1] != "line":
                continue
            words = [
                str(word.text or "").strip()
                for word in line
                if word.tag.rsplit("}", 1)[-1] == "word"
            ]
            text = " ".join(word for word in words if word)
            if not FIGURE_CAPTION.search(text):
                continue
            try:
                normalized = round(float(line.attrib["yMin"]) / page_height * 1000)
            except (KeyError, TypeError, ValueError):
                continue
            tops[index] = min(1000, max(0, normalized))
            break
    return tops


def _text_lines_from_bbox_xml(
    body: bytes, page_count: int
) -> list[tuple[tuple[str, int, int, int, int], ...]]:
    """Return Poppler text lines as normalized text/box tuples per page."""
    result: list[tuple[tuple[str, int, int, int, int], ...]] = [()] * page_count
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return result
    pages = [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "page"
    ]
    for index, page in enumerate(pages[:page_count]):
        try:
            page_width = float(page.attrib["width"])
            page_height = float(page.attrib["height"])
        except (KeyError, TypeError, ValueError):
            continue
        if page_width <= 0 or page_height <= 0:
            continue
        lines: list[tuple[str, int, int, int, int]] = []
        for line in page.iter():
            if line.tag.rsplit("}", 1)[-1] != "line":
                continue
            words = [
                str(word.text or "").strip()
                for word in line
                if word.tag.rsplit("}", 1)[-1] == "word"
            ]
            text = " ".join(word for word in words if word)
            if not text:
                continue
            try:
                box = (
                    round(float(line.attrib["xMin"]) / page_width * 1000),
                    round(float(line.attrib["yMin"]) / page_height * 1000),
                    round(float(line.attrib["xMax"]) / page_width * 1000),
                    round(float(line.attrib["yMax"]) / page_height * 1000),
                )
            except (KeyError, TypeError, ValueError):
                continue
            left, top, right, bottom = box
            lines.append(
                (
                    text,
                    min(1000, max(0, left)),
                    min(1000, max(0, top)),
                    min(1000, max(0, right)),
                    min(1000, max(0, bottom)),
                )
            )
        result[index] = tuple(lines)
    return result


def extract_pdf_pages_with_poppler(body: bytes) -> list[PdfPage]:
    """Extract every text layer once and render every page at a stable resolution."""
    if not isinstance(body, bytes) or not body:
        raise PdfExtractionError("manual_pdf_extraction_failed", "invalid_pdf_body")
    try:
        with tempfile.TemporaryDirectory(prefix="universe-pdf-") as directory:
            root = Path(directory)
            pdf_path = root / "source.pdf"
            pdf_path.write_bytes(body)
            info = subprocess.run(
                ["pdfinfo", str(pdf_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=120,
            )
            if info.returncode != 0:
                raise PdfExtractionError(
                    "manual_pdf_extraction_failed", "pdf_info_failed"
                )
            match = re.search(
                r"^Pages:\s+(\d+)\s*$", info.stdout.decode("utf-8", "replace"), re.M
            )
            if match is None or int(match.group(1)) < 1:
                raise PdfExtractionError(
                    "manual_pdf_extraction_failed", "pdf_page_count_missing"
                )
            page_count = int(match.group(1))
            text_result = subprocess.run(
                ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=120,
            )
            if text_result.returncode != 0:
                raise PdfExtractionError(
                    "manual_pdf_extraction_failed", "pdf_text_extraction_failed"
                )
            text_pages = text_result.stdout.decode("utf-8", "replace").split("\f")
            if len(text_pages) > page_count and not text_pages[-1].strip():
                text_pages.pop()
            text_pages = (text_pages + [""] * page_count)[:page_count]

            bbox_result = subprocess.run(
                [
                    "pdftotext",
                    "-bbox-layout",
                    "-enc",
                    "UTF-8",
                    str(pdf_path),
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=120,
            )
            caption_tops = (
                _figure_caption_tops_from_bbox_xml(bbox_result.stdout, page_count)
                if bbox_result.returncode == 0
                else [None] * page_count
            )
            text_lines = (
                _text_lines_from_bbox_xml(bbox_result.stdout, page_count)
                if bbox_result.returncode == 0
                else [()] * page_count
            )

            prefix = root / "page"
            render = subprocess.run(
                ["pdftoppm", "-png", "-r", "144", str(pdf_path), str(prefix)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=300,
            )
            if render.returncode != 0:
                raise PdfExtractionError(
                    "manual_pdf_render_failed", "pdf_page_render_failed"
                )
            rendered = sorted(root.glob("page-*.png"))
            if len(rendered) != page_count:
                raise PdfExtractionError(
                    "manual_pdf_render_failed", "pdf_page_render_count_mismatch"
                )
            pages: list[PdfPage] = []
            for number, path in enumerate(rendered, start=1):
                render_body = path.read_bytes()
                with Image.open(path) as image:
                    width, height = image.size
                pages.append(
                    PdfPage(
                        page_number=number,
                        text=_normalize_text_layer(text_pages[number - 1]),
                        render_body=render_body,
                        width=width,
                        height=height,
                        figure_caption_top_1000=caption_tops[number - 1],
                        text_lines_1000=text_lines[number - 1],
                    )
                )
            return pages
    except FileNotFoundError as exc:
        raise PdfExtractionError(
            "manual_pdf_extractor_missing", "pdf_extractor_unavailable"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise PdfExtractionError(
            "manual_pdf_extraction_failed", "pdf_extraction_timeout"
        ) from exc


def _normalize_text_layer(text: str) -> str:
    return (
        str(text)
        .replace("\x00", "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\f", "")
        .strip()
    )


def _page_id(job_id: str, pdf_asset_id: str, page_number: int) -> str:
    digest = hashlib.sha256(
        f"{job_id}:{pdf_asset_id}:{page_number}".encode("utf-8")
    ).hexdigest()[:32]
    return f"pdf-page-{digest}"


def _render_asset_id(page_id: str, digest: str) -> str:
    identity = hashlib.sha256(f"{page_id}:{digest}".encode()).hexdigest()[:32]
    return f"asset-pdf-page-{identity}"


def _persist_pages(
    conn: psycopg.Connection,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    pages: Sequence[PdfPage],
    store: AssetStore,
) -> list[dict[str, Any]]:
    expected = list(range(1, len(pages) + 1))
    if [page.page_number for page in pages] != expected:
        raise PdfExtractionError(
            "manual_pdf_extraction_failed", "pdf_page_order_invalid"
        )
    persisted: list[dict[str, Any]] = []
    for page in pages:
        if page.render_mime_type != "image/png" or not page.render_body:
            raise PdfExtractionError(
                "manual_pdf_render_failed", "pdf_page_render_invalid"
            )
        render_sha = hashlib.sha256(page.render_body).hexdigest()
        page_id = _page_id(str(job["id"]), str(pdf_asset["id"]), page.page_number)
        if page.render_asset_id:
            render_asset_id = page.render_asset_id
            asset_row = conn.execute(
                "SELECT sha256, storage_key, mime_type, metadata"
                " FROM source_asset WHERE id = %s AND acquisition_job_id = %s"
                " AND source_id = %s",
                (render_asset_id, job["id"], job["source_id"]),
            ).fetchone()
            if (
                asset_row is None
                or asset_row[0] != render_sha
                or asset_row[2] != "image/png"
            ):
                raise PdfExtractionError(
                    "manual_pdf_render_failed", "ordered_page_asset_mismatch"
                )
        else:
            stored = store.put(page.render_body, sha256=render_sha)
            render_asset_id = _render_asset_id(page_id, render_sha)
            metadata = {
                "page_number": page.page_number,
                "pdf_asset_id": pdf_asset["id"],
                "derived_by": PDF_RENDER_TOOL_VERSION,
                "width": page.width,
                "height": page.height,
            }
            if page.figure_caption_top_1000 is not None:
                metadata["figure_caption_top_1000"] = page.figure_caption_top_1000
            conn.execute(
                "INSERT INTO source_asset"
                " (id, acquisition_job_id, source_id, ordinal, kind, filename,"
                " mime_type, sha256, byte_size, storage_key, metadata)"
                " VALUES (%s, %s, %s, %s, 'pdf_page', %s, 'image/png', %s, %s, %s, %s)"
                " ON CONFLICT (id) DO NOTHING",
                (
                    render_asset_id,
                    job["id"],
                    job["source_id"],
                    DERIVED_PAGE_ORDINAL_BASE + page.page_number,
                    f"{Path(str(pdf_asset['filename'])).stem}-page-{page.page_number:04d}.png",
                    render_sha,
                    len(page.render_body),
                    stored.key,
                    Jsonb(metadata),
                ),
            )
        text = _normalize_text_layer(page.text)
        text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        conn.execute(
            "INSERT INTO source_pdf_page"
            " (id, acquisition_job_id, source_id, pdf_asset_id, page_number,"
            " text_body, text_sha256, text_layer_status, render_asset_id)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (id) DO NOTHING",
            (
                page_id,
                job["id"],
                job["source_id"],
                pdf_asset["id"],
                page.page_number,
                text,
                text_sha,
                "usable" if text.strip() else "empty",
                render_asset_id,
            ),
        )
        row = conn.execute(
            "SELECT p.id, p.page_number, p.text_body, p.text_layer_status,"
            " p.render_asset_id, a.sha256, a.storage_key, a.mime_type, a.metadata"
            " FROM source_pdf_page p JOIN source_asset a ON a.id = p.render_asset_id"
            " WHERE p.id = %s",
            (page_id,),
        ).fetchone()
        if row is None or row[1:5] != (
            page.page_number,
            text,
            "usable" if text.strip() else "empty",
            render_asset_id,
        ):
            raise RuntimeError("persisted PDF page does not match deterministic input")
        persisted.append(
            dict(
                zip(
                    (
                        "id",
                        "page_number",
                        "text_body",
                        "text_layer_status",
                        "render_asset_id",
                        "sha256",
                        "storage_key",
                        "mime_type",
                        "metadata",
                    ),
                    row,
                )
            )
        )
        persisted[-1]["figure_caption_top_1000"] = page.figure_caption_top_1000
        persisted[-1]["text_lines_1000"] = page.text_lines_1000
    conn.commit()
    return persisted


def _parsed_markdown(
    title: str,
    pdf_asset_id: str,
    parsed: str,
    *,
    source_link_label: str | None,
) -> str:
    parts = [f"# {title}"]
    if source_link_label:
        parts.append(f"[{source_link_label}](/api/source-assets/{pdf_asset_id})")
    parts.append(parsed.strip())
    return "\n\n".join(parts).rstrip() + "\n"


def _document_parse_call_id(job_id: str, pdf_asset_id: str) -> str:
    digest = hashlib.sha256(
        f"{job_id}:{pdf_asset_id}:{PDF_TEXT_TOOL_VERSION}".encode("utf-8")
    ).hexdigest()[:32]
    return f"pdf-parse-{digest}"


def _parse_document_once(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    parser: Callable[[bytes, str, str], PdfParseResult],
    document_mode: str,
) -> tuple[PdfParseResult, dict[str, Any]]:
    call_id = _document_parse_call_id(str(job["id"]), str(pdf_asset["id"]))
    options = {
        "formats": ["markdown", "images"],
        "pdf_mode": document_mode,
        "only_main_content": True,
    }
    conn.execute(
        "INSERT INTO pdf_document_parse_call"
        " (id, acquisition_job_id, pdf_asset_id, parser_ref, input_sha256,"
        " options, status) VALUES (%s, %s, %s, %s, %s, %s, 'queued')"
        " ON CONFLICT (id) DO NOTHING",
        (
            call_id,
            job["id"],
            pdf_asset["id"],
            PDF_TEXT_TOOL_VERSION,
            pdf_asset["sha256"],
            Jsonb(options),
        ),
    )
    row = conn.execute(
        "SELECT parser_ref, input_sha256, options, status, attempt_count,"
        " provider_attempts, result, failure_code, diagnostics"
        " FROM pdf_document_parse_call WHERE id = %s",
        (call_id,),
    ).fetchone()
    conn.commit()
    if row is None:
        raise RuntimeError("PDF parse call was not persisted")
    parser_ref, input_sha256, stored_options = row[:3]
    if (
        parser_ref != PDF_TEXT_TOOL_VERSION
        or input_sha256 != pdf_asset["sha256"]
        or dict(stored_options or {}) != options
    ):
        raise PdfExtractionError(
            "pdf_parse_configuration_conflict", "durable_parse_input_conflict"
        )
    status, attempt_count, provider_attempts, result, failure_code, diagnostics = row[3:]
    if status == "succeeded":
        payload = result or {}
        parsed = PdfParseResult(
            markdown=str(payload["markdown"]),
            image_urls=tuple(payload.get("image_urls") or ()),
            attempts=int(provider_attempts),
            diagnostics=dict(payload.get("diagnostics") or {}),
        )
        return parsed, {
            "id": call_id,
            "status": "succeeded",
            "attempt_count": attempt_count,
            "provider_attempts": provider_attempts,
            "reused": True,
        }
    if status == "failed":
        raise PdfExtractionError(
            str(failure_code or "pdf_parse_failed"),
            str((diagnostics or {}).get("category") or "pdf_parse_failed"),
        )
    claimed = conn.execute(
        "UPDATE pdf_document_parse_call SET status = 'running',"
        " attempt_count = attempt_count + 1, updated_at = now()"
        " WHERE id = %s AND status = 'queued' RETURNING attempt_count",
        (call_id,),
    ).fetchone()
    conn.commit()
    if claimed is None:
        raise RuntimeError("PDF parse call is already running")
    try:
        parsed = parser(
            bytes(pdf_asset["body"]),
            str(pdf_asset["filename"]),
            str(pdf_asset["mime_type"]),
        )
        result_payload = {
            "markdown": parsed.markdown,
            "image_urls": list(parsed.image_urls),
            "diagnostics": parsed.diagnostics,
        }
        conn.execute(
            "UPDATE pdf_document_parse_call SET status = 'succeeded',"
            " provider_attempts = %s, result = %s, diagnostics = %s,"
            " finished_at = now(), updated_at = now()"
            " WHERE id = %s AND status = 'running'",
            (
                parsed.attempts,
                Jsonb(result_payload),
                Jsonb(dict(parsed.diagnostics)),
                call_id,
            ),
        )
        conn.commit()
        return parsed, {
            "id": call_id,
            "status": "succeeded",
            "attempt_count": int(claimed[0]),
            "provider_attempts": parsed.attempts,
            "reused": False,
        }
    except PdfExtractionError as exc:
        conn.rollback()
        conn.execute(
            "UPDATE pdf_document_parse_call SET status = 'failed',"
            " failure_code = %s, diagnostics = %s, finished_at = now(),"
            " updated_at = now() WHERE id = %s AND status = 'running'",
            (exc.code, Jsonb({"category": exc.category}), call_id),
        )
        conn.commit()
        raise
    except Exception as exc:
        conn.rollback()
        conn.execute(
            "UPDATE pdf_document_parse_call SET status = 'failed',"
            " failure_code = 'pdf_parse_failed', diagnostics = %s,"
            " finished_at = now(), updated_at = now()"
            " WHERE id = %s AND status = 'running'",
            (
                Jsonb(
                    {
                        "category": "pdf_parse_adapter_error",
                        "exception": type(exc).__name__,
                    }
                ),
                call_id,
            ),
        )
        conn.commit()
        raise


def acquire_pdf_document(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    title: str,
    pdf_asset: Mapping[str, Any],
    asset_store: AssetStore,
    document_parser: Callable[[bytes, str, str], PdfParseResult] = parse_pdf_with_firecrawl,
    image_downloader: Callable[[str], PdfDownloadedImage] = download_pdf_image,
    figure_locator: Callable[
        [str, list[SourceImageInput]], PdfFigureLocalizationResult
    ]
    | None = None,
    page_extractor: Callable[[bytes], Sequence[PdfPage]] = extract_pdf_pages_with_poppler,
    document_mode: str = "auto",
    input_mode: str = "pdf",
    evidence_asset_ids: Sequence[str] | None = None,
    source_link_label: str | None = "Open original PDF",
    render_tool: str = "pdftoppm",
    render_tool_version: str = PDF_RENDER_TOOL_VERSION,
) -> PdfAcquisitionResult:
    if document_mode not in {"auto", "ocr", "fast"}:
        raise ValueError("unsupported PDF document mode")
    pdf_body = bytes(pdf_asset["body"])
    parsed, parse_call = _parse_document_once(
        conn,
        job=job,
        pdf_asset=pdf_asset,
        parser=document_parser,
        document_mode=document_mode,
    )
    pages = list(page_extractor(pdf_body))
    if not pages:
        raise PdfExtractionError("manual_pdf_extraction_failed", "pdf_has_no_pages")
    persisted = _persist_pages(conn, job, pdf_asset, pages, asset_store)
    raw = _parsed_markdown(
        title,
        str(pdf_asset["id"]),
        parsed.markdown,
        source_link_label=source_link_label,
    )
    effective_locator = figure_locator
    if effective_locator is None and private_pdf_figure_localization_enabled():
        effective_locator = default_pdf_figure_locator
    placement = place_pdf_figures(
        conn,
        job=job,
        pdf_asset=pdf_asset,
        pages=persisted,
        markdown=parsed.markdown,
        reported_urls=parsed.image_urls,
        asset_store=asset_store,
        image_downloader=image_downloader,
        locator=effective_locator,
    )
    figures = list(placement.figures)
    calls = list(placement.calls)
    image_failures = list(placement.failures)
    enriched = _parsed_markdown(
        title,
        str(pdf_asset["id"]),
        placement.markdown,
        source_link_label=source_link_label,
    )
    usage: dict[str, int | float] = {}
    estimated_credits = parsed.diagnostics.get("estimated_credits")
    if isinstance(estimated_credits, (int, float)):
        usage["firecrawl_credits_estimated"] = estimated_credits
    for call in calls:
        for key, value in dict(call.get("usage") or {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[key] = usage.get(key, 0) + value
    diagnostics = {
        "input_mode": input_mode,
        "asset_count": len(evidence_asset_ids or (pdf_asset["id"],)),
        "asset_ids": list(evidence_asset_ids or (pdf_asset["id"],)),
        "page_asset_ids": [page["render_asset_id"] for page in persisted],
        "figure_asset_ids": [figure["id"] for figure in figures],
        "page_count": len(persisted),
        "text_layer_pages": sum(page["text_layer_status"] == "usable" for page in persisted),
        "scanned_pages": sum(page["text_layer_status"] == "empty" for page in persisted),
        "extractor": {
            "document_tool": PDF_TEXT_TOOL,
            "document_tool_version": PDF_TEXT_TOOL_VERSION,
            "document_mode": document_mode,
            "render_tool": render_tool,
            "render_tool_version": render_tool_version,
        },
        "document_parse": {
            **parsed.diagnostics,
            "attempts": parsed.attempts,
            "image_urls_returned": len(parsed.image_urls),
            "extracted_image_count": len(figures),
            "image_failures": image_failures,
            **parse_call,
        },
        "prompt_version": None,
        "visual_calls": calls,
        "usage": usage,
        "pages": [
            {
                "page_id": page["id"],
                "page_number": page["page_number"],
                "render_asset_id": page["render_asset_id"],
                "text_layer_status": page["text_layer_status"],
                "publication_role": "audit_only",
            }
            for page in persisted
        ],
        "visual_incomplete": bool(image_failures),
        "pipeline_requires_cleanup": True,
        "tool_version": PDF_PAGE_TOOL_VERSION,
    }
    return PdfAcquisitionResult(raw, enriched, diagnostics)
