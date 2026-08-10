"""Page-aware PDF acquisition using immutable renders and grouped vision calls."""

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

from universe.acquisition.source_images import (
    SourceImageAnalysis,
    SourceImageBatchResult,
    SourceImageInput,
    analyze_source_images,
    input_manifest_hash,
)
from universe.acquisition.article_images import extract_markdown_images
from universe.assets import AssetStore
from universe.model_client import ModelClient
from universe.settings import (
    article_image_model,
    firecrawl_api_key,
    openrouter_multimodal_provider_routing,
    private_pdf_figure_localization_enabled,
)


PDF_PAGE_TOOL = "pdf-document-association"
PDF_PAGE_TOOL_VERSION = "firecrawl-pdf.v1"
PDF_TEXT_TOOL = "firecrawl-parse"
PDF_TEXT_TOOL_VERSION = "firecrawl-v2-parse.v1"
PDF_RENDER_TOOL_VERSION = "pdftoppm-png-144dpi.v1"
PDF_PROMPT_REF = "pdf-page-analysis/v002"
PDF_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "pdf-page-analysis" / "v002.md"
PDF_FIGURE_PROMPT_REF = "pdf-figure-localization/v002"
PDF_FIGURE_PROMPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "prompts"
    / "pdf-figure-localization"
    / "v002.md"
)
MAX_MULTIMODAL_REQUEST_BYTES = 18 * 1024 * 1024
MAX_MULTIMODAL_CONTEXT_CHARS = 80_000
DERIVED_PAGE_ORDINAL_BASE = 1_000_000
DERIVED_FIGURE_ORDINAL_BASE = 2_000_000
MAX_PDF_FIGURE_BYTES = 10 * 1024 * 1024
MAX_PDF_FIGURE_REDIRECTS = 4
FIRECRAWL_PARSE_URL = "https://api.firecrawl.dev/v2/parse"
FIRECRAWL_PARSE_RETRY_SECONDS = (2.0, 6.0, 18.0)
FIRECRAWL_PARSE_RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}
FIGURE_CAPTION = re.compile(
    r"(?im)^\s*(?:fig(?:ure|ura)?\.?|diagram(?:a)?|chart|gr[aá]fico)\s*\d+"
)
PDF_FIGURE_TOOL = {
    "type": "function",
    "function": {
        "name": "locate_pdf_figures",
        "description": "Locate informative non-table figures on rendered PDF pages.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "regions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "page_id": {"type": "string"},
                            "bbox": {
                                "type": "object",
                                "description": (
                                    "Named normalized coordinates enclosing the entire connected "
                                    "visual. The origin is the full page's top-left corner."
                                ),
                                "properties": {
                                    "left": {"type": "integer", "minimum": 0, "maximum": 1000},
                                    "top": {"type": "integer", "minimum": 0, "maximum": 1000},
                                    "right": {"type": "integer", "minimum": 0, "maximum": 1000},
                                    "bottom": {"type": "integer", "minimum": 0, "maximum": 1000},
                                },
                                "required": ["left", "top", "right", "bottom"],
                                "additionalProperties": False,
                            },
                            "description": {"type": "string"},
                            "visible_text": {"type": "string"},
                        },
                        "required": [
                            "page_id",
                            "bbox",
                            "description",
                            "visible_text",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["regions"],
            "additionalProperties": False,
        },
    },
}


@dataclass(frozen=True)
class PdfPage:
    page_number: int
    text: str
    render_body: bytes
    width: int
    height: int
    render_mime_type: str = "image/png"
    figure_caption_top_1000: int | None = None


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


@dataclass(frozen=True)
class PdfDownloadedImage:
    body: bytes
    mime_type: str
    filename: str
    final_url: str
    width: int
    height: int
    sha256: str


@dataclass(frozen=True)
class PdfFigureRegion:
    page_id: str
    bbox: tuple[int, int, int, int]
    description: str
    visible_text: str


@dataclass(frozen=True)
class PdfFigureLocalizationResult:
    regions: tuple[PdfFigureRegion, ...]
    requested_model: str
    response_model: str | None
    provider: str
    usage: dict[str, Any]
    duration_ms: int


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
    body: bytes, filename: str, mime_type: str
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

    options = {
        "formats": ["markdown", "images"],
        "onlyMainContent": True,
        "timeout": 300_000,
        "parsers": [{"type": "pdf", "mode": "auto"}],
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


def pdf_prompt_stamp() -> tuple[str, str, str]:
    raw = PDF_PROMPT_PATH.read_bytes()
    return PDF_PROMPT_REF, hashlib.sha256(raw).hexdigest(), raw.decode("utf-8")


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


def _complete_figure_bbox(
    bbox: tuple[int, int, int, int], *, caption_top_1000: int | None
) -> tuple[int, int, int, int]:
    """Extend a partial crop to the whitespace immediately before a lower caption."""
    if caption_top_1000 is None:
        return bbox
    left, top, right, bottom = bbox
    safe_bottom = max(top + 1, caption_top_1000 - 10)
    if safe_bottom <= bottom:
        return bbox
    return (left, top, right, min(1000, safe_bottom))


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


def _analysis_id(call_id: str, page_id: str) -> str:
    digest = hashlib.sha256(f"{call_id}:{page_id}".encode()).hexdigest()[:32]
    return f"analysis-pdf-page-{digest}"


def _call_id(job_id: str, ordinal: int, prompt_sha: str) -> str:
    digest = hashlib.sha256(
        f"{job_id}:{ordinal}:{prompt_sha}".encode("utf-8")
    ).hexdigest()[:32]
    return f"pdf-call-{digest}"


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
        stored = store.put(page.render_body, sha256=render_sha)
        page_id = _page_id(str(job["id"]), str(pdf_asset["id"]), page.page_number)
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
    conn.commit()
    return persisted


def _batch_weight(page: Mapping[str, Any], body: bytes) -> tuple[int, int]:
    encoded_bytes = ((len(body) + 2) // 3) * 4
    return encoded_bytes, len(str(page["text_body"]))


def pdf_page_batches(
    pages: Sequence[Mapping[str, Any]], render_bodies: Mapping[str, bytes]
) -> list[list[Mapping[str, Any]]]:
    """Group only for request byte/context limits; no semantic page cap exists."""
    batches: list[list[Mapping[str, Any]]] = []
    current: list[Mapping[str, Any]] = []
    byte_total = 0
    text_total = 0
    for page in pages:
        body = render_bodies[str(page["id"])]
        page_bytes, page_text = _batch_weight(page, body)
        if current and (
            byte_total + page_bytes > MAX_MULTIMODAL_REQUEST_BYTES
            or text_total + page_text > MAX_MULTIMODAL_CONTEXT_CHARS
        ):
            batches.append(current)
            current = []
            byte_total = 0
            text_total = 0
        current.append(page)
        byte_total += page_bytes
        text_total += page_text
    if current:
        batches.append(current)
    return batches


def _context_for_pages(pages: Sequence[Mapping[str, Any]]) -> str:
    sections = ["# Extracted PDF page text"]
    for page in pages:
        text = str(page["text_body"]).strip() or "(no extractable text layer)"
        sections.append(
            f"## Page {page['page_number']}\n"
            f"page_id: {page['id']}\n"
            f"text_layer_status: {page['text_layer_status']}\n\n{text}"
        )
    return "\n\n".join(sections).rstrip() + "\n"


def default_pdf_page_analyzer(
    context: str, images: list[SourceImageInput]
) -> SourceImageBatchResult:
    client = ModelClient(
        article_image_model(),
        temperature=0,
        max_tokens=65_536,
        extra={"provider": openrouter_multimodal_provider_routing()},
    )
    return analyze_source_images(
        context, images, client=client, prompt_spec=pdf_prompt_stamp()
    )


def default_pdf_figure_locator(
    context: str, images: list[SourceImageInput]
) -> PdfFigureLocalizationResult:
    prompt = PDF_FIGURE_PROMPT_PATH.read_text(encoding="utf-8").strip()
    content: list[dict[str, Any]] = [
        {"type": "text", "text": f"{prompt}\n\n{context}"}
    ]
    for image in images:
        content.extend(
            [
                {
                    "type": "text",
                    "text": f"page_id: {image.image_id}\nlabel: {image.alt_text}",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image.model_image_url, "detail": "high"},
                },
            ]
        )
    client = ModelClient(
        article_image_model(),
        temperature=0,
        max_tokens=16_384,
        extra={"provider": openrouter_multimodal_provider_routing()},
    )
    arguments, raw_usage, duration_ms = client.call_tool(
        [{"role": "user", "content": content}], PDF_FIGURE_TOOL
    )
    valid_page_ids = {image.image_id for image in images}
    raw_regions = arguments.get("regions")
    if not isinstance(raw_regions, list):
        raise ValueError("PDF figure locator returned no regions array")
    regions: list[PdfFigureRegion] = []
    seen: set[tuple[str, tuple[int, int, int, int]]] = set()
    for item in raw_regions:
        if not isinstance(item, dict) or item.get("page_id") not in valid_page_ids:
            raise ValueError("PDF figure locator referenced another page")
        raw_bbox = item.get("bbox")
        if not isinstance(raw_bbox, dict) or set(raw_bbox) != {
            "left",
            "top",
            "right",
            "bottom",
        }:
            raise ValueError("PDF figure locator returned an invalid box")
        bbox = tuple(
            raw_bbox[key] for key in ("left", "top", "right", "bottom")
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) for value in bbox
        ):
            raise ValueError("PDF figure locator returned an invalid box")
        left, top, right, bottom = bbox
        if not (0 <= left < right <= 1000 and 0 <= top < bottom <= 1000):
            raise ValueError("PDF figure locator returned an out-of-range box")
        if (right - left) * (bottom - top) > 850_000:
            raise ValueError("PDF figure locator tried to retain a full page")
        description = str(item.get("description") or "").strip()
        visible_text = str(item.get("visible_text") or "").strip()
        if not description:
            raise ValueError("PDF figure locator omitted its visible description")
        key = (str(item["page_id"]), bbox)
        if key in seen:
            continue
        seen.add(key)
        regions.append(
            PdfFigureRegion(
                page_id=key[0],
                bbox=bbox,
                description=description,
                visible_text=visible_text,
            )
        )
    response_model = raw_usage.get("response_model")
    provider = raw_usage.get("provider") or "openrouter"
    usage = {
        key: value
        for key, value in raw_usage.items()
        if key not in {"provider", "response_model"}
    }
    return PdfFigureLocalizationResult(
        regions=tuple(regions),
        requested_model=client.model,
        response_model=str(response_model) if response_model else None,
        provider=str(provider),
        usage=usage,
        duration_ms=duration_ms,
    )


def _source_inputs(
    pages: Sequence[Mapping[str, Any]], render_bodies: Mapping[str, bytes]
) -> list[SourceImageInput]:
    inputs = []
    for page in pages:
        body = render_bodies[str(page["id"])]
        encoded = base64.b64encode(body).decode("ascii")
        inputs.append(
            SourceImageInput(
                image_id=str(page["id"]),
                alt_text=f"PDF page {page['page_number']}",
                source_url=f"/api/source-assets/{page['render_asset_id']}",
                model_image_url=f"data:image/png;base64,{encoded}",
                asset_sha256=str(page["sha256"]),
                model_input_sha256=hashlib.sha256(body).hexdigest(),
            )
        )
    return inputs


def _insert_page_analysis(
    conn: psycopg.Connection,
    *,
    call_id: str,
    page: Mapping[str, Any],
    batch: SourceImageBatchResult | None,
    analysis: SourceImageAnalysis | None,
    unresolved_reason: str | None,
    failure_exception: str | None,
) -> None:
    failed = unresolved_reason is not None or failure_exception is not None
    if (
        not failed
        and page["text_layer_status"] == "empty"
        and (analysis is None or not analysis.retain or not (analysis.ocr or analysis.description))
    ):
        failed = True
        unresolved_reason = "scanned_page_not_reconstructed"
    result = (
        {
            "retain": analysis.retain,
            "reason_code": analysis.reason_code,
            "ocr": analysis.ocr,
            "description": analysis.description,
            "limitations": analysis.limitations,
        }
        if analysis is not None and not failed
        else {}
    )
    diagnostics = {
        "page_number": page["page_number"],
        **({"reason": unresolved_reason} if unresolved_reason else {}),
        **({"exception": failure_exception} if failure_exception else {}),
    }
    analysis_id = _analysis_id(call_id, str(page["id"]))
    conn.execute(
        "INSERT INTO source_asset_analysis"
        " (id, source_asset_id, purpose, status, prompt_version, requested_model,"
        " response_model, provider, result, usage, duration_ms, failure_code,"
        " diagnostics, pdf_page_id, pdf_analysis_call_id)"
        " VALUES (%s, %s, 'pdf_page_analysis', %s, %s, %s, %s, %s, %s, %s,"
        " %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (
            analysis_id,
            page["render_asset_id"],
            "failed" if failed else "succeeded",
            PDF_PROMPT_REF,
            batch.requested_model if batch else article_image_model(),
            batch.response_model if batch else None,
            batch.provider if batch else None,
            Jsonb(result),
            Jsonb(dict(batch.usage) if batch else {}),
            batch.duration_ms if batch else None,
            "pdf_page_analysis_unresolved" if failed else None,
            Jsonb(diagnostics),
            page["id"],
            call_id,
        ),
    )


def _analyze_batch(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    ordinal: int,
    pages: Sequence[Mapping[str, Any]],
    render_bodies: Mapping[str, bytes],
    analyzer: Callable[[str, list[SourceImageInput]], SourceImageBatchResult],
) -> dict[str, Any]:
    prompt_ref, prompt_sha, _template = pdf_prompt_stamp()
    context = _context_for_pages(pages)
    inputs = _source_inputs(pages, render_bodies)
    manifest_hash = input_manifest_hash(context, inputs)
    call_id = _call_id(str(job["id"]), ordinal, prompt_sha)
    conn.execute(
        "INSERT INTO pdf_page_analysis_call"
        " (id, acquisition_job_id, pdf_asset_id, batch_ordinal, page_ids,"
        " prompt_ref, prompt_sha, requested_model, input_manifest_hash, status)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'queued')"
        " ON CONFLICT (id) DO NOTHING",
        (
            call_id,
            job["id"],
            pdf_asset["id"],
            ordinal,
            Jsonb([page["id"] for page in pages]),
            prompt_ref,
            prompt_sha,
            article_image_model(),
            manifest_hash,
        ),
    )
    row = conn.execute(
        "SELECT status, requested_model, response_model, provider, usage,"
        " duration_ms, failure_code, diagnostics FROM pdf_page_analysis_call"
        " WHERE id = %s",
        (call_id,),
    ).fetchone()
    conn.commit()
    if row is None:
        raise RuntimeError("PDF visual call was not persisted")
    if row[0] in {"succeeded", "failed"}:
        return {
            "id": call_id,
            "status": row[0],
            "requested_model": row[1],
            "response_model": row[2],
            "provider": row[3],
            "usage": row[4] or {},
            "duration_ms": row[5],
            "failure_code": row[6],
            "diagnostics": row[7] or {},
            "reused": True,
        }
    claimed = conn.execute(
        "UPDATE pdf_page_analysis_call SET status = 'running',"
        " attempt_count = attempt_count + 1, updated_at = now()"
        " WHERE id = %s AND status = 'queued' RETURNING id",
        (call_id,),
    ).fetchone()
    conn.commit()
    if claimed is None:
        raise RuntimeError("PDF visual call could not be claimed")
    try:
        batch = analyzer(context, inputs)
        if batch.input_manifest_hash != manifest_hash:
            raise ValueError("PDF visual result manifest does not match the request")
        for page in pages:
            page_id = str(page["id"])
            _insert_page_analysis(
                conn,
                call_id=call_id,
                page=page,
                batch=batch,
                analysis=batch.analyses.get(page_id),
                unresolved_reason=batch.unresolved.get(page_id),
                failure_exception=None,
            )
        conn.execute(
            "UPDATE pdf_page_analysis_call SET status = 'succeeded',"
            " requested_model = %s, response_model = %s, provider = %s, usage = %s,"
            " duration_ms = %s, input_manifest_hash = %s, finished_at = now(),"
            " updated_at = now() WHERE id = %s AND status = 'running'",
            (
                batch.requested_model,
                batch.response_model,
                batch.provider,
                Jsonb(dict(batch.usage)),
                batch.duration_ms,
                batch.input_manifest_hash,
                call_id,
            ),
        )
        conn.commit()
        return {
            "id": call_id,
            "status": "succeeded",
            "requested_model": batch.requested_model,
            "response_model": batch.response_model,
            "provider": batch.provider,
            "usage": dict(batch.usage),
            "duration_ms": batch.duration_ms,
            "failure_code": None,
            "diagnostics": {},
            "reused": False,
        }
    except Exception as exc:
        conn.rollback()
        for page in pages:
            _insert_page_analysis(
                conn,
                call_id=call_id,
                page=page,
                batch=None,
                analysis=None,
                unresolved_reason=None,
                failure_exception=type(exc).__name__,
            )
        diagnostics = {"category": "pdf_page_analysis_failed", "exception": type(exc).__name__}
        conn.execute(
            "UPDATE pdf_page_analysis_call SET status = 'failed',"
            " failure_code = 'pdf_page_analysis_failed', diagnostics = %s,"
            " finished_at = now(), updated_at = now()"
            " WHERE id = %s AND status = 'running'",
            (Jsonb(diagnostics), call_id),
        )
        conn.commit()
        return {
            "id": call_id,
            "status": "failed",
            "requested_model": article_image_model(),
            "response_model": None,
            "provider": None,
            "usage": {},
            "duration_ms": None,
            "failure_code": "pdf_page_analysis_failed",
            "diagnostics": diagnostics,
            "reused": False,
        }


def _is_heading(lines: list[str], joined: str) -> bool:
    if len(lines) > 2 or len(joined) > 100 or joined.endswith((".", ";", ":", "?", "!")):
        return False
    if re.match(r"^\d+(?:\.\d+)*\.?\s+\S", joined):
        return True
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", joined)
    capitalized = sum(word[:1].isupper() for word in words)
    return bool(words) and capitalized >= max(1, (3 * len(words) + 3) // 4)


def text_layer_markdown(text: str) -> str:
    """Turn physical PDF line wraps into readable deterministic paragraphs."""
    normalized = _normalize_text_layer(text)
    if not normalized:
        return ""
    groups = re.split(r"\n\s*\n", normalized)
    rendered: list[str] = []
    for group in groups:
        lines = [re.sub(r"\s+", " ", line).strip() for line in group.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            continue
        if len(lines) > 1 and _is_heading([lines[0]], lines[0]):
            rendered.append(f"### {lines[0]}")
            lines = lines[1:]
        joined = " ".join(lines)
        if joined:
            rendered.append(f"### {joined}" if _is_heading(lines, joined) else joined)
    return "\n\n".join(rendered)


def _base_markdown(
    title: str,
    pdf_asset_id: str,
    pages: Sequence[Mapping[str, Any]],
) -> str:
    sections = [
        f"# {title}",
        f"[Open original PDF](/api/source-assets/{pdf_asset_id})",
    ]
    for page in pages:
        marker = (
            f"<!-- pdf-page:{page['id']} page={page['page_number']} "
            f"text-layer={page['text_layer_status']} -->"
        )
        content = text_layer_markdown(str(page["text_body"]))
        section = f"{marker}\n\n## Page {page['page_number']}"
        if content:
            section += f"\n\n{content}"
        sections.append(section)
    return "\n\n".join(sections).rstrip() + "\n"


def _enriched_markdown(
    base: str,
    pages: Sequence[Mapping[str, Any]],
    analyses: Mapping[str, Mapping[str, Any]],
) -> str:
    by_marker: dict[str, str] = {}
    for page in pages:
        analysis = analyses[str(page["id"])]
        result = analysis.get("result") or {}
        if analysis["status"] == "succeeded" and not result.get("retain"):
            continue
        lines = [
            f"![PDF page {page['page_number']}](/api/source-assets/{page['render_asset_id']})"
        ]
        if analysis["status"] != "succeeded":
            lines.extend(["", "Image analysis: unresolved."])
        else:
            if result.get("description"):
                lines.extend(["", f"Image summary: {re.sub(r'\s+', ' ', result['description']).strip()}"])
            if result.get("ocr"):
                lines.extend(["", f"OCR: {re.sub(r'\s+', ' ', result['ocr']).strip()}"])
            if result.get("limitations"):
                lines.extend(["", f"Image limitations: {re.sub(r'\s+', ' ', result['limitations']).strip()}"])
        by_marker[str(page["id"])] = "\n".join(lines)
    sections = base.rstrip().split("\n\n<!-- pdf-page:")
    output = [sections[0]]
    for raw in sections[1:]:
        section = "<!-- pdf-page:" + raw
        match = re.match(r"<!-- pdf-page:([^ ]+) ", section)
        if match is None:
            raise RuntimeError("PDF page marker is malformed")
        page_id = match.group(1)
        visual = by_marker.get(page_id)
        output.append(section + (f"\n\n{visual}" if visual else ""))
    return "\n\n".join(output).rstrip() + "\n"


def _load_analyses(
    conn: psycopg.Connection, job_id: str
) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        "SELECT p.id, a.status, a.result, a.failure_code, a.diagnostics, a.id"
        " FROM source_pdf_page p JOIN source_asset_analysis a ON a.pdf_page_id = p.id"
        " WHERE p.acquisition_job_id = %s ORDER BY p.page_number, a.created_at, a.id",
        (job_id,),
    ).fetchall()
    analyses: dict[str, dict[str, Any]] = {}
    for page_id, status, result, failure_code, diagnostics, analysis_id in rows:
        analyses[page_id] = {
            "id": analysis_id,
            "status": status,
            "result": result or {},
            "failure_code": failure_code,
            "diagnostics": diagnostics or {},
        }
    return analyses


def _parsed_markdown(title: str, pdf_asset_id: str, parsed: str) -> str:
    return (
        f"# {title}\n\n"
        f"[Open original PDF](/api/source-assets/{pdf_asset_id})\n\n"
        f"{parsed.strip()}\n"
    )


def _figure_asset_id(
    job_id: str, pdf_asset_id: str, ordinal: int, source_url: str, sha256: str
) -> str:
    digest = hashlib.sha256(
        f"{job_id}:{pdf_asset_id}:{ordinal}:{source_url}:{sha256}".encode("utf-8")
    ).hexdigest()[:32]
    return f"pdf-figure-{digest}"


def _firecrawl_image_urls(markdown: str, reported: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in [*reported, *(ref.source_url for ref in extract_markdown_images(markdown))]:
        url = str(value).strip()
        if not url or url.startswith("/api/source-assets/") or url in seen:
            continue
        if not (url.startswith("data:image/") or urlsplit(url).scheme in {"http", "https"}):
            continue
        ordered.append(url)
        seen.add(url)
    return ordered


def _localize_firecrawl_images(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    markdown: str,
    reported_urls: Sequence[str],
    asset_store: AssetStore,
    downloader: Callable[[str], PdfDownloadedImage],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    urls = _firecrawl_image_urls(markdown, reported_urls)
    localized: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for ordinal, url in enumerate(urls, start=1):
        try:
            image = downloader(url)
            if (
                not image.body
                or image.mime_type not in {"image/png", "image/jpeg", "image/webp"}
                or hashlib.sha256(image.body).hexdigest() != image.sha256
            ):
                raise PdfExtractionError(
                    "pdf_image_download_failed", "invalid_download_result"
                )
            stored = asset_store.put(image.body, sha256=image.sha256)
            asset_id = _figure_asset_id(
                str(job["id"]),
                str(pdf_asset["id"]),
                ordinal,
                url,
                image.sha256,
            )
            metadata = {
                "pdf_asset_id": pdf_asset["id"],
                "derived_by": PDF_TEXT_TOOL_VERSION,
                "source_url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
                "width": image.width,
                "height": image.height,
            }
            original_url = url if urlsplit(url).scheme in {"http", "https"} else None
            conn.execute(
                "INSERT INTO source_asset"
                " (id, acquisition_job_id, source_id, ordinal, kind, filename,"
                " mime_type, sha256, byte_size, storage_key, metadata, original_url)"
                " VALUES (%s, %s, %s, %s, 'pdf_figure', %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (id) DO NOTHING",
                (
                    asset_id,
                    job["id"],
                    job["source_id"],
                    DERIVED_FIGURE_ORDINAL_BASE + ordinal,
                    image.filename,
                    image.mime_type,
                    image.sha256,
                    len(image.body),
                    stored.key,
                    Jsonb(metadata),
                    original_url,
                ),
            )
            row = conn.execute(
                "SELECT id, filename, mime_type, sha256, storage_key, metadata"
                " FROM source_asset WHERE id = %s",
                (asset_id,),
            ).fetchone()
            if row is None or row[2:5] != (
                image.mime_type,
                image.sha256,
                stored.key,
            ):
                raise RuntimeError("persisted PDF figure does not match its input")
            localized[url] = {
                "id": row[0],
                "filename": row[1],
                "mime_type": row[2],
                "sha256": row[3],
                "storage_key": row[4],
                "metadata": row[5] or {},
                "source_url": url,
            }
            conn.commit()
        except PdfExtractionError as exc:
            conn.rollback()
            failures.append(
                {
                    "ordinal": ordinal,
                    "source_url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
                    "failure_code": exc.code,
                    "category": exc.category,
                }
            )
    references = extract_markdown_images(markdown)
    output = markdown
    referenced_urls: set[str] = set()
    for reference in reversed(references):
        asset = localized.get(reference.source_url)
        if asset is None:
            continue
        referenced_urls.add(reference.source_url)
        local_url = f"/api/source-assets/{asset['id']}"
        replacement = reference.original_markdown.replace(
            reference.source_url, local_url, 1
        )
        label = re.sub(
            r"\s+", " ", reference.alt_text.strip() or str(asset["filename"])
        )
        replacement += f"\n\nImage description: {label}"
        output = output[: reference.start_char] + replacement + output[reference.end_char :]

    additional = [
        asset for url, asset in localized.items() if url not in referenced_urls
    ]
    if additional:
        sections = [output.rstrip(), "", "## Extracted figures"]
        for asset in additional:
            label = re.sub(r"\s+", " ", str(asset["filename"]).strip())
            sections.extend(
                [
                    "",
                    f"![{label}](/api/source-assets/{asset['id']})",
                    "",
                    f"Image description: {label}",
                ]
            )
        output = "\n".join(sections)
    return output.rstrip() + "\n", list(localized.values()), failures


def _figure_candidate_pages(
    pages: Sequence[Mapping[str, Any]], markdown: str, localized_count: int
) -> list[Mapping[str, Any]]:
    if localized_count:
        return []
    matched = [
        page
        for page in pages
        if page["text_layer_status"] == "empty"
        or FIGURE_CAPTION.search(str(page["text_body"]))
    ]
    if not matched and FIGURE_CAPTION.search(markdown):
        return list(pages)
    return matched


def _crop_figure(render_body: bytes, bbox: tuple[int, int, int, int]) -> tuple[bytes, int, int]:
    try:
        with Image.open(io.BytesIO(render_body)) as image:
            image.load()
            width, height = image.size
            left, top, right, bottom = bbox
            pixel_box = (
                max(0, int(width * left / 1000)),
                max(0, int(height * top / 1000)),
                min(width, max(1, int(width * right / 1000))),
                min(height, max(1, int(height * bottom / 1000))),
            )
            if pixel_box[2] - pixel_box[0] < 20 or pixel_box[3] - pixel_box[1] < 20:
                raise ValueError("located PDF figure is too small")
            cropped = image.convert("RGB").crop(pixel_box)
            output = io.BytesIO()
            cropped.save(output, format="PNG", optimize=True)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise PdfExtractionError(
            "pdf_figure_crop_failed", "invalid_figure_region"
        ) from exc
    return output.getvalue(), cropped.width, cropped.height


def _persist_figure_crop(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    page: Mapping[str, Any],
    region: PdfFigureRegion,
    ordinal: int,
    render_body: bytes,
    asset_store: AssetStore,
    model_bbox: tuple[int, int, int, int] | None = None,
    caption_top_1000: int | None = None,
) -> dict[str, Any]:
    body, width, height = _crop_figure(render_body, region.bbox)
    sha256 = hashlib.sha256(body).hexdigest()
    stable_source = f"{page['id']}:{','.join(str(value) for value in region.bbox)}"
    asset_id = _figure_asset_id(
        str(job["id"]), str(pdf_asset["id"]), ordinal, stable_source, sha256
    )
    stored = asset_store.put(body, sha256=sha256)
    metadata = {
        "pdf_asset_id": pdf_asset["id"],
        "page_id": page["id"],
        "page_number": page["page_number"],
        "bbox_1000": list(region.bbox),
        "derived_by": PDF_FIGURE_PROMPT_REF,
        "width": width,
        "height": height,
    }
    if model_bbox is not None and model_bbox != region.bbox:
        metadata["model_bbox_1000"] = list(model_bbox)
        metadata["caption_top_1000"] = caption_top_1000
        metadata["bbox_adjustment"] = "extended_to_before_figure_caption"
    conn.execute(
        "INSERT INTO source_asset"
        " (id, acquisition_job_id, source_id, ordinal, kind, filename,"
        " mime_type, sha256, byte_size, storage_key, metadata)"
        " VALUES (%s, %s, %s, %s, 'pdf_figure', %s, 'image/png', %s, %s, %s, %s)"
        " ON CONFLICT (id) DO NOTHING",
        (
            asset_id,
            job["id"],
            job["source_id"],
            DERIVED_FIGURE_ORDINAL_BASE + ordinal,
            f"{Path(str(pdf_asset['filename'])).stem}-figure-{ordinal:04d}.png",
            sha256,
            len(body),
            stored.key,
            Jsonb(metadata),
        ),
    )
    conn.commit()
    return {
        "id": asset_id,
        "filename": f"PDF figure {ordinal}",
        "mime_type": "image/png",
        "sha256": sha256,
        "storage_key": stored.key,
        "metadata": metadata,
        "description": region.description,
        "visible_text": region.visible_text,
    }


def _figure_localization_call_id(
    job_id: str, pdf_asset_id: str, batch_ordinal: int
) -> str:
    digest = hashlib.sha256(
        f"{job_id}:{pdf_asset_id}:{batch_ordinal}:{PDF_FIGURE_PROMPT_REF}".encode(
            "utf-8"
        )
    ).hexdigest()[:32]
    return f"pdf-figure-call-{digest}"


def _locate_figures_once(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    batch_ordinal: int,
    context: str,
    inputs: list[SourceImageInput],
    locator: Callable[[str, list[SourceImageInput]], PdfFigureLocalizationResult],
) -> tuple[PdfFigureLocalizationResult, dict[str, Any]]:
    call_id = _figure_localization_call_id(
        str(job["id"]), str(pdf_asset["id"]), batch_ordinal
    )
    manifest_hash = input_manifest_hash(context, inputs)
    conn.execute(
        "INSERT INTO pdf_figure_localization_call"
        " (id, acquisition_job_id, pdf_asset_id, batch_ordinal, page_ids,"
        " prompt_ref, input_manifest_hash, status, requested_model)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, 'queued', %s)"
        " ON CONFLICT (id) DO NOTHING",
        (
            call_id,
            job["id"],
            pdf_asset["id"],
            batch_ordinal,
            Jsonb([image.image_id for image in inputs]),
            PDF_FIGURE_PROMPT_REF,
            manifest_hash,
            article_image_model(),
        ),
    )
    row = conn.execute(
        "SELECT status, attempt_count, requested_model, response_model, provider,"
        " usage, duration_ms, result, failure_code, diagnostics, input_manifest_hash"
        " FROM pdf_figure_localization_call WHERE id = %s",
        (call_id,),
    ).fetchone()
    conn.commit()
    if row is None or row[10] != manifest_hash:
        raise RuntimeError("PDF figure call does not match its immutable inputs")
    if row[0] == "succeeded":
        regions = tuple(
            PdfFigureRegion(
                page_id=str(item["page_id"]),
                bbox=tuple(item["bbox"]),
                description=str(item["description"]),
                visible_text=str(item.get("visible_text") or ""),
            )
            for item in (row[7] or {}).get("regions", [])
        )
        result = PdfFigureLocalizationResult(
            regions=regions,
            requested_model=str(row[2] or ""),
            response_model=str(row[3]) if row[3] else None,
            provider=str(row[4] or ""),
            usage=dict(row[5] or {}),
            duration_ms=int(row[6] or 0),
        )
        return result, {
            "id": call_id,
            "batch_ordinal": batch_ordinal,
            "status": "succeeded",
            "page_ids": [image.image_id for image in inputs],
            "prompt_ref": PDF_FIGURE_PROMPT_REF,
            "requested_model": result.requested_model,
            "response_model": result.response_model,
            "provider": result.provider,
            "usage": dict(result.usage),
            "duration_ms": result.duration_ms,
            "reused": True,
        }
    if row[0] == "failed":
        raise PdfExtractionError(
            str(row[8] or "pdf_figure_localization_failed"),
            str((row[9] or {}).get("category") or "figure_localization_failed"),
        )
    claimed = conn.execute(
        "UPDATE pdf_figure_localization_call SET status = 'running',"
        " attempt_count = attempt_count + 1, updated_at = now()"
        " WHERE id = %s AND status = 'queued' RETURNING attempt_count",
        (call_id,),
    ).fetchone()
    conn.commit()
    if claimed is None:
        raise RuntimeError("PDF figure localization call is already running")
    try:
        result = locator(context, inputs)
        valid_page_ids = {image.image_id for image in inputs}
        if any(region.page_id not in valid_page_ids for region in result.regions):
            raise ValueError("PDF figure result references another page")
        payload = {
            "regions": [
                {
                    "page_id": region.page_id,
                    "bbox": list(region.bbox),
                    "description": region.description,
                    "visible_text": region.visible_text,
                }
                for region in result.regions
            ]
        }
        conn.execute(
            "UPDATE pdf_figure_localization_call SET status = 'succeeded',"
            " requested_model = %s, response_model = %s, provider = %s, usage = %s,"
            " duration_ms = %s, result = %s, finished_at = now(), updated_at = now()"
            " WHERE id = %s AND status = 'running'",
            (
                result.requested_model,
                result.response_model,
                result.provider,
                Jsonb(dict(result.usage)),
                result.duration_ms,
                Jsonb(payload),
                call_id,
            ),
        )
        conn.commit()
        return result, {
            "id": call_id,
            "batch_ordinal": batch_ordinal,
            "status": "succeeded",
            "page_ids": [image.image_id for image in inputs],
            "prompt_ref": PDF_FIGURE_PROMPT_REF,
            "requested_model": result.requested_model,
            "response_model": result.response_model,
            "provider": result.provider,
            "usage": dict(result.usage),
            "duration_ms": result.duration_ms,
            "reused": False,
        }
    except Exception as exc:
        conn.rollback()
        conn.execute(
            "UPDATE pdf_figure_localization_call SET status = 'failed',"
            " failure_code = 'pdf_figure_localization_failed', diagnostics = %s,"
            " finished_at = now(), updated_at = now()"
            " WHERE id = %s AND status = 'running'",
            (
                Jsonb(
                    {
                        "category": "figure_localization_failed",
                        "exception": type(exc).__name__,
                    }
                ),
                call_id,
            ),
        )
        conn.commit()
        raise


def _recover_vector_figures(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    markdown: str,
    localized_count: int,
    asset_store: AssetStore,
    locator: Callable[[str, list[SourceImageInput]], PdfFigureLocalizationResult] | None,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = _figure_candidate_pages(pages, markdown, localized_count)
    if not candidates:
        return markdown, [], [], []
    if locator is None:
        return markdown, [], [], [
            {
                "category": "figure_localization_disabled",
                "failure_code": "pdf_figure_localization_disabled",
                "candidate_page_count": len(candidates),
            }
        ]
    render_bodies = {
        str(page["id"]): asset_store.get(str(page["storage_key"]))
        for page in candidates
    }
    figures: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for batch_ordinal, batch in enumerate(
        pdf_page_batches(candidates, render_bodies), start=1
    ):
        context = (
            "# Firecrawl structural Markdown\n\n"
            f"{markdown.strip()}\n\n"
            f"{_context_for_pages(batch)}"
        )
        inputs = _source_inputs(batch, render_bodies)
        try:
            result, call = _locate_figures_once(
                conn,
                job=job,
                pdf_asset=pdf_asset,
                batch_ordinal=batch_ordinal,
                context=context,
                inputs=inputs,
                locator=locator,
            )
            by_id = {str(page["id"]): page for page in batch}
            if any(region.page_id not in by_id for region in result.regions):
                raise ValueError("PDF figure result references a page outside its batch")
            calls.append(call)
            for region in result.regions:
                ordinal = localized_count + len(figures) + 1
                page = by_id[region.page_id]
                completed_bbox = _complete_figure_bbox(
                    region.bbox,
                    caption_top_1000=page.get("figure_caption_top_1000"),
                )
                completed_region = PdfFigureRegion(
                    page_id=region.page_id,
                    bbox=completed_bbox,
                    description=region.description,
                    visible_text=region.visible_text,
                )
                figures.append(
                    _persist_figure_crop(
                        conn,
                        job=job,
                        pdf_asset=pdf_asset,
                        page=page,
                        region=completed_region,
                        ordinal=ordinal,
                        render_body=render_bodies[region.page_id],
                        asset_store=asset_store,
                        model_bbox=region.bbox,
                        caption_top_1000=page.get("figure_caption_top_1000"),
                    )
                )
            if not result.regions:
                failures.append(
                    {
                        "batch_ordinal": batch_ordinal,
                        "category": "figure_not_localized",
                        "failure_code": "pdf_figure_not_localized",
                    }
                )
        except Exception as exc:
            conn.rollback()
            failures.append(
                {
                    "batch_ordinal": batch_ordinal,
                    "category": "figure_localization_failed",
                    "failure_code": "pdf_figure_localization_failed",
                    "exception": type(exc).__name__,
                }
            )
            calls.append(
                {
                    "batch_ordinal": batch_ordinal,
                    "status": "failed",
                    "page_ids": [str(page["id"]) for page in batch],
                    "prompt_ref": PDF_FIGURE_PROMPT_REF,
                    "usage": {},
                    "failure_code": "pdf_figure_localization_failed",
                }
            )
    if figures:
        sections = [markdown.rstrip(), "", "## Extracted figures"]
        for index, figure in enumerate(figures, start=1):
            sections.extend(
                [
                    "",
                    f"![PDF figure {index}](/api/source-assets/{figure['id']})",
                    "",
                    f"Image description: {figure['description']}",
                ]
            )
            if figure["visible_text"]:
                sections.extend(["", f"OCR: {figure['visible_text']}"])
        markdown = "\n".join(sections).rstrip() + "\n"
    return markdown, figures, calls, failures


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
) -> tuple[PdfParseResult, dict[str, Any]]:
    call_id = _document_parse_call_id(str(job["id"]), str(pdf_asset["id"]))
    options = {
        "formats": ["markdown", "images"],
        "pdf_mode": "auto",
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
        "SELECT status, attempt_count, provider_attempts, result, failure_code,"
        " diagnostics FROM pdf_document_parse_call WHERE id = %s",
        (call_id,),
    ).fetchone()
    conn.commit()
    if row is None:
        raise RuntimeError("PDF parse call was not persisted")
    status, attempt_count, provider_attempts, result, failure_code, diagnostics = row
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
) -> PdfAcquisitionResult:
    pdf_body = bytes(pdf_asset["body"])
    parsed, parse_call = _parse_document_once(
        conn,
        job=job,
        pdf_asset=pdf_asset,
        parser=document_parser,
    )
    pages = list(page_extractor(pdf_body))
    if not pages:
        raise PdfExtractionError("manual_pdf_extraction_failed", "pdf_has_no_pages")
    persisted = _persist_pages(conn, job, pdf_asset, pages, asset_store)
    raw = _parsed_markdown(title, str(pdf_asset["id"]), parsed.markdown)
    localized_markdown, figures, image_failures = _localize_firecrawl_images(
        conn,
        job=job,
        pdf_asset=pdf_asset,
        markdown=parsed.markdown,
        reported_urls=parsed.image_urls,
        asset_store=asset_store,
        downloader=image_downloader,
    )
    effective_locator = figure_locator
    if effective_locator is None and private_pdf_figure_localization_enabled():
        effective_locator = default_pdf_figure_locator
    localized_markdown, cropped_figures, calls, localization_failures = (
        _recover_vector_figures(
            conn,
            job=job,
            pdf_asset=pdf_asset,
            pages=persisted,
            markdown=localized_markdown,
            localized_count=len(figures),
            asset_store=asset_store,
            locator=effective_locator,
        )
    )
    figures.extend(cropped_figures)
    image_failures.extend(localization_failures)
    enriched = _parsed_markdown(
        title, str(pdf_asset["id"]), localized_markdown
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
        "input_mode": "pdf",
        "asset_count": 1,
        "asset_ids": [pdf_asset["id"]],
        "page_asset_ids": [page["render_asset_id"] for page in persisted],
        "figure_asset_ids": [figure["id"] for figure in figures],
        "page_count": len(persisted),
        "text_layer_pages": sum(page["text_layer_status"] == "usable" for page in persisted),
        "scanned_pages": sum(page["text_layer_status"] == "empty" for page in persisted),
        "extractor": {
            "document_tool": PDF_TEXT_TOOL,
            "document_tool_version": PDF_TEXT_TOOL_VERSION,
            "document_mode": "auto",
            "render_tool": "pdftoppm",
            "render_tool_version": PDF_RENDER_TOOL_VERSION,
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
