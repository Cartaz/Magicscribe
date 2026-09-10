"""Motore di rendering dei tratti di disegno.

Responsabile della resa grafica dei tratti su un QPainter,
gestendo i diversi tipi di strumento supportati dal runtime.

Questo modulo risiede in ui/ perche' importa PySide6; il livello core
rimane framework-agnostic.
"""

from __future__ import annotations

import logging
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen

from core.models import Point, Stroke, ToolType

logger = logging.getLogger(__name__)

_SO = QPainter.CompositionMode.CompositionMode_SourceOver
_SMOOTH_CONTROL_SPACING = 32.0
_SMOOTH_ALPHA = 0.28


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

        # Il corpo usa soli control point stabilizzati e quindi non cambia piu'.
        # La coda collega la spline all'ultimo campione grezzo mentre si disegna.
        if filtered:
            tail = QPainterPath(path.currentPosition())
            raw_last = stroke.points[-1]
            filtered_last = filtered[-1]
            tail.quadTo(
                filtered_last.x,
                filtered_last.y,
                raw_last.x,
                raw_last.y,
            )
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
    def _resample_smooth_controls(
        points: list[Point],
        spacing: float = _SMOOTH_CONTROL_SPACING,
    ) -> list[Point]:
        """Ricampiona la polilinea a distanza spaziale fissa e append-stable.

        Gli eventi mouse possono arrivare molto fitti: usare ogni evento come
        control point rende qualunque spline quasi identica alla Penna. Qui i
        control point vengono emessi ogni ``spacing`` pixel di lunghezza d'arco.
        Un campione parziale finale non viene consolidato, quindi aggiungere
        nuovi punti puo' soltanto appendere nuovi control point senza cambiare
        quelli precedenti.
        """
        if not points:
            return []
        if spacing <= 0:
            return list(points)

        sampled = [points[0]]
        distance_since_sample = 0.0
        previous = points[0]

        for current in points[1:]:
            start_x = previous.x
            start_y = previous.y
            end_x = current.x
            end_y = current.y
            dx = end_x - start_x
            dy = end_y - start_y
            segment_length = math.hypot(dx, dy)

            while (
                segment_length > 0.0
                and distance_since_sample + segment_length >= spacing
            ):
                needed = spacing - distance_since_sample
                ratio = needed / segment_length
                sample = Point(
                    start_x + dx * ratio,
                    start_y + dy * ratio,
                )
                sampled.append(sample)

                start_x = sample.x
                start_y = sample.y
                dx = end_x - start_x
                dy = end_y - start_y
                segment_length = math.hypot(dx, dy)
                distance_since_sample = 0.0

            distance_since_sample += segment_length
            previous = current

        return sampled

    @staticmethod
    def _smooth_points(points: list[Point]) -> list[Point]:
        """Crea control point spaziali e applica un low-pass causale forte."""
        sampled = DrawingEngine._resample_smooth_controls(points)
        if not sampled:
            return []

        filtered = [sampled[0]]
        keep = 1.0 - _SMOOTH_ALPHA
        for current in sampled[1:]:
            previous = filtered[-1]
            filtered.append(
                Point(
                    keep * previous.x + _SMOOTH_ALPHA * current.x,
                    keep * previous.y + _SMOOTH_ALPHA * current.y,
                )
            )
        return filtered

    @staticmethod
    def _smooth_path(points: list[Point]) -> QPainterPath:
        """Costruisce il corpo consolidato del tratto Smooth."""
        return DrawingEngine._smooth_path_from_filtered(
            DrawingEngine._smooth_points(points)
        )

    @staticmethod
    def _smooth_path_from_filtered(points: list[Point]) -> QPainterPath:
        """Renderizza una B-spline cubica uniforme, locale e append-stable."""
        path = QPainterPath()
        if not points:
            return path
        if len(points) == 1:
            path.moveTo(points[0].x, points[0].y)
            return path

        controls = [points[0], points[0], *points]

        for index in range(len(controls) - 3):
            p0, p1, p2, p3 = controls[index:index + 4]
            b0 = QPointF(
                (p0.x + 4 * p1.x + p2.x) / 6,
                (p0.y + 4 * p1.y + p2.y) / 6,
            )
            b1 = QPointF(
                (2 * p1.x + p2.x) / 3,
                (2 * p1.y + p2.y) / 3,
            )
            b2 = QPointF(
                (p1.x + 2 * p2.x) / 3,
                (p1.y + 2 * p2.y) / 3,
            )
            b3 = QPointF(
                (p1.x + 4 * p2.x + p3.x) / 6,
                (p1.y + 4 * p2.y + p3.y) / 6,
            )

            if index == 0:
                path.moveTo(b0)
            path.cubicTo(b1, b2, b3)

        return path
