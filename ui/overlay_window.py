"""Finestra overlay trasparente per il disegno su schermo.

Questa e' la finestra chiave dell'applicazione: copre
l'intero schermo con uno strato trasparente su cui
l'utente puo' disegnare annotazioni.

Quando il disegno e' disattivato, la finestra e' completamente
trasparente agli eventi mouse (click-through), permettendo
all'utente di interagire normalmente con le altre finestre.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import os
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QPainter, QCursor, QPixmap, QPen, QColor, QBrush,
    QKeySequence, QShortcut, QMouseEvent, QPaintEvent,
)
from PyQt6.QtWidgets import QWidget, QApplication

from core.models import Stroke, Point, ToolType
from ui.drawing_engine import DrawingEngine
from core.app_controller import AppController
from core.event_bus import event_bus
from config.constants import HotkeyDefaults

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Costanti X11 per XShapeCombineRegion / XShapeCombineMask
_SHAPE_INPUT = 2   # ShapeInput
_SHAPE_SET = 0     # ShapeSet


def _create_eraser_cursor(size: int = 32) -> QCursor:
    """Crea un cursore personalizzato circolare per la gomma.

    Args:
        size: diametro del cursore in pixel.

    Returns:
        QCursor con cerchio trasparente e bordo bianco.
    """
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(0, 0, 0, 0)))
    p.setPen(QPen(QColor(255, 255, 255, 180), 2))
    p.drawEllipse(2, 2, size - 4, size - 4)
    p.end()
    return QCursor(px, size // 2, size // 2)


# Cache globale per le librerie X11/Xext caricate via ctypes.
# Caricarle ad ogni chiamata di _apply_x11_input_shape era inefficiente
# e causava leak di handle Display*.
_x11_libs: Optional[tuple] = None


def _load_x11_libs() -> Optional[tuple]:
    """Carica e configura le librerie X11/Xext una sola volta (cache globale).

    Returns:
        Tuple (x11, xext) con i prototype gia' configurati, oppure None
        se le librerie non sono disponibili o non applicabili.
    """
    global _x11_libs
    if _x11_libs is not None:
        return _x11_libs

    platform = os.environ.get("QT_QPA_PLATFORM", "auto")
    if platform not in ("xcb", "auto"):
        _x11_libs = ()  # sentinel: non applicabile
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

        # Prototipi X11
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XCreateRegion.restype = ctypes.c_void_p
        x11.XDestroyRegion.argtypes = [ctypes.c_void_p]
        x11.XDestroyRegion.restype = None
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XFlush.restype = None
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = None

        # Prototipi XShape
        xext.XShapeCombineRegion.restype = None
        xext.XShapeCombineRegion.argtypes = [
            ctypes.c_void_p,   # Display*
            ctypes.c_ulong,    # Window
            ctypes.c_int,      # shape_kind (ShapeInput = 2)
            ctypes.c_int,      # x
            ctypes.c_int,      # y
            ctypes.c_void_p,   # Region
            ctypes.c_int,      # op (ShapeSet = 0)
        ]
        xext.XShapeCombineMask.restype = None
        xext.XShapeCombineMask.argtypes = [
            ctypes.c_void_p,   # Display*
            ctypes.c_ulong,    # Window
            ctypes.c_int,      # shape_kind
            ctypes.c_int,      # x
            ctypes.c_int,      # y
            ctypes.c_ulong,    # Pixmap (0 = None)
            ctypes.c_int,      # op (ShapeSet = 0)
        ]
    except (OSError, AttributeError) as exc:
        logger.debug("Caricamento librerie X11 fallito: %s", exc)
        _x11_libs = ()
        return None

    _x11_libs = (x11, xext)
    return _x11_libs


class OverlayWindow(QWidget):
    """Overlay trasparente full-screen per il disegno di annotazioni.

    La finestra copre tutti gli schermi ed e' sempre in primo piano,
    ma cattura gli eventi del mouse solo quando il disegno e' attivo.

    Attributes:
        _controller: riferimento al controller dell'app.
        _current_stroke: tratto in corso di disegno (None se idle).
        _eraser_cursor: cursore personalizzato per la gomma.
        _floating_icon: riferimento all'icona volante.
    """

    def __init__(
        self,
        controller: AppController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._current_stroke: Stroke | None = None
        self._eraser_cursor = _create_eraser_cursor()
        self._floating_icon: QWidget | None = None

        self._setup_window()
        self._connect_events()
        self._register_shortcuts()

    def set_floating_icon(self, icon: QWidget) -> None:
        """Imposta il riferimento all'icona volante per il fallback click.

        Args:
            icon: widget dell'icona volante.
        """
        self._floating_icon = icon

    def _is_in_floating_icon(self, pos) -> bool:
        """Verifica se una posizione globale e' dentro l'icona volante.

        Args:
            pos: posizione globale (QPointF o QPoint).

        Returns:
            True se la posizione e' dentro l'area dell'icona volante.
        """
        if self._floating_icon is None or not self._floating_icon.isVisible():
            return False
        try:
            gp = pos.toPoint() if hasattr(pos, 'toPoint') else pos
            icon_rect = self._floating_icon.geometry()
            return icon_rect.contains(gp)
        except (AttributeError, TypeError) as exc:
            logger.debug("Errore verifica icona volante: %s", exc)
            return False

    def _setup_window(self) -> None:
        """Configura le proprieta' della finestra overlay."""
        self.setWindowTitle("MagicScribe Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        # Evita che l'overlay appaia nella taskbar di KDE Plasma.
        # Su XWayland il flag Tool da solo potrebbe non bastare.
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._cover_all_screens()
        self._set_click_through(True)

    def _cover_all_screens(self) -> None:
        """Imposta la geometria per coprire tutti gli schermi.

        Difensivo rispetto a primaryScreen() che puo' restituire None
        (headless, schermi non ancora rilevati).
        """
        app = QApplication.instance()
        if not app:
            return
        screen = app.primaryScreen()
        if screen is None:
            logger.warning("Nessuno schermo primario disponibile per l'overlay")
            return
        self.setGeometry(screen.virtualGeometry())

    def _set_click_through(self, enabled: bool) -> None:
        """Abilita/disabilita il click-through dell'overlay.

        Usa un approccio a due livelli per massima affidabilita':
        1. Attributi Qt (WA_TransparentForMouseEvents + WA_InputMethodTransparent)
        2. X11 XShape input region diretto via ctypes (per KDE/XWayland)

        Args:
            enabled: True per far passare gli eventi mouse attraverso.
        """
        # Livello 1: Attributi Qt
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, enabled,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_InputMethodTransparent, enabled,
        )
        if enabled:
            self.unsetCursor()
        else:
            tool = self._controller.get_current_tool()
            self._apply_tool_cursor(tool)

        # Livello 2: X11 XShape input region
        self._apply_x11_input_shape(enabled)

    def _apply_x11_input_shape(self, click_through: bool) -> None:
        """Imposta l'input shape X11 per il click-through.

        Su alcuni window manager (KDE Plasma con XWayland),
        WA_TransparentForMouseEvents potrebbe non funzionare.
        Questo metodo usa XShapeCombineRegion direttamente per
        garantire che l'input shape sia impostata correttamente.

        Args:
            click_through: True per far passare tutti i click attraverso.
        """
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
                    # Regione vuota = tutti i click passano attraverso
                    region = x11.XCreateRegion()
                    xext.XShapeCombineRegion(
                        display, win_id, _SHAPE_INPUT,
                        0, 0, region, _SHAPE_SET,
                    )
                    x11.XDestroyRegion(region)
                else:
                    # Rimuovi input shape = finestra cattura i click
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
        """Imposta il cursore appropriato per lo strumento.

        Args:
            tool: tipo di strumento selezionato.
        """
        if tool == ToolType.ERASER:
            self.setCursor(self._eraser_cursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def _connect_events(self) -> None:
        """Connette i segnali dell'event bus."""
        event_bus.subscribe("drawing_toggled", self._on_drawing_toggled)
        event_bus.subscribe("visibility_toggled", self._on_visibility_toggled)
        event_bus.subscribe("strokes_changed", self._on_strokes_changed)
        event_bus.subscribe("stroke_undone", self._on_strokes_changed)
        event_bus.subscribe("stroke_redone", self._on_strokes_changed)
        event_bus.subscribe("strokes_cleared", self._on_strokes_changed)
        event_bus.subscribe("tool_changed", self._on_tool_changed)

    def _register_shortcuts(self) -> None:
        """Registra le scorciatoie da tastiera anche sull'overlay."""
        shortcuts = [
            (HotkeyDefaults.TOGGLE_DRAW, self._controller.toggle_drawing),
            (HotkeyDefaults.TOGGLE_VISIBILITY, self._controller.toggle_visibility),
            (HotkeyDefaults.CLEAR, self._controller.clear_screen),
            (HotkeyDefaults.UNDO, self._controller.undo),
            (HotkeyDefaults.REDO, self._controller.redo),
        ]
        for key, slot in shortcuts:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)

    # ── Gestione eventi ──────────────────────────────────────────────────

    def _on_drawing_toggled(self, active: bool, **kwargs) -> None:
        """Reagisce al toggle della modalita' disegno."""
        self._set_click_through(not active)
        self.update()
        QTimer.singleShot(50, self.lower)

    def _on_visibility_toggled(self, visible: bool, **kwargs) -> None:
        """Reagisce al toggle della visibilita' annotazioni."""
        self.update()

    def _on_strokes_changed(self, **kwargs) -> None:
        """Reagisce alle modifiche dei tratti."""
        self.update()

    def _on_tool_changed(self, new_tool: ToolType, **kwargs) -> None:
        """Reagisce al cambio strumento aggiornando il cursore."""
        if self._controller.is_drawing_active():
            self._apply_tool_cursor(new_tool)

    # ── Eventi mouse ─────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Inizia un nuovo tratto alla pressione del mouse."""
        if not self._controller.is_drawing_active():
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._is_in_floating_icon(event.globalPosition()):
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
        """Aggiunge punti al tratto durante il movimento."""
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
        """Finalizza il tratto al rilascio del mouse."""
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

    # ── Rendering ────────────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """Renderizza tutti i tratti sull'overlay."""
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

    # ── Utility ──────────────────────────────────────────────────────────

    def refresh_geometry(self) -> None:
        """Aggiorna la geometria dell'overlay (es. dopo cambio schermo)."""
        self._cover_all_screens()
