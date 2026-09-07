"""Finestra overlay trasparente per il disegno su schermo.

Questa finestra copre il desktop virtuale e cattura il mouse solo quando il
disegno e' attivo. In M4 mantiene intenzionalmente il comportamento QWidget,
QPainter e X11/XShape esistente; pannello e floating palette sono invece QML.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import os
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QPainter, QCursor, QPixmap, QPen, QColor, QBrush,
    QKeySequence, QShortcut, QMouseEvent, QPaintEvent, QWindow,
)
from PySide6.QtWidgets import QWidget, QApplication

from core.models import Stroke, Point, ToolType
from ui.drawing_engine import DrawingEngine
from core.app_controller import AppController
from core.event_bus import event_bus
from config.constants import HotkeyDefaults

logger = logging.getLogger(__name__)

_SHAPE_INPUT = 2
_SHAPE_SET = 0


def _create_eraser_cursor(size: int = 32) -> QCursor:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
    painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
    painter.drawEllipse(2, 2, size - 4, size - 4)
    painter.end()
    return QCursor(px, size // 2, size // 2)


_x11_libs: Optional[tuple] = None


def _load_x11_libs() -> Optional[tuple]:
    """Carica e configura X11/Xext una sola volta."""
    global _x11_libs
    if _x11_libs is not None:
        return _x11_libs

    platform = os.environ.get("QT_QPA_PLATFORM", "auto")
    if platform not in ("xcb", "auto"):
        _x11_libs = ()
        return None

    x11_path = ctypes.util.find_library("X11")
    xext_path = ctypes.util.find_library("Xext")
    if not x11_path or not xext_path:
        logger.debug("Librerie X11/Xext non trovate")
        _x11_libs = ()
        return None

    try:
        x11 = ctypes.cdll.LoadLibrary(x11_path)
        xext = ctypes.cdll.LoadLibrary(xext_path)

        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XCreateRegion.restype = ctypes.c_void_p
        x11.XDestroyRegion.argtypes = [ctypes.c_void_p]
        x11.XDestroyRegion.restype = None
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XFlush.restype = None
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = None

        xext.XShapeCombineRegion.restype = None
        xext.XShapeCombineRegion.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        xext.XShapeCombineMask.restype = None
        xext.XShapeCombineMask.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_int,
        ]
    except (OSError, AttributeError) as exc:
        logger.debug("Caricamento librerie X11 fallito: %s", exc)
        _x11_libs = ()
        return None

    _x11_libs = (x11, xext)
    return _x11_libs


class OverlayWindow(QWidget):
    """Overlay trasparente full-screen per il disegno di annotazioni."""

    def __init__(
        self,
        controller: AppController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._current_stroke: Stroke | None = None
        self._eraser_cursor = _create_eraser_cursor()
        self._floating_surface: QWidget | QWindow | None = None
        self._shortcuts: list[QShortcut] = []

        self._setup_window()
        self._connect_events()
        self._register_shortcuts()

    def set_floating_icon(self, icon: QWidget) -> None:
        """Compatibilita' temporanea con la MainWindow QWidget legacy."""
        self._floating_surface = icon

    def set_floating_window(self, window: QWindow) -> None:
        """Registra la floating palette QML usata dal runtime M4."""
        self._floating_surface = window

    def _is_in_floating_surface(self, pos) -> bool:
        surface = self._floating_surface
        if surface is None or not surface.isVisible():
            return False
        try:
            global_pos = pos.toPoint() if hasattr(pos, "toPoint") else pos
            return surface.geometry().contains(global_pos)
        except (AttributeError, TypeError) as exc:
            logger.debug("Errore verifica floating surface: %s", exc)
            return False

    def _setup_window(self) -> None:
        self.setWindowTitle("MagicScribe Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._cover_all_screens()
        self._set_click_through(True)

    def _cover_all_screens(self) -> None:
        app = QApplication.instance()
        if not app:
            return
        screen = app.primaryScreen()
        if screen is None:
            logger.warning("Nessuno schermo primario disponibile per l'overlay")
            return
        self.setGeometry(screen.virtualGeometry())

    def _set_click_through(self, enabled: bool) -> None:
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, enabled,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_InputMethodTransparent, enabled,
        )
        if enabled:
            self.unsetCursor()
        else:
            self._apply_tool_cursor(self._controller.get_current_tool())

        self._apply_x11_input_shape(enabled)

    def _apply_x11_input_shape(self, click_through: bool) -> None:
        libs = _load_x11_libs()
        if not libs:
            return
        x11, xext = libs

        try:
            display = x11.XOpenDisplay(None)
            if not display:
                logger.debug("Impossibile aprire display X11")
                return

            try:
                win_id = ctypes.c_ulong(int(self.winId()))

                if click_through:
                    region = x11.XCreateRegion()
                    xext.XShapeCombineRegion(
                        display, win_id, _SHAPE_INPUT,
                        0, 0, region, _SHAPE_SET,
                    )
                    x11.XDestroyRegion(region)
                else:
                    xext.XShapeCombineMask(
                        display, win_id, _SHAPE_INPUT,
                        0, 0, ctypes.c_ulong(0), _SHAPE_SET,
                    )

                x11.XFlush(display)
            finally:
                x11.XCloseDisplay(display)

            logger.debug(
                "X11 input shape: click_through=%s, win=%s",
                click_through, int(self.winId()),
            )
        except Exception as exc:
            logger.debug("X11 input shape fallita: %s", exc)

    def _apply_tool_cursor(self, tool: ToolType) -> None:
        if tool == ToolType.ERASER:
            self.setCursor(self._eraser_cursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def _connect_events(self) -> None:
        event_bus.subscribe("drawing_toggled", self._on_drawing_toggled)
        event_bus.subscribe("visibility_toggled", self._on_visibility_toggled)
        event_bus.subscribe("strokes_changed", self._on_strokes_changed)
        event_bus.subscribe("stroke_undone", self._on_strokes_changed)
        event_bus.subscribe("stroke_redone", self._on_strokes_changed)
        event_bus.subscribe("strokes_cleared", self._on_strokes_changed)
        event_bus.subscribe("tool_changed", self._on_tool_changed)

    def _register_shortcuts(self) -> None:
        """Mantiene le shortcut dell'overlay per la parita' del comportamento M1."""
        shortcuts = [
            (HotkeyDefaults.TOGGLE_DRAW, self._controller.toggle_drawing),
            (HotkeyDefaults.TOGGLE_VISIBILITY, self._controller.toggle_visibility),
            (HotkeyDefaults.CLEAR, self._controller.clear_screen),
            (HotkeyDefaults.UNDO, self._controller.undo),
            (HotkeyDefaults.REDO, self._controller.redo),
        ]
        for key, slot in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)

    def _on_drawing_toggled(self, active: bool, **kwargs) -> None:
        self._set_click_through(not active)
        self.update()
        QTimer.singleShot(50, self.lower)

    def _on_visibility_toggled(self, visible: bool, **kwargs) -> None:
        self.update()

    def _on_strokes_changed(self, **kwargs) -> None:
        self.update()

    def _on_tool_changed(self, new_tool: ToolType, **kwargs) -> None:
        if self._controller.is_drawing_active():
            self._apply_tool_cursor(new_tool)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not self._controller.is_drawing_active():
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._is_in_floating_surface(event.globalPosition()):
            return

        tool = self._controller.get_current_tool()
        stroke = self._controller.create_stroke(tool)
        pos = event.position()
        stroke.points.append(Point(x=pos.x(), y=pos.y(), pressure=1.0))
        self._current_stroke = stroke

        if stroke.is_shape():
            stroke.points.append(Point(x=pos.x(), y=pos.y()))

        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._current_stroke is None:
            return

        pos = event.position()
        point = Point(x=pos.x(), y=pos.y(), pressure=1.0)

        if self._current_stroke.is_shape():
            self._current_stroke.points[-1] = point
        else:
            self._current_stroke.points.append(point)

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._current_stroke is None:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position()
        if self._current_stroke.is_shape():
            self._current_stroke.points[-1] = Point(x=pos.x(), y=pos.y())
        else:
            self._current_stroke.points.append(Point(x=pos.x(), y=pos.y()))

        self._controller.finalize_stroke(self._current_stroke)
        self._current_stroke = None
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        if not self._controller.is_visible():
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            strokes = self._controller.stroke_manager.get_strokes()
            DrawingEngine.render_strokes(painter, strokes)

            if self._current_stroke is not None:
                DrawingEngine.render_stroke(painter, self._current_stroke)
        finally:
            painter.end()

    def refresh_geometry(self) -> None:
        self._cover_all_screens()
