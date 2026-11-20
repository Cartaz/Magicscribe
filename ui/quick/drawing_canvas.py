"""Canvas Qt Quick che riusa il renderer QPainter esistente."""

from __future__ import annotations

import math
import operator

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
from PySide6.QtQuick import QQuickPaintedItem

from core.models import Point, Stroke
from core.stroke_manager import UNDO_MAX_DEPTH
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.drawing_engine import DrawingEngine

# Tratti che una sequenza di undo puo' togliere dalla coda dello snapshot.
_UNDO_REACH = UNDO_MAX_DEPTH


def _fits(layer: QImage | None, size: tuple[int, int, float]) -> bool:
    width, height, ratio = size
    return (
        layer is not None
        and layer.width() == width
        and layer.height() == height
        and layer.devicePixelRatio() == ratio
    )


def _starts_with(strokes: list[Stroke], prefix: list[Stroke]) -> bool:
    return len(prefix) <= len(strokes) and all(map(operator.is_, prefix, strokes))


def _blank_layer(size: tuple[int, int, float]) -> QImage:
    width, height, ratio = size
    layer = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    layer.setDevicePixelRatio(ratio)
    layer.fill(Qt.GlobalColor.transparent)
    return layer


class DrawingCanvas(QQuickPaintedItem):
    """Superficie di disegno con coordinate canoniche globali del desktop.

    I tratti gia' committati vivono in un layer cache: un nuovo tratto viene
    aggiunto al layer esistente, mentre undo/redo/clear, origine o dimensione
    lo ricostruiscono partendo da una base congelata dei tratti fuori dalla
    portata dell'undo. Durante il disegno ogni frame compone il layer e il
    solo tratto in corso.
    """

    def __init__(
        self,
        adapter: DrawingAdapter,
        parent=None,
        *,
        global_origin: QPointF | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._current_stroke: Stroke | None = None
        self._global_origin = QPointF(global_origin or QPointF())
        self._committed_layer: QImage | None = None
        self._layer_strokes: list[Stroke] = []
        self._layer_stale = True
        self._base_layer: QImage | None = None
        self._base_strokes: list[Stroke] = []

        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton
            if adapter.active
            else Qt.MouseButton.NoButton
        )
        self.setAntialiasing(True)
        self.setOpaquePainting(False)
        self.setFillColor(QColor(0, 0, 0, 0))

        adapter.historyChanged.connect(self._on_history_changed)
        adapter.annotationsVisibleChanged.connect(self.update)
        adapter.activeChanged.connect(self._on_active_changed)

    def set_global_origin(self, origin: QPointF) -> None:
        """Imposta l'origine globale corrispondente al pixel locale (0, 0)."""
        if self._global_origin == origin:
            return
        self._global_origin = QPointF(origin)
        self._committed_layer = None
        self._base_layer = None
        self._layer_stale = True
        self.update()

    def global_origin(self) -> QPointF:
        return QPointF(self._global_origin)

    def paint(self, painter: QPainter) -> None:
        """Renderizza lo snapshot globale nella porzione di desktop locale."""
        if not self._adapter.annotationsVisible:
            return

        layer = self._committed_strokes_layer()
        if layer is not None:
            painter.drawImage(QPointF(0, 0), layer)
        if self._current_stroke is None:
            return

        painter.save()
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.translate(-self._global_origin.x(), -self._global_origin.y())
            DrawingEngine.render_stroke(painter, self._current_stroke)
        finally:
            painter.restore()

    def _committed_strokes_layer(self) -> QImage | None:
        window = self.window()
        ratio = window.effectiveDevicePixelRatio() if window is not None else 1.0
        size = (
            max(1, math.ceil(self.width() * ratio)),
            max(1, math.ceil(self.height() * ratio)),
            ratio,
        )
        if not self._layer_stale:
            if not self._layer_strokes:
                return None
            if _fits(self._committed_layer, size):
                return self._committed_layer

        strokes = self._adapter.strokes_snapshot()
        previous, self._layer_strokes = self._layer_strokes, strokes
        self._layer_stale = False
        if not strokes:
            # Nessun buffer full-screen finche' non c'e' nulla da mostrare.
            self._committed_layer = None
            return None

        layer = self._committed_layer
        if (
            _fits(layer, size)
            and len(strokes) == len(previous) + 1
            and _starts_with(strokes, previous)
        ):
            self._paint_on_layer(layer, strokes[-1:])
        else:
            self._committed_layer = None
            base, covered = self._frozen_base(strokes, size)
            layer = base.copy() if base is not None else _blank_layer(size)
            self._paint_on_layer(layer, strokes[covered:])
            self._committed_layer = layer
        self._frozen_base(strokes, size)
        return layer

    def _frozen_base(
        self, strokes: list[Stroke], size: tuple[int, int, float]
    ) -> tuple[QImage | None, int]:
        """Immagine dei tratti che l'undo non puo' piu' raggiungere.

        Undo/redo toccano solo la coda dello snapshot: tenendo congelato il
        prefisso, una ricostruzione ridisegna al massimo ``2 * _UNDO_REACH``
        tratti invece dell'intera sessione.
        """
        base = self._base_layer
        covered = len(self._base_strokes)
        if not (
            _fits(base, size)
            and covered <= len(strokes)
            and _starts_with(strokes, self._base_strokes)
        ):
            base, covered = None, 0
        target = len(strokes) - _UNDO_REACH
        if target - covered > _UNDO_REACH or (base is None and target > 0):
            advanced = base.copy() if base is not None else _blank_layer(size)
            self._paint_on_layer(advanced, strokes[covered:target])
            self._base_layer, self._base_strokes = advanced, strokes[:target]
            return advanced, target
        return base, covered

    def _paint_on_layer(self, layer: QImage, strokes: list[Stroke]) -> None:
        layer_painter = QPainter(layer)
        try:
            layer_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            layer_painter.translate(-self._global_origin.x(), -self._global_origin.y())
            DrawingEngine.render_strokes(layer_painter, strokes)
        finally:
            layer_painter.end()

    def _on_history_changed(self) -> None:
        self._layer_stale = True
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            not self._adapter.active
            or event.button() != Qt.MouseButton.LeftButton
        ):
            event.ignore()
            return

        self._begin_stroke(event.position())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._current_stroke is None:
            event.ignore()
            return

        self._extend_stroke(event.position())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            self._current_stroke is None
            or event.button() != Qt.MouseButton.LeftButton
        ):
            event.ignore()
            return

        self._finish_stroke(event.position())
        event.accept()

    def _begin_stroke(self, position: QPointF) -> None:
        stroke = self._adapter.create_current_stroke()
        point = self._point(position)
        stroke.points.append(point)
        if stroke.is_shape():
            stroke.points.append(self._point(position))
        self._current_stroke = stroke
        self.update()

    def _extend_stroke(self, position: QPointF) -> None:
        stroke = self._current_stroke
        if stroke is None:
            return

        point = self._point(position)
        if stroke.is_shape():
            stroke.points[-1] = point
        else:
            stroke.points.append(point)
        self.update()

    def _finish_stroke(self, position: QPointF) -> None:
        stroke = self._current_stroke
        if stroke is None:
            return

        point = self._point(position)
        if stroke.is_shape():
            stroke.points[-1] = point
        else:
            stroke.points.append(point)

        self._current_stroke = None
        self._adapter.finalize_stroke(stroke)
        self.update()

    def _on_active_changed(self) -> None:
        active = self._adapter.active
        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton if active else Qt.MouseButton.NoButton
        )
        if active:
            return

        # Accepting a mouse press gives a QQuickItem an exclusive pointer grab
        # until release. If drawing is disabled while that grab is still alive,
        # the wl_surface can already be click-through while Qt Quick keeps
        # routing pointer events to this item. Release the grab explicitly before
        # returning control to the desktop.
        self.setKeepMouseGrab(False)
        self.ungrabMouse()

        if self._current_stroke is not None:
            self._current_stroke = None
            self.update()

    def _point(self, position: QPointF) -> Point:
        return Point(
            x=position.x() + self._global_origin.x(),
            y=position.y() + self._global_origin.y(),
        )
