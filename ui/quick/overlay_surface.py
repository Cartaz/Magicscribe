"""Top-level Qt Quick surfaces per l'overlay di disegno."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QGuiApplication,
    QPainter,
    QPen,
    QPixmap,
    QScreen,
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


def _is_native_wayland() -> bool:
    return _platform_name().startswith("wayland")


@dataclass
class _OverlayView:
    screen: QScreen | None
    window: QQuickWindow
    canvas: DrawingCanvas


class OverlaySurface:
    """Possiede le finestre overlay e la loro policy di input/rendering.

    X11/offscreen usa una singola finestra sul desktop virtuale. Wayland nativo
    usa invece una superficie fullscreen per ogni QScreen, evitando di dipendere
    dal posizionamento assoluto delle top-level che XDG Shell non espone. Tutte
    le canvas leggono e scrivono coordinate globali, quindi la cronologia dei
    tratti resta unica e indipendente dal monitor che ha ricevuto la gesture.
    """

    def __init__(
        self,
        drawing_adapter: DrawingAdapter,
        tool_adapter: ToolAdapter,
    ) -> None:
        self._drawing_adapter = drawing_adapter
        self._tool_adapter = tool_adapter
        self._eraser_cursor = _create_eraser_cursor()
        self._screen_signals_connected = False
        self._bound_screens: list[QScreen] = []
        self._views: list[_OverlayView] = []
        self._shown = False

        drawing_adapter.activeChanged.connect(self._sync_input_mode)
        tool_adapter.currentToolChanged.connect(self._sync_cursor)

        self._bind_screen_signals()
        self._build_views()
        self.refresh_geometry()
        self._sync_cursor()

    @property
    def windows(self) -> tuple[QQuickWindow, ...]:
        return tuple(view.window for view in self._views)

    @property
    def primary_window(self) -> QQuickWindow:
        primary = QGuiApplication.primaryScreen()
        for view in self._views:
            if view.screen is primary:
                return view.window
        if not self._views:
            raise RuntimeError("OverlaySurface senza finestre")
        return self._views[0].window

    @property
    def window(self) -> QQuickWindow:
        """Alias compatibile per il primary overlay window."""
        return self.primary_window

    @property
    def canvas(self) -> DrawingCanvas:
        primary = self.primary_window
        for view in self._views:
            if view.window is primary:
                return view.canvas
        raise RuntimeError("OverlaySurface senza canvas primaria")

    def show(self) -> None:
        self._shown = True
        for view in self._views:
            if _is_native_wayland() and view.screen is not None:
                view.window.showFullScreen()
            else:
                view.window.show()
        # X11 Shape richiede un native id valido e Qt Wayland puo' ricreare la
        # surface quando cambiano i flag: sincronizziamo sempre dopo show().
        self._sync_input_mode()
        logger.info(
            "Overlay avviato: backend=%s, superfici=%d",
            _platform_name(),
            len(self._views),
        )

    def ensure_z_order(self) -> None:
        for view in self._views:
            if view.window.isVisible():
                view.window.lower()

    def shutdown(self) -> None:
        self._shown = False
        self._unbind_screen_signals()
        for view in self._views:
            view.window.hide()

    def refresh_geometry(self) -> None:
        """Sincronizza porzione di desktop e origine globale di ogni canvas."""
        if _is_native_wayland():
            for view in self._views:
                if view.screen is None:
                    continue
                geometry = view.screen.geometry()
                view.canvas.set_global_origin(
                    QPointF(geometry.x(), geometry.y())
                )
                self._sync_canvas_size(view)
            return

        if not self._views:
            return
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            logger.warning("Nessuno schermo primario disponibile per l'overlay Quick")
            return
        geometry = screen.virtualGeometry()
        view = self._views[0]
        view.window.setGeometry(geometry)
        view.canvas.set_global_origin(QPointF(geometry.x(), geometry.y()))
        self._sync_canvas_size(view)

    def _build_views(self) -> None:
        screens = list(QGuiApplication.screens())
        if _is_native_wayland() and screens:
            for index, screen in enumerate(screens):
                self._views.append(self._create_view(screen, index))
        else:
            self._views.append(self._create_view(None, 0))

    def _create_view(self, screen: QScreen | None, index: int) -> _OverlayView:
        window = QQuickWindow()
        window.setObjectName("overlayWindow" if index == 0 else f"overlayWindow{index}")
        window.setTitle("MagicScribe Overlay")
        window.setColor(QColor(0, 0, 0, 0))
        if screen is not None:
            window.setScreen(screen)

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        if _platform_name() != "xcb" and not self._drawing_adapter.active:
            flags |= Qt.WindowType.WindowTransparentForInput
        window.setFlags(flags)

        content = window.contentItem()
        origin = QPointF()
        if screen is not None:
            geometry = screen.geometry()
            origin = QPointF(geometry.x(), geometry.y())
        canvas = DrawingCanvas(
            self._drawing_adapter,
            content,
            global_origin=origin,
        )
        canvas.setObjectName("drawingCanvas" if index == 0 else f"drawingCanvas{index}")
        view = _OverlayView(screen=screen, window=window, canvas=canvas)

        content.widthChanged.connect(
            lambda *_, current=view: self._sync_canvas_size(current)
        )
        content.heightChanged.connect(
            lambda *_, current=view: self._sync_canvas_size(current)
        )
        self._sync_canvas_size(view)
        return view

    def _destroy_views(self) -> None:
        for view in self._views:
            view.window.hide()
            view.canvas.deleteLater()
            view.window.deleteLater()
        self._views = []

    def _bind_screen_signals(self) -> None:
        app = QGuiApplication.instance()
        if app is not None and not self._screen_signals_connected:
            app.screenAdded.connect(self._on_screen_topology_changed)
            app.screenRemoved.connect(self._on_screen_topology_changed)
            app.primaryScreenChanged.connect(self._on_screen_topology_changed)
            self._screen_signals_connected = True
        self._rebind_screen_geometry_signals()

    def _rebind_screen_geometry_signals(self) -> None:
        self._disconnect_screen_geometry_signals()
        self._bound_screens = list(QGuiApplication.screens())
        for screen in self._bound_screens:
            screen.geometryChanged.connect(self._on_screen_geometry_changed)
            screen.virtualGeometryChanged.connect(self._on_screen_geometry_changed)

    def _disconnect_screen_geometry_signals(self) -> None:
        for screen in self._bound_screens:
            for signal in (screen.geometryChanged, screen.virtualGeometryChanged):
                try:
                    signal.disconnect(self._on_screen_geometry_changed)
                except (RuntimeError, TypeError):
                    pass
        self._bound_screens = []

    def _unbind_screen_signals(self) -> None:
        self._disconnect_screen_geometry_signals()
        if not self._screen_signals_connected:
            return
        app = QGuiApplication.instance()
        if app is not None:
            for signal in (
                app.screenAdded,
                app.screenRemoved,
                app.primaryScreenChanged,
            ):
                try:
                    signal.disconnect(self._on_screen_topology_changed)
                except (RuntimeError, TypeError):
                    pass
        self._screen_signals_connected = False

    def _on_screen_topology_changed(self, *_args) -> None:
        self._rebind_screen_geometry_signals()
        if _is_native_wayland():
            was_shown = self._shown
            self._destroy_views()
            self._build_views()
            self.refresh_geometry()
            self._sync_cursor()
            if was_shown:
                self.show()
            return
        self.refresh_geometry()

    def _on_screen_geometry_changed(self, *_args) -> None:
        self.refresh_geometry()

    @staticmethod
    def _sync_canvas_size(view: _OverlayView) -> None:
        content = view.window.contentItem()
        view.canvas.setWidth(content.width())
        view.canvas.setHeight(content.height())

    def _sync_input_mode(self) -> None:
        """Alterna click-through e cattura input su tutte le superfici."""
        click_through = not self._drawing_adapter.active

        for view in self._views:
            if _platform_name() == "xcb":
                if set_x11_click_through(int(view.window.winId()), click_through):
                    continue
                logger.warning(
                    "X11 input shape non disponibile; uso il fallback Qt per l'overlay"
                )
            self._set_qt_input_transparency(view.window, click_through)

        self._sync_cursor()

    @staticmethod
    def _set_qt_input_transparency(
        window: QQuickWindow,
        click_through: bool,
    ) -> None:
        """Usa la policy Qt nativa, preservando fullscreen su Wayland."""
        was_visible = window.isVisible()
        window.setFlag(
            Qt.WindowType.WindowTransparentForInput,
            click_through,
        )
        if was_visible and not window.isVisible():
            if _is_native_wayland() and window.screen() is not None:
                window.showFullScreen()
            else:
                window.show()

    def _sync_cursor(self) -> None:
        if not self._drawing_adapter.active:
            cursor = QCursor(Qt.CursorShape.ArrowCursor)
        elif self._tool_adapter.currentTool == "eraser":
            cursor = self._eraser_cursor
        else:
            cursor = QCursor(Qt.CursorShape.CrossCursor)

        for view in self._views:
            view.window.setCursor(cursor)
