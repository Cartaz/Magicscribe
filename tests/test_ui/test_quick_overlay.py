"""Behavioral tests for the Quick drawing overlay."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from core.app_controller import AppController
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.quick.drawing_canvas import DrawingCanvas
from ui.quick.overlay_surface import OverlaySurface
import ui.quick.overlay_surface as overlay_surface_module

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


def test_overlay_surface_toggles_native_input_transparency(tmp_path) -> None:
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    surface = OverlaySurface(drawing_adapter, tool_adapter)
    surface.show()
    _APP.processEvents()
    try:
        assert surface.window.flags() & Qt.WindowType.WindowTransparentForInput
        drawing_adapter.toggle_drawing()
        _APP.processEvents()
        assert controller.is_drawing_active()
        assert not (surface.window.flags() & Qt.WindowType.WindowTransparentForInput)
        drawing_adapter.toggle_drawing()
        _APP.processEvents()
        assert surface.window.flags() & Qt.WindowType.WindowTransparentForInput
    finally:
        _close(surface, settings, drawing_adapter, tool_adapter)


def test_native_wayland_builds_one_overlay_per_screen(tmp_path, monkeypatch) -> None:
    settings, _controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    monkeypatch.setattr(overlay_surface_module, "_platform_name", lambda: "wayland")

    class _FakeLayerShellComponent:
        @staticmethod
        def create():
            return QQuickWindow()

        @staticmethod
        def errors():
            return []

    def _fake_prepare(surface: OverlaySurface) -> None:
        surface._wayland_component = _FakeLayerShellComponent()

    monkeypatch.setattr(OverlaySurface, "_prepare_wayland_component", _fake_prepare)
    surface = OverlaySurface(drawing_adapter, tool_adapter)
    try:
        screens = list(_APP.screens())
        assert screens
        assert len(surface.windows) == len(screens)
        for view in surface._views:
            geometry = view.screen.geometry()
            assert view.canvas.global_origin() == QPointF(geometry.x(), geometry.y())
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
