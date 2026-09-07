"""Canvas Qt Quick che riusa il renderer QPainter esistente."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtQuick import QQuickPaintedItem

from core.models import Point, Stroke
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.drawing_engine import DrawingEngine


class DrawingCanvas(QQuickPaintedItem):
    """Superficie di disegno Qt Quick con stato di gesture solo temporaneo."""

    def __init__(
        self,
        adapter: DrawingAdapter,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._current_stroke: Stroke | None = None

        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setAntialiasing(True)
        self.setOpaquePainting(False)
        self.setFillColor(QColor(0, 0, 0, 0))

        adapter.repaintRequested.connect(self.update)
        adapter.activeChanged.connect(self._on_active_changed)

    def paint(self, painter: QPainter) -> None:
        """Renderizza snapshot canonico + preview della gesture corrente."""
        if not self._adapter.annotationsVisible:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        DrawingEngine.render_strokes(painter, self._adapter.strokes_snapshot())
        if self._current_stroke is not None:
            DrawingEngine.render_stroke(painter, self._current_stroke)

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
        point = self._point(position, pressure=1.0)
        stroke.points.append(point)
        if stroke.is_shape():
            stroke.points.append(self._point(position))
        self._current_stroke = stroke
        self.update()

    def _extend_stroke(self, position: QPointF) -> None:
        stroke = self._current_stroke
        if stroke is None:
            return

        point = self._point(position, pressure=1.0)
        if stroke.is_shape():
            stroke.points[-1] = point
        else:
            stroke.points.append(point)
        self.update()

    def _finish_stroke(self, position: QPointF) -> None:
        stroke = self._current_stroke
        if stroke is None:
            return

        point = self._point(position, pressure=1.0)
        if stroke.is_shape():
            stroke.points[-1] = point
        else:
            stroke.points.append(point)

        self._current_stroke = None
        self._adapter.finalize_stroke(stroke)
        self.update()

    def _on_active_changed(self) -> None:
        if not self._adapter.active and self._current_stroke is not None:
            self._current_stroke = None
            self.update()

    @staticmethod
    def _point(position: QPointF, pressure: float = 1.0) -> Point:
        return Point(x=position.x(), y=position.y(), pressure=pressure)
