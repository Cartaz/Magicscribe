"""Regression guard for releasing Quick pointer input when drawing stops."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from core.app_controller import AppController
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.quick.drawing_canvas import DrawingCanvas

_APP = QApplication.instance() or QApplication([])


def test_canvas_stops_accepting_mouse_when_drawing_turns_off(tmp_path) -> None:
    settings = Settings(path=tmp_path / "input.json")
    controller = AppController(settings)
    adapter = DrawingAdapter(controller)
    canvas = DrawingCanvas(adapter)
    try:
        assert canvas.acceptedMouseButtons() == Qt.MouseButton.NoButton
        adapter.toggle_drawing()
        _APP.processEvents()
        assert canvas.acceptedMouseButtons() == Qt.MouseButton.LeftButton
        adapter.toggle_drawing()
        _APP.processEvents()
        assert canvas.acceptedMouseButtons() == Qt.MouseButton.NoButton
    finally:
        canvas.deleteLater()
        adapter.close()
        settings.close()
        _APP.processEvents()


def test_deactivation_mid_stroke_drops_the_stroke_and_mouse_grab(tmp_path) -> None:
    settings = Settings(path=tmp_path / "input.json")
    controller = AppController(settings)
    adapter = DrawingAdapter(controller)
    canvas = DrawingCanvas(adapter)
    try:
        adapter.toggle_drawing()
        canvas.setKeepMouseGrab(True)
        canvas._begin_stroke(QPointF(1, 1))
        canvas._extend_stroke(QPointF(5, 5))

        adapter.toggle_drawing()
        _APP.processEvents()

        assert canvas._current_stroke is None
        assert canvas.keepMouseGrab() is False
        assert controller.stroke_count() == 0
    finally:
        canvas.deleteLater()
        adapter.close()
        settings.close()
        _APP.processEvents()
