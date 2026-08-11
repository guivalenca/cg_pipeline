"""Exhaustive recovery and local placement of figures from rendered PDF pages.

Firecrawl Markdown remains the structural document.  This Module accounts for
every rendered page, persists informative crops, and inserts each crop beside
an exact Markdown anchor when one is available.
"""

from __future__ import annotations

import base64
import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

import psycopg
from PIL import Image, UnidentifiedImageError
from psycopg.types.json import Jsonb

from universe import blocks
from universe.acquisition.article_images import extract_markdown_images
from universe.acquisition.source_images import SourceImageInput, input_manifest_hash
from universe.assets import AssetStore
from universe.model_client import ModelClient
from universe.settings import (
    article_image_model,
    openrouter_multimodal_provider_routing,
)


PDF_FIGURE_PROMPT_REF = "pdf-figure-localization/v004"
PDF_FIGURE_PROMPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "prompts"
    / "pdf-figure-localization"
    / "v004.md"
)
UNANCHORED_FIGURES_HEADING = "## Extracted figures (unanchored)"
MAX_MULTIMODAL_REQUEST_BYTES = 18 * 1024 * 1024
MAX_MULTIMODAL_CONTEXT_CHARS = 80_000
MAX_FIGURE_PAGES_PER_CALL = 8
FIGURE_BBOX_HORIZONTAL_MARGIN_1000 = 24
FIGURE_BBOX_BOTTOM_MARGIN_1000 = 16
DERIVED_FIGURE_ORDINAL_BASE = 2_000_000

PDF_FIGURE_TOOL = {
    "type": "function",
    "function": {
        "name": "locate_pdf_figures",
        "description": (
            "Inventory every informative non-table figure on the supplied PDF pages."
        ),
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
                                    "left": {
                                        "type": "integer",
                                        "minimum": 0,
                                        "maximum": 1000,
                                    },
                                    "top": {
                                        "type": "integer",
                                        "minimum": 0,
                                        "maximum": 1000,
                                    },
                                    "right": {
                                        "type": "integer",
                                        "minimum": 0,
                                        "maximum": 1000,
                                    },
                                    "bottom": {
                                        "type": "integer",
                                        "minimum": 0,
                                        "maximum": 1000,
                                    },
                                },
                                "required": ["left", "top", "right", "bottom"],
                                "additionalProperties": False,
                            },
                            "description": {"type": "string"},
                            "visible_text": {"type": "string"},
                            "anchor_id": {
                                "type": "string",
                                "description": (
                                    "The exact md-block identifier beside this figure, or an empty "
                                    "string when no reliable Markdown anchor exists."
                                ),
                            },
                        },
                        "required": [
                            "page_id",
                            "bbox",
                            "description",
                            "visible_text",
                            "anchor_id",
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
class PdfFigureRegion:
    page_id: str
    bbox: tuple[int, int, int, int]
    description: str
    visible_text: str
    anchor_id: str = ""


@dataclass(frozen=True)
class PdfFigureLocalizationResult:
    regions: tuple[PdfFigureRegion, ...]
    requested_model: str
    response_model: str | None
    provider: str
    usage: dict[str, Any]
    duration_ms: int


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
class PdfFigurePlacementResult:
    markdown: str
    figures: tuple[dict[str, Any], ...]
    calls: tuple[dict[str, Any], ...]
    failures: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class _AnchorPlacement:
    status: str
    offset: int | None
    block_kind: str | None


class _ImageLocalizationError(RuntimeError):
    code = "pdf_image_download_failed"
    category = "invalid_download_result"


def _firecrawl_image_urls(markdown: str, reported: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    references = extract_markdown_images(markdown)
    for value in [*reported, *(reference.source_url for reference in references)]:
        url = str(value).strip()
        if not url or url.startswith("/api/source-assets/") or url in seen:
            continue
        if not (
            url.startswith("data:image/")
            or urlsplit(url).scheme in {"http", "https"}
        ):
            continue
        ordered.append(url)
        seen.add(url)
    return ordered


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
        bbox = tuple(raw_bbox[key] for key in ("left", "top", "right", "bottom"))
        if any(isinstance(value, bool) or not isinstance(value, int) for value in bbox):
            raise ValueError("PDF figure locator returned an invalid box")
        left, top, right, bottom = bbox
        if not (0 <= left < right <= 1000 and 0 <= top < bottom <= 1000):
            raise ValueError("PDF figure locator returned an out-of-range box")
        if (right - left) * (bottom - top) > 850_000:
            raise ValueError("PDF figure locator tried to retain a full page")
        description = str(item.get("description") or "").strip()
        visible_text = str(item.get("visible_text") or "").strip()
        anchor_id = str(item.get("anchor_id") or "").strip()
        if not description:
            raise ValueError("PDF figure locator omitted its visible description")
        if len(anchor_id) > 100:
            raise ValueError("PDF figure locator returned an oversized anchor")
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
                anchor_id=anchor_id,
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


def _batch_weight(page: Mapping[str, Any], body: bytes) -> tuple[int, int]:
    encoded_bytes = ((len(body) + 2) // 3) * 4
    return encoded_bytes, len(str(page["text_body"]))


def _page_batches(
    pages: Sequence[Mapping[str, Any]], render_bodies: Mapping[str, bytes]
) -> list[list[Mapping[str, Any]]]:
    batches: list[list[Mapping[str, Any]]] = []
    current: list[Mapping[str, Any]] = []
    byte_total = 0
    text_total = 0
    for page in pages:
        body = render_bodies[str(page["id"])]
        page_bytes, page_text = _batch_weight(page, body)
        if current and (
            len(current) >= MAX_FIGURE_PAGES_PER_CALL
            or byte_total + page_bytes > MAX_MULTIMODAL_REQUEST_BYTES
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


def _content_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[^\W_]+", value.casefold(), flags=re.UNICODE)
        if len(token) >= 3
    }


def _region_page_mismatch(
    region: PdfFigureRegion, pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any] | None:
    """Detect only strong cross-page evidence; uncertain cases remain accepted."""
    visible = _content_tokens(region.visible_text)
    if len(visible) < 8:
        return None
    scored = []
    for page in pages:
        if page["text_layer_status"] != "usable":
            continue
        overlap = len(visible & _content_tokens(str(page["text_body"]))) / len(visible)
        scored.append((overlap, str(page["id"])))
    if not scored:
        return None
    scored.sort(reverse=True)
    best_score, best_page_id = scored[0]
    claimed_score = next(
        (score for score, page_id in scored if page_id == region.page_id), 0.0
    )
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if (
        best_page_id != region.page_id
        and best_score >= 0.8
        and claimed_score <= 0.4
        and best_score - runner_up >= 0.25
    ):
        return {
            "reason": "visible_text_matches_another_page",
            "claimed_score": round(claimed_score, 3),
            "best_score": round(best_score, 3),
            "best_page_id": best_page_id,
        }
    return None


def _figure_asset_id(
    job_id: str, pdf_asset_id: str, ordinal: int, source: str, sha256: str
) -> str:
    digest = hashlib.sha256(
        f"{job_id}:{pdf_asset_id}:{ordinal}:{source}:{sha256}".encode("utf-8")
    ).hexdigest()[:32]
    return f"pdf-figure-{digest}"


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
    references = extract_markdown_images(markdown)
    reference_urls = {reference.source_url for reference in references}
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
                raise _ImageLocalizationError("invalid PDF image download result")
            stored = asset_store.put(image.body, sha256=image.sha256)
            asset_id = _figure_asset_id(
                str(job["id"]), str(pdf_asset["id"]), ordinal, url, image.sha256
            )
            metadata = {
                "pdf_asset_id": pdf_asset["id"],
                "derived_by": "firecrawl-v2-parse.v1",
                "source_url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
                "width": image.width,
                "height": image.height,
                "placement": (
                    "firecrawl_markdown_reference"
                    if url in reference_urls
                    else "unanchored_firecrawl_result"
                ),
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
        except Exception as exc:
            conn.rollback()
            code = getattr(exc, "code", None)
            category = getattr(exc, "category", None)
            if not code or not category:
                raise
            failures.append(
                {
                    "ordinal": ordinal,
                    "source_url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
                    "failure_code": str(code),
                    "category": str(category),
                }
            )

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
        output = (
            output[: reference.start_char]
            + replacement
            + output[reference.end_char :]
        )

    additional = [
        asset for url, asset in localized.items() if url not in referenced_urls
    ]
    if additional:
        sections = [output.rstrip()]
        if UNANCHORED_FIGURES_HEADING not in output:
            sections.extend(["", UNANCHORED_FIGURES_HEADING])
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


def _crop_figure(
    render_body: bytes, bbox: tuple[int, int, int, int]
) -> tuple[bytes, int, int]:
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
        raise ValueError("invalid PDF figure region") from exc
    return output.getvalue(), cropped.width, cropped.height


def _markdown_anchors(
    markdown: str,
) -> tuple[str, dict[str, blocks.Block]]:
    inventory = ["# Canonical Markdown placement anchors"]
    indexed: dict[str, blocks.Block] = {}
    for ordinal, block in enumerate(blocks.split_blocks(markdown), start=1):
        if block.kind in {"image", "image_summary"}:
            continue
        digest = hashlib.sha256(block.text.encode("utf-8")).hexdigest()[:10]
        anchor_id = f"md-block-{ordinal:04d}-{digest}"
        indexed[anchor_id] = block
        inventory.append(
            f"## anchor_id: {anchor_id}\nkind: {block.kind}\n\n{block.text}"
        )
    return "\n\n".join(inventory).rstrip() + "\n", indexed


def _find_anchor(
    anchors: Mapping[str, blocks.Block], anchor_id: str
) -> _AnchorPlacement:
    if not anchor_id:
        return _AnchorPlacement("missing_anchor", None, None)
    block = anchors.get(anchor_id)
    if block is None:
        return _AnchorPlacement("unmatched_anchor", None, None)
    return _AnchorPlacement("before_markdown_block", block.start_char, block.kind)


def _complete_figure_bbox(
    bbox: tuple[int, int, int, int], *, caption_top_1000: int | None
) -> tuple[int, int, int, int]:
    if caption_top_1000 is None:
        return bbox
    left, top, right, bottom = bbox
    target_bottom = max(top + 1, caption_top_1000 - 10)
    if bottom < target_bottom and bottom < caption_top_1000:
        return (left, top, right, min(1000, target_bottom))
    return bbox


def _pad_figure_bbox(
    bbox: tuple[int, int, int, int], *,
    caption_top_1000: int | None,
    bottom_margin_1000: int = FIGURE_BBOX_BOTTOM_MARGIN_1000,
) -> tuple[int, int, int, int]:
    """Give semantic boxes enough context to avoid clipping diagram strokes.

    Vision models commonly return boxes tangent to circles, arrowheads, and
    labels.  A small deterministic margin is cheaper and more reliable than a
    second localization call.  When a single known caption follows the figure,
    the lower margin stops before it so the crop does not absorb prose.
    """
    left, top, right, bottom = bbox
    bottom_limit = 1000
    if caption_top_1000 is not None and bottom < caption_top_1000:
        bottom_limit = max(top + 1, caption_top_1000 - 10)
    return (
        max(0, left - FIGURE_BBOX_HORIZONTAL_MARGIN_1000),
        top,
        min(1000, right + FIGURE_BBOX_HORIZONTAL_MARGIN_1000),
        min(bottom_limit, bottom + bottom_margin_1000),
    )


def _multi_region_text_gap_bboxes(
    regions: Sequence[PdfFigureRegion], *, page: Mapping[str, Any]
) -> dict[tuple[int, int, int, int], tuple[int, int, int, int]]:
    """Assign stacked regions to visual gaps between exact Poppler prose lines.

    Gemini reliably inventories diagrams but may compress intervening prose in
    its Y coordinates. Wide/dense Poppler lines bound the whitespace that owns
    each visual. A monotonic nearest-gap assignment retains Gemini's region
    order and X coordinates while replacing only the drifting vertical axis.
    """
    raw_lines = page.get("text_lines_1000")
    if not isinstance(raw_lines, (list, tuple)) or not raw_lines:
        return {}
    lines = [
        tuple(line)
        for line in raw_lines
        if isinstance(line, (list, tuple))
        and len(line) == 5
        and isinstance(line[0], str)
        and all(isinstance(value, int) for value in line[1:])
    ]
    if not lines:
        return {}
    lines.sort(key=lambda line: (line[2], line[1], line[4], line[3]))
    prose_lines = [
        line
        for line in lines
        if int(line[3]) - int(line[1]) >= 280
        or len(_content_tokens(str(line[0]))) >= 7
        or re.match(r"^\s*\d+(?:\.\d+)+\s", str(line[0]))
    ]
    gaps = [
        (int(previous[4]) + 6, int(following[2]) - 6)
        for previous, following in zip(prose_lines, prose_lines[1:])
        if int(following[2]) - int(previous[4]) - 12 >= 35
    ]
    if prose_lines and 970 - int(prose_lines[-1][4]) - 6 >= 35:
        gaps.append((int(prose_lines[-1][4]) + 6, 970))
    ordered = sorted(regions, key=lambda region: (region.bbox[1], region.bbox[0]))
    if len(gaps) < len(ordered):
        return {}
    assigned: dict[tuple[int, int, int, int], tuple[int, int, int, int]] = {}
    previous_gap = -1
    for index, region in enumerate(ordered):
        remaining = len(ordered) - index - 1
        final_candidate = len(gaps) - remaining - 1
        choices = range(previous_gap + 1, final_candidate + 1)
        model_top, model_bottom = region.bbox[1], region.bbox[3]
        model_center = (model_top + model_bottom) / 2

        def cost(gap_index: int) -> tuple[int, float, float]:
            gap_top, gap_bottom = gaps[gap_index]
            overlap = max(0, min(model_bottom, gap_bottom) - max(model_top, gap_top))
            gap_center = (gap_top + gap_bottom) / 2
            return (
                0 if overlap else 1,
                -float(overlap) if overlap else abs(model_center - gap_center),
                abs(model_center - gap_center),
            )

        chosen = min(choices, key=cost)
        previous_gap = chosen
        left, _top, right, _bottom = region.bbox
        gap_top, gap_bottom = gaps[chosen]
        assigned[region.bbox] = (left, gap_top, right, gap_bottom)
    return assigned


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
    placement: _AnchorPlacement,
    known_sha256s: set[str],
    model_bbox: tuple[int, int, int, int] | None = None,
    caption_top_1000: int | None = None,
    geometry_adjustment: str | None = None,
) -> dict[str, Any]:
    body, width, height = _crop_figure(render_body, region.bbox)
    sha256 = hashlib.sha256(body).hexdigest()
    if sha256 in known_sha256s:
        return {"duplicate": True, "sha256": sha256}
    known_sha256s.add(sha256)
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
        "anchor_id": region.anchor_id,
        "placement": placement.status,
    }
    if placement.block_kind:
        metadata["anchor_block_kind"] = placement.block_kind
    if model_bbox is not None and model_bbox != region.bbox:
        metadata["model_bbox_1000"] = list(model_bbox)
        caption_target = (
            max(model_bbox[1] + 1, caption_top_1000 - 10)
            if caption_top_1000 is not None
            else None
        )
        caption_extended = (
            caption_target is not None
            and model_bbox[3] < caption_target
            and region.bbox[3] >= caption_target
        )
        metadata["bbox_adjustment"] = geometry_adjustment or (
            "padded_and_extended_to_before_figure_caption"
            if caption_extended
            else "padded_for_crop_safety"
        )
        if caption_top_1000 is not None:
            metadata["caption_top_1000"] = caption_top_1000
    filename = f"{Path(str(pdf_asset['filename'])).stem}-figure-{ordinal:04d}.png"
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
            filename,
            sha256,
            len(body),
            stored.key,
            Jsonb(metadata),
        ),
    )
    row = conn.execute(
        "SELECT id, sha256, storage_key FROM source_asset WHERE id = %s",
        (asset_id,),
    ).fetchone()
    if row is None or row[1:] != (sha256, stored.key):
        raise RuntimeError("persisted PDF figure does not match its crop")
    conn.commit()
    return {
        "duplicate": False,
        "id": asset_id,
        "filename": filename,
        "mime_type": "image/png",
        "sha256": sha256,
        "storage_key": stored.key,
        "metadata": metadata,
        "description": region.description,
        "visible_text": region.visible_text,
        "anchor_offset": placement.offset,
    }


def _call_id(job_id: str, pdf_asset_id: str, batch_ordinal: int) -> str:
    digest = hashlib.sha256(
        f"{job_id}:{pdf_asset_id}:{batch_ordinal}:{PDF_FIGURE_PROMPT_REF}".encode(
            "utf-8"
        )
    ).hexdigest()[:32]
    return f"pdf-figure-call-{digest}"


def _locate_once(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    batch_ordinal: int,
    context: str,
    inputs: list[SourceImageInput],
    locator: Callable[[str, list[SourceImageInput]], PdfFigureLocalizationResult],
) -> tuple[PdfFigureLocalizationResult, dict[str, Any]]:
    call_id = _call_id(str(job["id"]), str(pdf_asset["id"]), batch_ordinal)
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
                anchor_id=str(item.get("anchor_id") or ""),
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
        return result, _call_diagnostics(
            call_id, batch_ordinal, inputs, result, reused=True
        )
    if row[0] == "failed":
        raise RuntimeError(str(row[8] or "pdf_figure_localization_failed"))
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
                    "anchor_id": region.anchor_id,
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
        return result, _call_diagnostics(
            call_id, batch_ordinal, inputs, result, reused=False
        )
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


def _call_diagnostics(
    call_id: str,
    batch_ordinal: int,
    inputs: Sequence[SourceImageInput],
    result: PdfFigureLocalizationResult,
    *,
    reused: bool,
) -> dict[str, Any]:
    return {
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
        "reused": reused,
        "region_count": len(result.regions),
    }


def _record_region_outcome(
    conn: psycopg.Connection,
    *,
    call_id: str,
    region_ordinal: int,
    region: PdfFigureRegion,
    final_bbox: tuple[int, int, int, int],
    status: str,
    source_asset_id: str | None,
    diagnostics: Mapping[str, Any],
) -> None:
    digest = hashlib.sha256(
        f"{call_id}:{region_ordinal}:{PDF_FIGURE_PROMPT_REF}".encode("utf-8")
    ).hexdigest()[:32]
    outcome_id = f"pdf-figure-region-{digest}"
    conn.execute(
        "INSERT INTO pdf_figure_region_outcome"
        " (id, localization_call_id, region_ordinal, page_id, model_bbox,"
        " final_bbox, description, visible_text, anchor_id, status,"
        " source_asset_id, diagnostics)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (id) DO NOTHING",
        (
            outcome_id,
            call_id,
            region_ordinal,
            region.page_id,
            Jsonb(list(region.bbox)),
            Jsonb(list(final_bbox)),
            region.description,
            region.visible_text,
            region.anchor_id,
            status,
            source_asset_id,
            Jsonb(dict(diagnostics)),
        ),
    )
    row = conn.execute(
        "SELECT localization_call_id, region_ordinal, page_id, model_bbox,"
        " final_bbox, anchor_id, status, source_asset_id"
        " FROM pdf_figure_region_outcome WHERE id = %s",
        (outcome_id,),
    ).fetchone()
    expected = (
        call_id,
        region_ordinal,
        region.page_id,
        list(region.bbox),
        list(final_bbox),
        region.anchor_id,
        status,
        source_asset_id,
    )
    if row != expected:
        raise RuntimeError("persisted PDF figure region outcome is not idempotent")
    conn.commit()


def _figure_atom(index: int, figure: Mapping[str, Any]) -> str:
    description = re.sub(r"\s+", " ", str(figure["description"])).strip()
    visible_text = re.sub(r"\s+", " ", str(figure["visible_text"])).strip()
    lines = [
        f"![PDF figure {index}](/api/source-assets/{figure['id']})",
        "",
        f"Image description: {description}",
    ]
    if visible_text:
        lines.extend(["", f"OCR: {visible_text}"])
    return "\n".join(lines)


def _place_figures(markdown: str, figures: Sequence[Mapping[str, Any]]) -> str:
    anchored: list[tuple[int, int, str]] = []
    unanchored: list[str] = []
    for index, figure in enumerate(figures, start=1):
        index = int(figure.get("display_ordinal") or index)
        atom = _figure_atom(index, figure)
        offset = figure.get("anchor_offset")
        if isinstance(offset, int):
            anchored.append((offset, index, atom))
        else:
            unanchored.append(atom)

    output = markdown
    for offset, _index, atom in sorted(anchored, reverse=True):
        prefix = output[:offset].rstrip()
        suffix = output[offset:].lstrip()
        output = f"{prefix}\n\n{atom}\n\n{suffix}"
    if unanchored:
        output = output.rstrip()
        if UNANCHORED_FIGURES_HEADING not in output:
            output += f"\n\n{UNANCHORED_FIGURES_HEADING}"
        output += "\n\n" + "\n\n".join(unanchored)
    return output.rstrip() + "\n"


def _recover_crops(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    markdown: str,
    existing_figures: Sequence[Mapping[str, Any]],
    asset_store: AssetStore,
    locator: Callable[[str, list[SourceImageInput]], PdfFigureLocalizationResult]
    | None,
) -> PdfFigurePlacementResult:
    """Inspect every page and place every recovered crop near canonical text.

    An empty region list is a successful page-accounting result.  Only a
    disabled or failed locator makes the visual pass incomplete.
    """
    if not pages:
        return PdfFigurePlacementResult(markdown, (), (), ())
    if locator is None:
        return PdfFigurePlacementResult(
            markdown,
            (),
            (),
            (
                {
                    "category": "figure_localization_disabled",
                    "failure_code": "pdf_figure_localization_disabled",
                    "page_count": len(pages),
                },
            ),
        )
    render_bodies = {
        str(page["id"]): asset_store.get(str(page["storage_key"])) for page in pages
    }
    known_sha256s = {
        str(figure["sha256"])
        for figure in existing_figures
        if figure.get("sha256")
    }
    figures: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    anchor_inventory, anchors = _markdown_anchors(markdown)
    page_order = {
        str(page["id"]): (int(page["page_number"]), index)
        for index, page in enumerate(pages)
    }
    for batch_ordinal, batch in enumerate(_page_batches(pages, render_bodies), start=1):
        context = (
            f"{anchor_inventory}\n"
            f"{_context_for_pages(batch)}"
        )
        inputs = _source_inputs(batch, render_bodies)
        try:
            result, call = _locate_once(
                conn,
                job=job,
                pdf_asset=pdf_asset,
                batch_ordinal=batch_ordinal,
                context=context,
                inputs=inputs,
                locator=locator,
            )
            calls.append(call)
            by_id = {str(page["id"]): page for page in batch}
            ordered_regions = sorted(
                result.regions,
                key=lambda region: (
                    page_order[region.page_id],
                    region.bbox[1],
                    region.bbox[0],
                    region.bbox[3],
                    region.bbox[2],
                ),
            )
            region_entries = [
                (ordinal, region, _region_page_mismatch(region, batch))
                for ordinal, region in enumerate(ordered_regions, start=1)
            ]
            region_counts: dict[str, int] = {}
            for _ordinal, region, mismatch in region_entries:
                if mismatch is None:
                    region_counts[region.page_id] = (
                        region_counts.get(region.page_id, 0) + 1
                    )
            geometry_overrides: dict[
                tuple[str, tuple[int, int, int, int]],
                tuple[int, int, int, int],
            ] = {}
            for page_id, count in region_counts.items():
                if count <= 1:
                    continue
                page_regions = [
                    region
                    for _ordinal, region, mismatch in region_entries
                    if mismatch is None and region.page_id == page_id
                ]
                for model_bbox, final_bbox in _multi_region_text_gap_bboxes(
                    page_regions, page=by_id[page_id]
                ).items():
                    geometry_overrides[(page_id, model_bbox)] = final_bbox
            for region_ordinal, region, mismatch in region_entries:
                if mismatch is not None:
                    _record_region_outcome(
                        conn,
                        call_id=str(call["id"]),
                        region_ordinal=region_ordinal,
                        region=region,
                        final_bbox=region.bbox,
                        status="failed",
                        source_asset_id=None,
                        diagnostics=mismatch,
                    )
                    failures.append(
                        {
                            "batch_ordinal": batch_ordinal,
                            "region_ordinal": region_ordinal,
                            "page_id": region.page_id,
                            "category": "figure_page_mismatch",
                            "failure_code": "pdf_figure_page_mismatch",
                        }
                    )
                    continue
                page = by_id[region.page_id]
                caption_top = (
                    page.get("figure_caption_top_1000")
                    if region_counts[region.page_id] == 1
                    else None
                )
                geometry_bbox = geometry_overrides.get(
                    (region.page_id, region.bbox), region.bbox
                )
                geometry_adjusted = geometry_bbox != region.bbox
                padded_bbox = _pad_figure_bbox(
                    geometry_bbox,
                    caption_top_1000=caption_top,
                    bottom_margin_1000=(0 if geometry_adjusted else FIGURE_BBOX_BOTTOM_MARGIN_1000),
                )
                completed_bbox = _complete_figure_bbox(
                    padded_bbox,
                    caption_top_1000=caption_top,
                )
                completed_region = PdfFigureRegion(
                    page_id=region.page_id,
                    bbox=completed_bbox,
                    description=region.description,
                    visible_text=region.visible_text,
                    anchor_id=region.anchor_id,
                )
                placement = _find_anchor(anchors, region.anchor_id)
                ordinal = len(existing_figures) + len(figures) + 1
                try:
                    figure = _persist_figure_crop(
                        conn,
                        job=job,
                        pdf_asset=pdf_asset,
                        page=page,
                        region=completed_region,
                        ordinal=ordinal,
                        render_body=render_bodies[region.page_id],
                        asset_store=asset_store,
                        placement=placement,
                        known_sha256s=known_sha256s,
                        model_bbox=region.bbox,
                        caption_top_1000=caption_top,
                        geometry_adjustment=(
                            "multi_region_text_gap_with_side_margin"
                            if geometry_adjusted
                            else None
                        ),
                    )
                    if figure["duplicate"]:
                        _record_region_outcome(
                            conn,
                            call_id=str(call["id"]),
                            region_ordinal=region_ordinal,
                            region=region,
                            final_bbox=completed_bbox,
                            status="duplicate",
                            source_asset_id=None,
                            diagnostics={
                                "reason": "content_sha256_duplicate",
                                "sha256": figure["sha256"],
                            },
                        )
                        continue
                    figure["display_ordinal"] = ordinal
                    figures.append(figure)
                    outcome_status = (
                        "placed"
                        if placement.status == "before_markdown_block"
                        else "unanchored"
                    )
                    _record_region_outcome(
                        conn,
                        call_id=str(call["id"]),
                        region_ordinal=region_ordinal,
                        region=region,
                        final_bbox=completed_bbox,
                        status=outcome_status,
                        source_asset_id=str(figure["id"]),
                        diagnostics={
                            "placement": placement.status,
                            **(
                                {"geometry_adjustment": "multi_region_text_gap"}
                                if geometry_adjusted
                                else {}
                            ),
                        },
                    )
                except Exception as exc:
                    conn.rollback()
                    _record_region_outcome(
                        conn,
                        call_id=str(call["id"]),
                        region_ordinal=region_ordinal,
                        region=region,
                        final_bbox=completed_bbox,
                        status="failed",
                        source_asset_id=None,
                        diagnostics={"exception": type(exc).__name__},
                    )
                    failures.append(
                        {
                            "batch_ordinal": batch_ordinal,
                            "region_ordinal": region_ordinal,
                            "page_id": region.page_id,
                            "category": "figure_crop_failed",
                            "failure_code": "pdf_figure_crop_failed",
                            "exception": type(exc).__name__,
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
    placed = _place_figures(markdown, figures)
    return PdfFigurePlacementResult(
        placed, tuple(figures), tuple(calls), tuple(failures)
    )


def place_pdf_figures(
    conn: psycopg.Connection,
    *,
    job: Mapping[str, Any],
    pdf_asset: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    markdown: str,
    reported_urls: Sequence[str],
    asset_store: AssetStore,
    image_downloader: Callable[[str], PdfDownloadedImage],
    locator: Callable[[str, list[SourceImageInput]], PdfFigureLocalizationResult]
    | None,
) -> PdfFigurePlacementResult:
    """Localize provider images, scan all pages, and place every accepted figure."""
    localized_markdown, firecrawl_figures, download_failures = (
        _localize_firecrawl_images(
            conn,
            job=job,
            pdf_asset=pdf_asset,
            markdown=markdown,
            reported_urls=reported_urls,
            asset_store=asset_store,
            downloader=image_downloader,
        )
    )
    recovered = _recover_crops(
        conn,
        job=job,
        pdf_asset=pdf_asset,
        pages=pages,
        markdown=localized_markdown,
        existing_figures=firecrawl_figures,
        asset_store=asset_store,
        locator=locator,
    )
    return PdfFigurePlacementResult(
        markdown=recovered.markdown,
        figures=tuple([*firecrawl_figures, *recovered.figures]),
        calls=recovered.calls,
        failures=tuple([*download_failures, *recovered.failures]),
    )
