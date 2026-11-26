"""Behavioral tests for the Quick drawing overlay."""

from __future__ import annotations

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
    for y in (5, 10, 15):
        canvas._begin_stroke(QPointF(5, y))
        canvas._finish_stroke(QPointF(20, y))

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
        assert history_renders == [3]
        assert image.pixelColor(10, 5).alpha() > 0
        assert image.pixelColor(30, 40).alpha() > 0

        # Committing appends the new stroke to the layer without a rebuild.
        canvas._finish_stroke(QPointF(40, 40))
        image = _paint(canvas)
        assert history_renders == [3, 1]
        assert image.pixelColor(30, 40).alpha() > 0
        assert image.pixelColor(10, 5).alpha() > 0

        # Toggling visibility does not touch the history either.
        drawing_adapter.toggle_visibility()
        drawing_adapter.toggle_visibility()
        _paint(canvas)
        assert history_renders == [3, 1]

        # Undo is not an append: the layer is rebuilt without the stroke.
        drawing_adapter.undo()
        image = _paint(canvas)
        assert history_renders == [3, 1, 3]
        assert image.pixelColor(30, 40).alpha() == 0
        assert image.pixelColor(10, 15).alpha() > 0
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


def _reference(canvas: DrawingCanvas, strokes) -> QImage:
    image = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        DrawingEngine.render_strokes(painter, strokes)
    finally:
        painter.end()
    return image


def test_history_rebuilds_are_bounded_by_the_undo_reach(tmp_path, monkeypatch) -> None:
    import ui.quick.drawing_canvas as drawing_canvas

    reach = 2
    monkeypatch.setattr(drawing_canvas, "_UNDO_REACH", reach)
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(drawing_adapter)
    canvas.setWidth(64)
    canvas.setHeight(64)
    drawing_adapter.toggle_drawing()

    rendered: list[int] = []
    original = DrawingEngine.render_strokes

    def counting_render(painter, strokes):
        rendered.append(len(strokes))
        original(painter, strokes)

    monkeypatch.setattr(DrawingEngine, "render_strokes", staticmethod(counting_render))

    def step(action) -> int:
        rendered.clear()
        action()
        image = _paint(canvas)
        total = sum(rendered)
        assert image == _reference(canvas, drawing_adapter.strokes_snapshot())
        return total

    try:
        for index in range(12):
            y = 3 + 5 * index

            def draw(y=y):
                canvas._begin_stroke(QPointF(5, y))
                canvas._finish_stroke(QPointF(60, y))

            # The new stroke, plus occasionally freezing reach + 1 older ones.
            assert step(draw) <= reach + 2
        for action in (drawing_adapter.undo, drawing_adapter.undo, drawing_adapter.redo):
            # Only the tail beyond the frozen base is redrawn, not all 12 strokes.
            assert step(action) <= 2 * reach

        assert step(drawing_adapter.clear_screen) == 0
        assert canvas._committed_layer is None
        assert step(drawing_adapter.undo) <= 2 * reach
    finally:
        canvas.deleteLater()
        drawing_adapter.close()
        tool_adapter.close()
        settings.close()
        _APP.processEvents()


def test_empty_canvas_holds_no_layer(tmp_path) -> None:
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    canvas = DrawingCanvas(drawing_adapter)
    canvas.setWidth(64)
    canvas.setHeight(64)
    try:
        _paint(canvas)
        assert canvas._committed_layer is None
    finally:
        canvas.deleteLater()
        drawing_adapter.close()
        tool_adapter.close()
        settings.close()
        _APP.processEvents()


def test_eraser_cursor_matches_eraser_size(tmp_path, overlay_window_component) -> None:
    settings, controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    surface = OverlaySurface(
        drawing_adapter, tool_adapter, window_component=overlay_window_component
    )
    try:
        drawing_adapter.toggle_drawing()
        tool_adapter.select_tool("eraser")
        tool_adapter.set_size(80)
        _APP.processEvents()

        window = surface.windows[0]
        pixmap = window.cursor().pixmap()
        logical_width = pixmap.width() / pixmap.devicePixelRatio()
        assert 80 <= logical_width <= 90

        tool_adapter.set_size(20)
        _APP.processEvents()
        pixmap = window.cursor().pixmap()
        logical_width = pixmap.width() / pixmap.devicePixelRatio()
        assert 20 <= logical_width <= 30

        tool_adapter.select_tool("pen")
        _APP.processEvents()
        assert window.cursor().shape() == Qt.CursorShape.CrossCursor
    finally:
        _close(surface, settings, drawing_adapter, tool_adapter)


def test_eraser_cursor_uses_integer_scale_for_fractional_ratio() -> None:
    from ui.quick.overlay_surface import _create_eraser_cursor

    pixmap = _create_eraser_cursor(19, 1.5).pixmap()
    assert pixmap.devicePixelRatio() == 2
    assert pixmap.width() % 2 == 0
    assert 19 <= pixmap.width() / 2 <= 25


def test_eraser_cursor_follows_window_device_pixel_ratio_change(
    tmp_path, overlay_window_component
) -> None:
    from PySide6.QtCore import QEvent

    settings, _controller, drawing_adapter, tool_adapter = _adapters(tmp_path)
    surface = OverlaySurface(
        drawing_adapter, tool_adapter, window_component=overlay_window_component
    )
    try:
        drawing_adapter.toggle_drawing()
        tool_adapter.select_tool("eraser")
        window = surface.windows[0]
        window.setCursor(Qt.CursorShape.ArrowCursor)
        _APP.sendEvent(window, QEvent(QEvent.Type.DevicePixelRatioChange))
        assert window.cursor().shape() == Qt.CursorShape.BitmapCursor
    finally:
        _close(surface, settings, drawing_adapter, tool_adapter)
