"""Behavioral tests for the Quick drawing overlay."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from core.app_controller import AppController
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.drawing_engine import DrawingEngine
from ui.quick.drawing_canvas import DrawingCanvas
from ui.quick.overlay_surface import OverlaySurface

_APP = QApplication.instance() or QApplication([])


def _adapters(tmp_path):
    settings = Settings(path=tmp_path / "quick.json")
    controller = AppController(settings)
    return settings, controller, DrawingAdapter(controller), ToolAdapter(controller)


def _close(surface, settings, drawing_adapter, tool_adapter) -> None:
    surface.shutdown()
    for window in surface.windows:
        window.deleteLater()
    drawing_adapter.close()
    tool_adapter.close()
    settings.close()
    _APP.processEvents()


def test_overlay_surface_toggles_native_input_transparency(
    tmp_path, overlay_window_component
) -> None:
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    surface = OverlaySurface(
        drawing_adapter, tool_adapter, window_component=overlay_window_component
    )
    surface.show()
    _APP.processEvents()
    try:
        assert surface.windows[0].flags() & Qt.WindowType.WindowTransparentForInput
        drawing_adapter.toggle_drawing()
        _APP.processEvents()
        assert controller.is_drawing_active()
        assert not (surface.windows[0].flags() & Qt.WindowType.WindowTransparentForInput)
        drawing_adapter.toggle_drawing()
        _APP.processEvents()
        assert surface.windows[0].flags() & Qt.WindowType.WindowTransparentForInput
    finally:
        _close(surface, settings, drawing_adapter, tool_adapter)


def test_overlay_builds_one_layer_surface_per_screen(
    tmp_path, overlay_window_component
) -> None:
    settings, _controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    surface = OverlaySurface(
        drawing_adapter, tool_adapter, window_component=overlay_window_component
    )
    try:
        screens = list(_APP.screens())
        assert screens
        assert list(surface.windows) == overlay_window_component.created
        assert len(surface.windows) == len(screens)
        for view in surface._views:
            assert view.window.screen() is view.screen
            geometry = view.screen.geometry()
            assert view.canvas.global_origin() == QPointF(geometry.x(), geometry.y())
    finally:
        _close(surface, settings, drawing_adapter, tool_adapter)


def test_screen_topology_change_rebuilds_visible_surfaces(
    tmp_path, overlay_window_component
) -> None:
    settings, _controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    surface = OverlaySurface(
        drawing_adapter, tool_adapter, window_component=overlay_window_component
    )
    surface.show()
    try:
        before = surface.windows
        surface._on_screen_topology_changed()
        _APP.processEvents()
        after = surface.windows
        assert len(after) == len(_APP.screens())
        assert not set(before) & set(after)
        assert all(window.isVisible() for window in after)
        assert all(
            window.flags() & Qt.WindowType.WindowTransparentForInput for window in after
        )
    finally:
        _close(surface, settings, drawing_adapter, tool_adapter)


def test_drawing_canvas_commits_and_renders_pen_stroke(tmp_path) -> None:
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(drawing_adapter)
    canvas.setWidth(64)
    canvas.setHeight(64)
    drawing_adapter.toggle_drawing()
    canvas._begin_stroke(QPointF(10, 10))
    canvas._extend_stroke(QPointF(16, 16))
    canvas._finish_stroke(QPointF(22, 22))
    assert controller.stroke_count() == 1

    image = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        canvas.paint(painter)
    finally:
        painter.end()
    assert image.pixelColor(10, 10).alpha() > 0

    canvas.deleteLater()
    drawing_adapter.close()
    tool_adapter.close()
    settings.close()
    _APP.processEvents()


def test_canvas_stores_global_desktop_coordinates(tmp_path) -> None:
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(drawing_adapter, global_origin=QPointF(-100, 50))
    drawing_adapter.toggle_drawing()
    canvas._begin_stroke(QPointF(10, 10))
    canvas._finish_stroke(QPointF(20, 20))
    stroke = controller.strokes_snapshot()[0]
    assert stroke.points[0].x == -90
    assert stroke.points[0].y == 60

    canvas.deleteLater()
    drawing_adapter.close()
    tool_adapter.close()
    settings.close()
    _APP.processEvents()


def test_shape_preview_keeps_two_endpoints(tmp_path) -> None:
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(drawing_adapter)
    tool_adapter.select_tool("rect")
    canvas._begin_stroke(QPointF(4, 5))
    canvas._extend_stroke(QPointF(30, 40))
    assert canvas._current_stroke is not None
    assert len(canvas._current_stroke.points) == 2
    canvas._finish_stroke(QPointF(32, 42))
    assert controller.stroke_count() == 1

    canvas.deleteLater()
    drawing_adapter.close()
    tool_adapter.close()
    settings.close()
    _APP.processEvents()


def _paint(canvas: DrawingCanvas, size: int = 64) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        canvas.paint(painter)
    finally:
        painter.end()
    return image


def test_live_frames_reuse_the_committed_strokes_layer(tmp_path, monkeypatch) -> None:
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(drawing_adapter)
    canvas.setWidth(64)
    canvas.setHeight(64)
    drawing_adapter.toggle_drawing()
    canvas._begin_stroke(QPointF(5, 5))
    canvas._finish_stroke(QPointF(20, 5))

    history_renders: list[int] = []
    original = DrawingEngine.render_strokes

    def counting_render(painter, strokes):
        history_renders.append(len(strokes))
        original(painter, strokes)

    monkeypatch.setattr(DrawingEngine, "render_strokes", staticmethod(counting_render))
    try:
        canvas._begin_stroke(QPointF(5, 40))
        for x in range(6, 40):
            canvas._extend_stroke(QPointF(x, 40))
            image = _paint(canvas)
        # Una sola rasterizzazione della cronologia per tutti i frame live.
        assert history_renders == [1]
        assert image.pixelColor(10, 5).alpha() > 0
        assert image.pixelColor(30, 40).alpha() > 0

        canvas._finish_stroke(QPointF(40, 40))
        _paint(canvas)
        assert history_renders == [1, 2]
    finally:
        canvas.deleteLater()
        drawing_adapter.close()
        tool_adapter.close()
        settings.close()
        _APP.processEvents()


def test_history_changes_invalidate_the_committed_layer(tmp_path) -> None:
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(drawing_adapter)
    canvas.setWidth(64)
    canvas.setHeight(64)
    drawing_adapter.toggle_drawing()
    canvas._begin_stroke(QPointF(10, 10))
    canvas._finish_stroke(QPointF(30, 10))
    try:
        assert _paint(canvas).pixelColor(20, 10).alpha() > 0
        drawing_adapter.undo()
        assert _paint(canvas).pixelColor(20, 10).alpha() == 0
        drawing_adapter.redo()
        assert _paint(canvas).pixelColor(20, 10).alpha() > 0
        drawing_adapter.clear_screen()
        assert _paint(canvas).pixelColor(20, 10).alpha() == 0
    finally:
        canvas.deleteLater()
        drawing_adapter.close()
        tool_adapter.close()
        settings.close()
        _APP.processEvents()
