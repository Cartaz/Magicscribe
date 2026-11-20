"""Pixel-level rendering tests for every drawing tool."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter

from core.models import Point, Stroke, ToolType
from ui.drawing_engine import DrawingEngine


def _render(*strokes: Stroke) -> QImage:
    image = QImage(100, 100, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        DrawingEngine.render_strokes(painter, list(strokes))
    finally:
        painter.end()
    return image


def _alpha(image: QImage, x: int, y: int) -> int:
    return image.pixelColor(x, y).alpha()


@pytest.mark.parametrize("tool", [ToolType.PEN, ToolType.SMOOTH, ToolType.LINE])
def test_open_paths_paint_along_the_stroke_only(tool: ToolType) -> None:
    points = [Point(float(x), 50.0) for x in range(10, 91)]
    image = _render(Stroke(tool, points, "#00ff00", 6))

    assert image.pixelColor(50, 50) == QColor("#00ff00")
    assert _alpha(image, 50, 20) == 0


def test_rect_outlines_the_dragged_box_without_fill() -> None:
    image = _render(Stroke(ToolType.RECT, [Point(80, 80), Point(20, 20)], "#0000ff", 4))

    assert _alpha(image, 20, 50) > 0
    assert _alpha(image, 50, 80) > 0
    assert _alpha(image, 50, 50) == 0


def test_circle_outlines_the_bounding_ellipse_without_fill() -> None:
    image = _render(Stroke(ToolType.CIRCLE, [Point(20, 20), Point(80, 80)], "#ff8800", 4))

    assert _alpha(image, 50, 20) > 0
    assert _alpha(image, 20, 50) > 0
    assert _alpha(image, 50, 50) == 0
    assert _alpha(image, 22, 22) == 0


def test_shapes_need_two_points() -> None:
    for tool in (ToolType.LINE, ToolType.RECT, ToolType.CIRCLE):
        image = _render(Stroke(tool, [Point(50, 50)], "#ff0000", 10))
        assert _alpha(image, 50, 50) == 0


def test_eraser_clears_earlier_strokes_only_where_it_passes() -> None:
    pen = Stroke(ToolType.PEN, [Point(10, 50), Point(90, 50)], "#ff0000", 10)
    eraser = Stroke(ToolType.ERASER, [Point(50, 10), Point(50, 90)], "#000000", 20)
    image = _render(pen, eraser)

    assert _alpha(image, 50, 50) == 0
    assert image.pixelColor(20, 50) == QColor("#ff0000")


def test_invalid_color_falls_back_to_black() -> None:
    image = _render(Stroke(ToolType.PEN, [Point(10, 50), Point(90, 50)], "nope", 6))

    assert image.pixelColor(50, 50) == QColor("#000000")
