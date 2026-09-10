"""Adapter Qt/QML per stato e azioni di disegno."""

from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.app_controller import AppController
from core.models import Stroke


class DrawingAdapter(QObject):
    """Boundary QML sottile; ogni mutazione passa da AppController."""

    activeChanged = Signal()
    annotationsVisibleChanged = Signal()
    historyChanged = Signal()
    repaintRequested = Signal()

    def __init__(self, controller: AppController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._closed = False
        controller.add_drawing_listener(self._on_drawing_changed)
        controller.add_visibility_listener(self._on_visibility_changed)
        controller.add_history_listener(self._on_history_changed)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._controller.remove_drawing_listener(self._on_drawing_changed)
        self._controller.remove_visibility_listener(self._on_visibility_changed)
        self._controller.remove_history_listener(self._on_history_changed)

    active = Property(bool, lambda self: self._controller.is_drawing_active(), notify=activeChanged)
    annotationsVisible = Property(
        bool,
        lambda self: self._controller.is_visible(),
        notify=annotationsVisibleChanged,
    )
    canUndo = Property(bool, lambda self: self._controller.can_undo(), notify=historyChanged)
    canRedo = Property(bool, lambda self: self._controller.can_redo(), notify=historyChanged)
    strokeCount = Property(int, lambda self: self._controller.stroke_count(), notify=historyChanged)

    @Slot()
    def toggle_drawing(self) -> None:
        self._controller.toggle_drawing()

    @Slot()
    def toggle_visibility(self) -> None:
        self._controller.toggle_visibility()

    @Slot()
    def clear_screen(self) -> None:
        self._controller.clear_screen()

    @Slot()
    def undo(self) -> None:
        self._controller.undo()

    @Slot()
    def redo(self) -> None:
        self._controller.redo()

    def create_current_stroke(self) -> Stroke:
        return self._controller.create_stroke(self._controller.get_current_tool())

    def finalize_stroke(self, stroke: Stroke) -> None:
        self._controller.finalize_stroke(stroke)

    def strokes_snapshot(self) -> list[Stroke]:
        return self._controller.strokes_snapshot()

    def _on_drawing_changed(self) -> None:
        self.activeChanged.emit()

    def _on_visibility_changed(self) -> None:
        self.annotationsVisibleChanged.emit()
        self.repaintRequested.emit()

    def _on_history_changed(self) -> None:
        self.historyChanged.emit()
        self.repaintRequested.emit()
