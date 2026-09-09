"""Adapter Qt/QML per lo stato e le azioni di disegno."""

from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.app_controller import AppController
from core.event_bus import event_bus
from core.models import Stroke


class DrawingAdapter(QObject):
    """Boundary UI focalizzato sul workflow di disegno.

    Le Property/Slot costituiscono l'API QML. I metodi Python non decorati sono
    usati dal QQuickPaintedItem e mantengono il controller/core fuori da QML.

    Gli Slot mantengono il nome Python originale. PySide6 6.11.2 con Python
    3.14 puo' andare in crash quando QML invoca uno Slot rinominato tramite
    ``@Slot(name=...)``; il boundary usa quindi direttamente snake_case.
    """

    activeChanged = Signal()
    annotationsVisibleChanged = Signal()
    historyChanged = Signal()
    repaintRequested = Signal()

    def __init__(self, controller: AppController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._closed = False
        event_bus.subscribe("drawing_toggled", self._on_drawing_toggled)
        event_bus.subscribe("visibility_toggled", self._on_visibility_toggled)
        event_bus.subscribe("strokes_changed", self._on_history_changed)

    def close(self) -> None:
        """Rimuove in modo idempotente le subscription possedute dall'adapter."""
        if self._closed:
            return
        self._closed = True
        event_bus.unsubscribe("drawing_toggled", self._on_drawing_toggled)
        event_bus.unsubscribe("visibility_toggled", self._on_visibility_toggled)
        event_bus.unsubscribe("strokes_changed", self._on_history_changed)

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

    # API Python-only del canvas. Non e' esposta come Slot a QML.
    def create_current_stroke(self) -> Stroke:
        return self._controller.create_stroke(self._controller.get_current_tool())

    def finalize_stroke(self, stroke: Stroke) -> None:
        self._controller.finalize_stroke(stroke)

    def strokes_snapshot(self) -> list[Stroke]:
        return self._controller.stroke_manager.get_strokes()

    def _on_drawing_toggled(self, **_kwargs) -> None:
        self.activeChanged.emit()

    def _on_visibility_toggled(self, **_kwargs) -> None:
        self.annotationsVisibleChanged.emit()
        self.repaintRequested.emit()

    def _on_history_changed(self, **_kwargs) -> None:
        self.historyChanged.emit()
        self.repaintRequested.emit()
