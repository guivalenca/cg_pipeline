"""Public contracts for content-aware figure crop planning."""

import io

import pytest
from PIL import Image, ImageDraw

from universe.acquisition.figure_crop import FigureCropUnresolved, plan_figure_crop


def _page_with_diagram_and_prose() -> bytes:
    page = Image.new("RGB", (1000, 1000), "white")
    draw = ImageDraw.Draw(page)
    draw.rectangle((250, 120, 750, 360), outline="black", width=4)
    draw.line((500, 360, 500, 384), fill="black", width=4)
    for top in (455, 480, 505):
        draw.rectangle((130, top, 870, top + 7), fill="black")
    output = io.BytesIO()
    page.save(output, format="PNG")
    return output.getvalue()


def test_normal_figure_stops_at_clean_gutter_before_prose():
    plan = plan_figure_crop(
        _page_with_diagram_and_prose(),
        (190, 90, 810, 380),
    )

    assert plan.bbox[0:3] == (190, 90, 810)
    assert 384 < plan.bbox[3] < 455
    assert plan.adjusted_edges == ("bottom",)


def test_clipped_rotated_figure_grows_each_touched_edge_to_clean_gutters():
    page = Image.new("RGB", (1000, 1000), "white")
    draw = ImageDraw.Draw(page)
    draw.polygon(
        ((500, 125), (895, 520), (500, 930), (105, 520)),
        outline="black",
        width=5,
    )
    output = io.BytesIO()
    page.save(output, format="PNG")

    plan = plan_figure_crop(output.getvalue(), (190, 160, 810, 790))

    left, top, right, bottom = plan.bbox
    assert left < 105
    assert top < 125
    assert right > 895
    assert bottom > 930
    assert plan.adjusted_edges == ("left", "top", "right", "bottom")


def test_figure_without_clean_separation_is_left_for_attention():
    page = Image.new("RGB", (1000, 1000), "black")
    output = io.BytesIO()
    page.save(output, format="PNG")

    with pytest.raises(FigureCropUnresolved, match="whitespace gutter"):
        plan_figure_crop(output.getvalue(), (300, 300, 700, 700))
