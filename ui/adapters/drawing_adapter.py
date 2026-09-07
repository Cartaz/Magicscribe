"""Adapter QML per lo stato e le azioni di disegno."""

from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.app_controller import AppController
from core.event_bus import event_bus


class DrawingAdapter(QObject):
    """Espone a QML la minima API necessaria per il workflow di disegno."""

    activeChanged = Signal()
    annotationsVisibleChanged = Signal()
    historyChanged = Signal()

    def __init__(self, controller: AppController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        event_bus.subscribe("drawing_toggled", self._on_drawing_toggled)
        event_bus.subscribe("visibility_toggled", self._on_visibility_toggled)
        event_bus.subscribe("strokes_changed", self._on_history_changed)

    def _get_active(self) -> bool:
        return self._controller.is_drawing_active()

    active = Property(bool, _get_active, notify=activeChanged)

    def _get_annotations_visible(self) -> bool:
        return self._controller.is_visible()

    annotationsVisible = Property(
        bool,
        _get_annotations_visible,
        notify=annotationsVisibleChanged,
    )

    def _get_can_undo(self) -> bool:
        return self._controller.stroke_manager.can_undo

    canUndo = Property(bool, _get_can_undo, notify=historyChanged)

    def _get_can_redo(self) -> bool:
        return self._controller.stroke_manager.can_redo

    canRedo = Property(bool, _get_can_redo, notify=historyChanged)

    def _get_stroke_count(self) -> int:
        return self._controller.stroke_manager.stroke_count

    strokeCount = Property(int, _get_stroke_count, notify=historyChanged)

    @Slot(name="toggleDrawing")
    def toggle_drawing(self) -> None:
        self._controller.toggle_drawing()

    @Slot(name="toggleVisibility")
    def toggle_visibility(self) -> None:
        self._controller.toggle_visibility()

    @Slot(name="clearScreen")
    def clear_screen(self) -> None:
        self._controller.clear_screen()

    @Slot()
    def undo(self) -> None:
        self._controller.undo()

    @Slot()
    def redo(self) -> None:
        self._controller.redo()

    def _on_drawing_toggled(self, **_kwargs) -> None:
        self.activeChanged.emit()

    def _on_visibility_toggled(self, **_kwargs) -> None:
        self.annotationsVisibleChanged.emit()

    def _on_history_changed(self, **_kwargs) -> None:
        self.historyChanged.emit()
