"""Content-aware crop planning for figures localized on rendered pages.

The vision model supplies the semantic region.  This Module verifies the
region against the page pixels and grows touched edges only as far as the
first stable whitespace gutter.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError


NormalizedBBox = tuple[int, int, int, int]


class FigureCropUnresolved(ValueError):
    """Raised when page pixels do not expose a safe crop boundary."""


@dataclass(frozen=True)
class FigureCropPlan:
    """A validated normalized crop and the edges changed to obtain it."""

    bbox: NormalizedBBox
    adjusted_edges: tuple[str, ...]


def _page_ink(render_body: bytes) -> tuple[list[int], int]:
    try:
        with Image.open(io.BytesIO(render_body)) as image:
            image.load()
            grayscale = ImageOps.grayscale(image).resize(
                (1000, 1000), Image.Resampling.BILINEAR
            )
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise FigureCropUnresolved("figure page render is invalid") from exc

    histogram = grayscale.histogram()
    target = grayscale.width * grayscale.height * 0.90
    cumulative = 0
    background = 255
    for luminance, count in enumerate(histogram):
        cumulative += count
        if cumulative >= target:
            background = luminance
            break
    ink_threshold = max(80, min(245, background - 18))
    pixels = (
        grayscale.get_flattened_data()
        if hasattr(grayscale, "get_flattened_data")
        else grayscale.getdata()
    )
    return list(pixels), ink_threshold


def _axis_position_is_blank(
    pixels: list[int],
    *,
    position: int,
    span_start: int,
    span_end: int,
    horizontal: bool,
    threshold: int,
) -> bool:
    allowed_ink = max(1, (span_end - span_start) // 400)
    ink = 0
    for offset in range(span_start, span_end):
        pixel_index = (
            position * 1000 + offset
            if horizontal
            else offset * 1000 + position
        )
        if pixels[pixel_index] <= threshold:
            ink += 1
            if ink > allowed_ink:
                return False
    return True


def _stable_blank_runs(
    pixels: list[int],
    *,
    scan_start: int,
    scan_end: int,
    span_start: int,
    span_end: int,
    horizontal: bool,
    threshold: int,
    minimum_gutter: int = 12,
) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    run_start: int | None = None
    for position in range(scan_start, scan_end):
        if _axis_position_is_blank(
            pixels,
            position=position,
            span_start=span_start,
            span_end=span_end,
            horizontal=horizontal,
            threshold=threshold,
        ):
            if run_start is None:
                run_start = position
            continue
        if run_start is not None and position - run_start >= minimum_gutter:
            runs.append((run_start, position))
        run_start = None
    if run_start is not None and scan_end - run_start >= minimum_gutter:
        runs.append((run_start, scan_end))
    return runs


def _planned_boundary(
    pixels: list[int],
    *,
    boundary: int,
    span_start: int,
    span_end: int,
    horizontal: bool,
    direction: int,
    edge_name: str,
    threshold: int,
    max_expansion: int = 220,
    max_recession: int = 60,
    minimum_gutter: int = 12,
) -> int:
    if (direction < 0 and boundary == 0) or (direction > 0 and boundary == 1000):
        return boundary
    if direction > 0:
        scan_start = max(0, boundary - max_recession)
        scan_end = min(1000, boundary + max_expansion)
    else:
        scan_start = max(0, boundary - max_expansion)
        scan_end = min(1000, boundary + max_recession)
    runs = _stable_blank_runs(
        pixels,
        scan_start=scan_start,
        scan_end=scan_end,
        span_start=span_start,
        span_end=span_end,
        horizontal=horizontal,
        threshold=threshold,
        minimum_gutter=minimum_gutter,
    )
    if any(start <= boundary < end for start, end in runs):
        return boundary
    if direction > 0:
        inward = [
            (start, end)
            for start, end in runs
            if end <= boundary and boundary - end <= max_recession
        ]
        if inward:
            start, end = max(inward, key=lambda run: run[1])
            return min(end - 1, start + 3)
        candidates = [(start, end) for start, end in runs if start > boundary]
        if candidates:
            start, end = min(candidates, key=lambda run: run[0])
            return min(end - 1, start + 3)
    else:
        inward = [
            (start, end)
            for start, end in runs
            if start >= boundary and start - boundary <= max_recession
        ]
        if inward:
            start, end = min(inward, key=lambda run: run[0])
            return max(start, end - 3)
        candidates = [(start, end) for start, end in runs if end <= boundary]
        if candidates:
            start, end = max(candidates, key=lambda run: run[1])
            return max(start, end - 3)
    raise FigureCropUnresolved(f"no clean whitespace gutter beyond {edge_name} edge")


def plan_figure_crop(
    render_body: bytes, semantic_bbox: NormalizedBBox
) -> FigureCropPlan:
    """Validate a semantic box and extend touched edges to whitespace."""

    left, top, right, bottom = semantic_bbox
    if not (0 <= left < right <= 1000 and 0 <= top < bottom <= 1000):
        raise FigureCropUnresolved("figure bounding box is invalid")
    pixels, threshold = _page_ink(render_body)
    planned_left = _planned_boundary(
        pixels,
        boundary=left,
        span_start=top,
        span_end=bottom,
        horizontal=False,
        direction=-1,
        edge_name="left",
        threshold=threshold,
    )
    planned_top = _planned_boundary(
        pixels,
        boundary=top,
        span_start=left,
        span_end=right,
        horizontal=True,
        direction=-1,
        edge_name="top",
        threshold=threshold,
    )
    planned_right = _planned_boundary(
        pixels,
        boundary=right,
        span_start=top,
        span_end=bottom,
        horizontal=False,
        direction=1,
        edge_name="right",
        threshold=threshold,
    )
    planned_bottom = _planned_boundary(
        pixels,
        boundary=bottom,
        span_start=left,
        span_end=right,
        horizontal=True,
        direction=1,
        edge_name="bottom",
        threshold=threshold,
    )
    planned = (planned_left, planned_top, planned_right, planned_bottom)
    adjusted_edges = tuple(
        name
        for name, original, final in zip(
            ("left", "top", "right", "bottom"), semantic_bbox, planned
        )
        if original != final
    )
    return FigureCropPlan(
        bbox=planned,
        adjusted_edges=adjusted_edges,
    )
