"""Regression guard for releasing Quick pointer input when drawing stops."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
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


def test_deactivation_explicitly_releases_quick_mouse_grab() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "ui" / "quick" / "drawing_canvas.py"
    ).read_text(encoding="utf-8")
    assert "self.setKeepMouseGrab(False)" in source
    assert "self.ungrabMouse()" in source
