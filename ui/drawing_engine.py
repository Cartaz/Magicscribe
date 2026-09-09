"""Motore di rendering dei tratti di disegno.

Responsabile della resa grafica dei tratti su un QPainter,
gestendo i diversi tipi di strumento supportati dal runtime.

Questo modulo risiede in ui/ perche' importa PySide6; il livello core
rimane framework-agnostic.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen

from core.models import Point, Stroke, ToolType

logger = logging.getLogger(__name__)

_SO = QPainter.CompositionMode.CompositionMode_SourceOver


def _qcolor(color_str: str) -> QColor:
    """Converte una stringa colore in QColor restituendo sempre un colore valido."""
    if not color_str:
        return QColor("#000000")
    if color_str.startswith("rgba("):
        inner = color_str[5:-1]
        parts = [p.strip() for p in inner.split(",")]
        if len(parts) == 4:
            try:
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                a = int(float(parts[3]) * 255)
                return QColor(r, g, b, a)
            except (ValueError, TypeError):
                logger.warning("Colore rgba malformato: %r, uso nero", color_str)
                return QColor("#000000")
    color = QColor(color_str)
    if not color.isValid():
        logger.warning("Colore non valido: %r, uso nero", color_str)
        return QColor("#000000")
    return color


class DrawingEngine:
    """Motore di rendering per i tratti di disegno."""

    @staticmethod
    def render_stroke(painter: QPainter, stroke: Stroke) -> None:
        """Renderizza un singolo tratto su un QPainter."""
        if not stroke.points:
            return
        painter.save()
        dispatch = {
            ToolType.ERASER: DrawingEngine._render_eraser,
            ToolType.PEN: DrawingEngine._render_freehand,
            ToolType.SMOOTH: DrawingEngine._render_smooth,
            ToolType.LINE: DrawingEngine._render_line,
            ToolType.RECT: DrawingEngine._render_rect,
            ToolType.CIRCLE: DrawingEngine._render_circle,
        }
        handler = dispatch.get(stroke.tool_type)
        if handler:
            handler(painter, stroke)
        painter.restore()

    @staticmethod
    def render_strokes(painter: QPainter, strokes: list[Stroke]) -> None:
        """Renderizza una lista di tratti in ordine."""
        for stroke in strokes:
            DrawingEngine.render_stroke(painter, stroke)

    @staticmethod
    def _render_freehand(painter: QPainter, stroke: Stroke) -> None:
        color = _qcolor(stroke.color)
        pen = QPen(
            QBrush(color), stroke.size, Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin,
        )
        painter.setCompositionMode(_SO)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(stroke.points[0].x, stroke.points[0].y)
        for pt in stroke.points[1:]:
            path.lineTo(pt.x, pt.y)
        painter.drawPath(path)

    @staticmethod
    def _render_smooth(painter: QPainter, stroke: Stroke) -> None:
        color = _qcolor(stroke.color)
        pen = QPen(
            QBrush(color), stroke.size, Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin,
        )
        painter.setCompositionMode(_SO)
        painter.setPen(pen)

        filtered = DrawingEngine._smooth_points(stroke.points)
        path = DrawingEngine._smooth_path_from_filtered(filtered)
        painter.drawPath(path)

        # Il corpo del tratto e' append-stable. Solo la mezza coda finale e'
        # provvisoria, cosi' il cursore resta collegato senza poter deformare
        # segmenti ormai consolidati quando arrivano nuovi campioni.
        if len(filtered) >= 2:
            tail = QPainterPath(path.currentPosition())
            last = filtered[-1]
            tail.quadTo(last.x, last.y, last.x, last.y)
            painter.drawPath(tail)

    @staticmethod
    def _render_eraser(painter: QPainter, stroke: Stroke) -> None:
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Clear
        )
        pen = QPen(
            QBrush(QColor(0, 0, 0, 0)), stroke.size,
            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(stroke.points[0].x, stroke.points[0].y)
        for pt in stroke.points[1:]:
            path.lineTo(pt.x, pt.y)
        painter.drawPath(path)

    @staticmethod
    def _render_line(painter: QPainter, stroke: Stroke) -> None:
        if len(stroke.points) < 2:
            return
        color = _qcolor(stroke.color)
        painter.setCompositionMode(_SO)
        painter.setPen(QPen(
            QBrush(color), stroke.size, Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        ))
        p1, p2 = stroke.points[0], stroke.points[-1]
        painter.drawLine(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y))

    @staticmethod
    def _render_rect(painter: QPainter, stroke: Stroke) -> None:
        if len(stroke.points) < 2:
            return
        color = _qcolor(stroke.color)
        painter.setCompositionMode(_SO)
        painter.setPen(QPen(QBrush(color), stroke.size, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        p1, p2 = stroke.points[0], stroke.points[-1]
        painter.drawRect(QRectF(
            QPointF(p1.x, p1.y), QPointF(p2.x, p2.y),
        ).normalized())

    @staticmethod
    def _render_circle(painter: QPainter, stroke: Stroke) -> None:
        if len(stroke.points) < 2:
            return
        color = _qcolor(stroke.color)
        painter.setCompositionMode(_SO)
        painter.setPen(QPen(QBrush(color), stroke.size, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        p1, p2 = stroke.points[0], stroke.points[-1]
        painter.drawEllipse(QRectF(
            QPointF(p1.x, p1.y), QPointF(p2.x, p2.y),
        ).normalized())

    @staticmethod
    def _smooth_points(points: list[Point]) -> list[Point]:
        """Filtra causalmente i campioni senza modificare quelli gia' prodotti."""
        if not points:
            return []
        if len(points) == 1:
            return [points[0]]

        filtered = [
            points[0],
            Point(
                0.30 * points[0].x + 0.70 * points[1].x,
                0.30 * points[0].y + 0.70 * points[1].y,
            ),
        ]
        for index in range(2, len(points)):
            older = points[index - 2]
            previous = points[index - 1]
            current = points[index]
            filtered.append(
                Point(
                    0.15 * older.x + 0.30 * previous.x + 0.55 * current.x,
                    0.15 * older.y + 0.30 * previous.y + 0.55 * current.y,
                )
            )
        return filtered

    @staticmethod
    def _smooth_path(points: list[Point]) -> QPainterPath:
        """Costruisce il corpo consolidato di un tratto Smooth.

        I punti vengono filtrati causalmente e poi collegati con curve
        quadratiche tra i midpoint consecutivi. L'aggiunta di nuovi campioni
        appende nuovi segmenti senza cambiare quelli gia' consolidati.
        """
        return DrawingEngine._smooth_path_from_filtered(
            DrawingEngine._smooth_points(points)
        )

    @staticmethod
    def _smooth_path_from_filtered(points: list[Point]) -> QPainterPath:
        path = QPainterPath()
        if not points:
            return path

        path.moveTo(points[0].x, points[0].y)
        if len(points) == 1:
            return path

        first_mid = QPointF(
            (points[0].x + points[1].x) / 2,
            (points[0].y + points[1].y) / 2,
        )
        path.lineTo(first_mid)

        for index in range(1, len(points) - 1):
            current = points[index]
            following = points[index + 1]
            next_mid = QPointF(
                (current.x + following.x) / 2,
                (current.y + following.y) / 2,
            )
            path.quadTo(current.x, current.y, next_mid.x(), next_mid.y())

        return path
