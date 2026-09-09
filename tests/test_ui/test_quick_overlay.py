"""Test dell'overlay QQuickWindow/QQuickPaintedItem."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.quick.drawing_canvas import DrawingCanvas
from ui.quick.overlay_surface import OverlaySurface
import ui.quick.overlay_surface as overlay_surface_module

_APP = QApplication.instance() or QApplication([])


def _adapters(tmp_path):
    settings = Settings(path=tmp_path / "quick_overlay_settings.json")
    controller = AppController(settings)
    return controller, DrawingAdapter(controller), ToolAdapter(controller)


def _close_surface(surface, drawing_adapter, tool_adapter) -> None:
    surface.shutdown()
    for window in surface.windows:
        window.deleteLater()
    drawing_adapter.close()
    tool_adapter.close()
    event_bus.clear()
    _APP.processEvents()


def test_overlay_surface_toggles_native_input_transparency(tmp_path) -> None:
    event_bus.clear()
    controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    surface = OverlaySurface(drawing_adapter, tool_adapter)
    surface.show()
    _APP.processEvents()

    try:
        assert surface._screen_signals_connected is True
        assert surface._bound_screens
        assert surface.window.flags() & Qt.WindowType.WindowTransparentForInput

        drawing_adapter.toggle_drawing()
        _APP.processEvents()
        assert controller.is_drawing_active() is True
        assert not (
            surface.window.flags() & Qt.WindowType.WindowTransparentForInput
        )

        drawing_adapter.toggle_drawing()
        _APP.processEvents()
        assert controller.is_drawing_active() is False
        assert surface.window.flags() & Qt.WindowType.WindowTransparentForInput
    finally:
        surface.shutdown()
        assert surface._screen_signals_connected is False
        assert surface._bound_screens == []
        for window in surface.windows:
            window.deleteLater()
        drawing_adapter.close()
        tool_adapter.close()
        event_bus.clear()
        _APP.processEvents()


def test_overlay_xcb_uses_input_shape_without_changing_window_flags(
    tmp_path,
    monkeypatch,
) -> None:
    event_bus.clear()
    controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    calls: list[tuple[int, bool]] = []

    monkeypatch.setattr(overlay_surface_module, "_platform_name", lambda: "xcb")
    monkeypatch.setattr(
        overlay_surface_module,
        "set_x11_click_through",
        lambda window_id, enabled: calls.append((window_id, enabled)) or True,
    )

    surface = OverlaySurface(drawing_adapter, tool_adapter)
    flags_before = surface.window.flags()
    surface.show()
    _APP.processEvents()

    try:
        assert calls and calls[-1][1] is True
        assert surface.window.flags() == flags_before
        assert not (
            surface.window.flags() & Qt.WindowType.WindowTransparentForInput
        )

        drawing_adapter.toggle_drawing()
        _APP.processEvents()
        assert controller.is_drawing_active() is True
        assert calls[-1][1] is False
        assert surface.window.flags() == flags_before

        drawing_adapter.toggle_drawing()
        _APP.processEvents()
        assert controller.is_drawing_active() is False
        assert calls[-1][1] is True
        assert surface.window.flags() == flags_before
    finally:
        _close_surface(surface, drawing_adapter, tool_adapter)


def test_native_wayland_builds_one_overlay_per_screen(
    tmp_path,
    monkeypatch,
) -> None:
    event_bus.clear()
    _controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    monkeypatch.setattr(overlay_surface_module, "_platform_name", lambda: "wayland")

    surface = OverlaySurface(drawing_adapter, tool_adapter)
    try:
        screens = list(_APP.screens())
        assert screens
        assert len(surface.windows) == len(screens)
        assert [view.screen for view in surface._views] == screens
        for view in surface._views:
            geometry = view.screen.geometry()
            assert view.canvas.global_origin() == QPointF(
                geometry.x(), geometry.y()
            )
    finally:
        _close_surface(surface, drawing_adapter, tool_adapter)


def test_drawing_canvas_commits_and_renders_pen_stroke(tmp_path) -> None:
    event_bus.clear()
    controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(drawing_adapter)
    canvas.setWidth(64)
    canvas.setHeight(64)

    drawing_adapter.toggle_drawing()
    canvas._begin_stroke(QPointF(10, 10))
    canvas._extend_stroke(QPointF(16, 16))
    canvas._finish_stroke(QPointF(22, 22))

    assert controller.stroke_manager.stroke_count == 1
    assert canvas._current_stroke is None

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
    event_bus.clear()
    _APP.processEvents()


def test_drawing_canvas_translates_global_desktop_coordinates(tmp_path) -> None:
    event_bus.clear()
    controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(
        drawing_adapter,
        global_origin=QPointF(-100, 50),
    )
    canvas.setWidth(64)
    canvas.setHeight(64)

    drawing_adapter.toggle_drawing()
    canvas._begin_stroke(QPointF(10, 10))
    canvas._finish_stroke(QPointF(20, 20))

    stroke = controller.stroke_manager.get_strokes()[0]
    assert stroke.points[0].x == -90
    assert stroke.points[0].y == 60

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
    event_bus.clear()
    _APP.processEvents()


def test_shape_preview_keeps_two_endpoints(tmp_path) -> None:
    event_bus.clear()
    controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(drawing_adapter)

    tool_adapter.select_tool("rect")
    canvas._begin_stroke(QPointF(4, 5))
    canvas._extend_stroke(QPointF(30, 40))

    assert canvas._current_stroke is not None
    assert len(canvas._current_stroke.points) == 2
    assert canvas._current_stroke.points[-1].x == 30
    assert canvas._current_stroke.points[-1].y == 40

    canvas._finish_stroke(QPointF(32, 42))
    assert controller.stroke_manager.stroke_count == 1
    assert canvas._current_stroke is None

    canvas.deleteLater()
    drawing_adapter.close()
    tool_adapter.close()
    event_bus.clear()
    _APP.processEvents()
