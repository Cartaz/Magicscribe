"""Motore QPainter dei tratti; gli algoritmi geometrici puri restano nel core."""

from __future__ import annotations

import logging
import math

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QPolygonF

from core.geometry import rdp_simplify
from core.models import Stroke, ToolType, Point

logger = logging.getLogger(__name__)
_SO = QPainter.CompositionMode.CompositionMode_SourceOver


def _qcolor(color_str: str) -> QColor:
    if not color_str:
        return QColor("#000000")
    if color_str.startswith("rgba("):
        parts = [p.strip() for p in color_str[5:-1].split(",")]
        if len(parts) == 4:
            try:
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                a = int(float(parts[3]) * 255)
                return QColor(r, g, b, a)
            except (ValueError, TypeError):
                logger.warning("Colore rgba malformato: %r", color_str)
                return QColor("#000000")
    color = QColor(color_str)
    if not color.isValid():
        logger.warning("Colore non valido: %r, uso nero", color_str)
        return QColor("#000000")
    return color


class DrawingEngine:
    @staticmethod
    def render_stroke(painter: QPainter, stroke: Stroke) -> None:
        if not stroke.points:
            return
        painter.save()
        dispatch = {ToolType.ERASER: DrawingEngine._render_eraser, ToolType.PEN: DrawingEngine._render_freehand, ToolType.SMOOTH: DrawingEngine._render_smooth, ToolType.LINE: DrawingEngine._render_line, ToolType.RECT: DrawingEngine._render_rect, ToolType.CIRCLE: DrawingEngine._render_circle}
        handler = dispatch.get(stroke.tool_type)
        if handler:
            handler(painter, stroke)
        painter.restore()

    @staticmethod
    def render_strokes(painter: QPainter, strokes: list[Stroke]) -> None:
        for stroke in strokes:
            DrawingEngine.render_stroke(painter, stroke)

    @staticmethod
    def _render_freehand(painter: QPainter, stroke: Stroke) -> None:
        color = _qcolor(stroke.color)
        pen = QPen(QBrush(color), stroke.size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setCompositionMode(_SO)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(stroke.points[0].x, stroke.points[0].y)
        for pt in stroke.points[1:]:
            path.lineTo(pt.x, pt.y)
        painter.drawPath(path)
        if stroke.arrow_size > 0 and len(stroke.points) >= 2:
            DrawingEngine._draw_arrow(painter, stroke, color)

    @staticmethod
    def _render_smooth(painter: QPainter, stroke: Stroke) -> None:
        color = _qcolor(stroke.color)
        pen = QPen(QBrush(color), stroke.size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setCompositionMode(_SO)
        painter.setPen(pen)
        painter.drawPath(DrawingEngine._smooth_path(stroke.points, tolerance=10.0))

    @staticmethod
    def _render_eraser(painter: QPainter, stroke: Stroke) -> None:
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.setPen(QPen(QBrush(QColor(0, 0, 0, 0)), stroke.size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
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
        painter.setPen(QPen(QBrush(color), stroke.size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p1, p2 = stroke.points[0], stroke.points[-1]
        painter.drawLine(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y))

    @staticmethod
    def _render_rect(painter: QPainter, stroke: Stroke) -> None:
        if len(stroke.points) < 2:
            return
        color = _qcolor(stroke.color)
        painter.setCompositionMode(_SO)
        painter.setPen(QPen(QBrush(color), stroke.size, Qt.PenStyle.SolidLine))
        p1, p2 = stroke.points[0], stroke.points[-1]
        painter.drawRect(QRectF(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y)).normalized())

    @staticmethod
    def _render_circle(painter: QPainter, stroke: Stroke) -> None:
        if len(stroke.points) < 2:
            return
        color = _qcolor(stroke.color)
        painter.setCompositionMode(_SO)
        painter.setPen(QPen(QBrush(color), stroke.size, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush(_qcolor(stroke.fill_color)) if stroke.fill_color else Qt.BrushStyle.NoBrush)
        p1, p2 = stroke.points[0], stroke.points[-1]
        painter.drawEllipse(QRectF(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y)).normalized())

    @staticmethod
    def _draw_arrow(painter: QPainter, stroke: Stroke, color: QColor) -> None:
        p_end = stroke.points[-1]
        p_prev = stroke.points[-2]
        angle = math.atan2(p_end.y - p_prev.y, p_end.x - p_prev.x)
        arrow_len = stroke.size * stroke.arrow_size * 3
        p1x = p_end.x - arrow_len * math.cos(angle - math.pi / 6)
        p1y = p_end.y - arrow_len * math.sin(angle - math.pi / 6)
        p2x = p_end.x - arrow_len * math.cos(angle + math.pi / 6)
        p2y = p_end.y - arrow_len * math.sin(angle + math.pi / 6)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(p_end.x, p_end.y), QPointF(p1x, p1y), QPointF(p2x, p2y)]))

    @staticmethod
    def _smooth_path(points: list[Point], tolerance: float = 10.0) -> QPainterPath:
        path = QPainterPath()
        if not points:
            return path
        if len(points) < 3:
            path.moveTo(points[0].x, points[0].y)
            for point in points[1:]:
                path.lineTo(point.x, point.y)
            return path
        simplified = rdp_simplify(points, tolerance)
        if not simplified:
            return path
        path.moveTo(simplified[0].x, simplified[0].y)
        for index in range(1, len(simplified) - 1):
            xc = (simplified[index].x + simplified[index + 1].x) / 2
            yc = (simplified[index].y + simplified[index + 1].y) / 2
            path.quadTo(simplified[index].x, simplified[index].y, xc, yc)
        path.lineTo(simplified[-1].x, simplified[-1].y)
        return path
