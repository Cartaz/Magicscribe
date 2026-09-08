"""Top-level Qt Quick surface per l'overlay di disegno."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QGuiApplication,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtQuick import QQuickWindow

from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.native.x11_input_shape import set_x11_click_through
from ui.quick.drawing_canvas import DrawingCanvas

logger = logging.getLogger(__name__)


def _create_eraser_cursor(size: int = 32) -> QCursor:
    """Crea il cursore circolare usato dallo strumento gomma."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
        painter.drawEllipse(2, 2, size - 4, size - 4)
    finally:
        painter.end()
    return QCursor(pixmap, size // 2, size // 2)


def _platform_name() -> str:
    return QGuiApplication.platformName().lower()


class OverlaySurface:
    """Possiede QQuickWindow, canvas e policy native del solo overlay.

    Non possiede stato di dominio: deriva interattivita' e cursore dagli
    adapter, mentre il canvas inoltra le gesture al controller tramite il
    DrawingAdapter.
    """

    def __init__(
        self,
        drawing_adapter: DrawingAdapter,
        tool_adapter: ToolAdapter,
    ) -> None:
        self._drawing_adapter = drawing_adapter
        self._tool_adapter = tool_adapter
        self._eraser_cursor = _create_eraser_cursor()

        self.window = QQuickWindow()
        self.window.setObjectName("overlayWindow")
        self.window.setTitle("MagicScribe Overlay")
        self.window.setColor(QColor(0, 0, 0, 0))
        self.window.setFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )

        content = self.window.contentItem()
        self.canvas = DrawingCanvas(drawing_adapter, content)
        self.canvas.setObjectName("drawingCanvas")
        content.widthChanged.connect(self._sync_canvas_size)
        content.heightChanged.connect(self._sync_canvas_size)

        drawing_adapter.activeChanged.connect(self._sync_input_mode)
        tool_adapter.currentToolChanged.connect(self._sync_cursor)

        self.refresh_geometry()
        self._sync_canvas_size()
        self._sync_cursor()

    def show(self) -> None:
        self.window.show()
        # L'input region X11 richiede un native window id valido, quindi viene
        # sincronizzata dopo show() e poi a ogni cambio dello stato drawing.
        self._sync_input_mode()

    def shutdown(self) -> None:
        self.window.hide()

    def refresh_geometry(self) -> None:
        """Copre il desktop virtuale usando le coordinate dello schermo primario."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            logger.warning("Nessuno schermo primario disponibile per l'overlay Quick")
            return
        self.window.setGeometry(screen.virtualGeometry())

    def _sync_canvas_size(self) -> None:
        content = self.window.contentItem()
        self.canvas.setWidth(content.width())
        self.canvas.setHeight(content.height())

    def _sync_input_mode(self) -> None:
        """Alterna click-through e cattura input senza ricreare la window xcb."""
        click_through = not self._drawing_adapter.active

        # Sul runtime di migrazione reale (xcb/XWayland) cambiare
        # WindowTransparentForInput a finestra Quick gia' visibile si e'
        # dimostrato instabile. Usiamo quindi l'input shape X11, che modifica
        # solo la regione di input del native window esistente.
        if _platform_name() == "xcb":
            if set_x11_click_through(int(self.window.winId()), click_through):
                self._sync_cursor()
                return
            logger.warning(
                "X11 input shape non disponibile; uso il fallback Qt per l'overlay"
            )

        self._set_qt_input_transparency(click_through)
        self._sync_cursor()

    def _set_qt_input_transparency(self, click_through: bool) -> None:
        """Fallback portabile per piattaforme diverse da xcb."""
        was_visible = self.window.isVisible()
        self.window.setFlag(
            Qt.WindowType.WindowTransparentForInput,
            click_through,
        )
        if was_visible and not self.window.isVisible():
            self.window.show()

    def _sync_cursor(self) -> None:
        if not self._drawing_adapter.active:
            self.window.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            return

        if self._tool_adapter.currentTool == "eraser":
            self.window.setCursor(self._eraser_cursor)
        else:
            self.window.setCursor(QCursor(Qt.CursorShape.CrossCursor))
