"""Icona volante minimizzata per MagicScribe.

Piccolo widget circolare che rimane sullo schermo quando
la GUI e' minimizzata. Cliccandoci sopra, la GUI ricompare.
Supporta il drag per riposizionarsi sullo schermo.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPen, QCursor,
    QMouseEvent, QPaintEvent,
)
from PySide6.QtWidgets import QWidget, QApplication

from config.theme import ThemeColors as C
from core.event_bus import event_bus

logger = logging.getLogger(__name__)


class FloatingIcon(QWidget):
    """Icona volante circolare per richiamare la GUI."""

    ICON_SIZE = 56
    CIRCLE_RADIUS = 20
    DRAG_THRESHOLD = 5

    def __init__(
        self,
        on_clicked: Optional[Callable[[], None]] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_clicked_cb = on_clicked
        self._drag_start: QPoint = QPoint()
        self._click_pos: QPoint = QPoint()
        self._is_dragging: bool = False
        self._system_move_active: bool = False
        self._drag_timer: QTimer | None = None
        self._last_pos: QPoint | None = None

        self._setup_window()
        self._connect_events()

    def _setup_window(self) -> None:
        self.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("MagicScribe — trascina per spostare, clicca per GUI")

    def show_at(self, pos: QPoint | None = None) -> None:
        if pos is None:
            if self._last_pos is not None:
                pos = self._last_pos
            else:
                pos = self._default_position()

        logger.info("FloatingIcon: show_at pos=%s", pos)
        self.show()
        self.move(pos)
        self.raise_()
        QTimer.singleShot(100, lambda: (self.move(pos), self.raise_()))

    def _default_position(self) -> QPoint:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            return QPoint(
                geo.right() - self.ICON_SIZE - 20,
                geo.bottom() - self.ICON_SIZE - 20,
            )
        return QPoint(100, 100)

    def hide(self) -> None:
        self._last_pos = self.pos()
        super().hide()

    def _connect_events(self) -> None:
        event_bus.subscribe("drawing_toggled", self._on_drawing_toggled)

    def _on_drawing_toggled(self, active: bool, **kwargs) -> None:
        if self.isVisible():
            QTimer.singleShot(80, self.raise_)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.ICON_SIZE / 2
        cy = self.ICON_SIZE / 2
        r = self.CIRCLE_RADIUS

        painter.setBrush(QBrush(QColor(C.PRIMARY_DARK)))
        painter.setPen(QPen(QColor(C.PRIMARY), 2))
        painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        pen = QPen(QColor(C.TEXT_PRIMARY), 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(int(cx - 5), int(cy + 8), int(cx), int(cy - 5))
        painter.drawLine(int(cx), int(cy - 5), int(cx + 5), int(cy + 2))
        painter.end()

    def _try_start_system_move(self) -> bool:
        try:
            wh = self.windowHandle()
            if wh is None:
                logger.debug("FloatingIcon: windowHandle is None")
                return False
            result = wh.startSystemMove()
            if result:
                logger.info("FloatingIcon: startSystemMove() avviato")
                return True
            logger.debug("FloatingIcon: startSystemMove() restituito False")
            return False
        except AttributeError as exc:
            logger.debug(
                "FloatingIcon: startSystemMove() non disponibile: %s", exc,
            )
            return False

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._click_pos = self.pos()
            self._is_dragging = False
            self._system_move_active = False

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if self._system_move_active:
            return

        if self._is_dragging:
            delta = event.globalPosition().toPoint() - self._drag_start
            self.move(self._click_pos + delta)
            return

        delta = event.globalPosition().toPoint() - self._drag_start
        if delta.manhattanLength() <= self.DRAG_THRESHOLD:
            return

        self._is_dragging = True

        if self._try_start_system_move():
            self._system_move_active = True
            return

        logger.info("FloatingIcon: startSystemMove non disponibile, drag manuale")
        self._start_manual_drag()

    def _start_manual_drag(self) -> None:
        if self._drag_timer is not None:
            self._drag_timer.stop()

        self._drag_timer = QTimer(self)
        self._drag_timer.timeout.connect(self._on_drag_tick)
        self._drag_timer.start(16)

    def _on_drag_tick(self) -> None:
        if not (QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
            self._stop_manual_drag()
            return

        current = QCursor.pos()
        delta = current - self._drag_start
        self.move(self._click_pos + delta)

    def _stop_manual_drag(self) -> None:
        if self._drag_timer and self._drag_timer.isActive():
            self._drag_timer.stop()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._stop_manual_drag()
            if not self._is_dragging and self._on_clicked_cb:
                self._on_clicked_cb()
