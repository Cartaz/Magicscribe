"""Layer-surface Qt Quick per l'overlay di disegno, una per QScreen."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import math
from typing import Any, Protocol

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
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
from ui.quick.drawing_canvas import DrawingCanvas

logger = logging.getLogger(__name__)


# Sotto questa soglia un anello non si distingue piu' da un punto: il cerchio
# resta leggibile anche se l'area cancellata e' leggermente piu' piccola.
_ERASER_CURSOR_MIN_DIAMETER = 6.0


def _create_eraser_cursor(diameter: float, device_pixel_ratio: float = 1.0) -> QCursor:
    """Crea il cursore circolare della gomma con il diametro reale del tratto.

    ``diameter`` e' in pixel logici, come lo spessore del tratto sulla canvas;
    la pixmap e' generata in pixel fisici cosi' il cerchio resta nitido e della
    stessa dimensione dell'area cancellata anche su schermi HiDPI.

    QtWayland invia i cursori bitmap con un ``buffer_scale`` intero: con lo
    scaling frazionario la pixmap usa il ratio intero superiore e un lato
    multiplo di esso, e il compositor la riduce alla dimensione logica giusta.
    """
    diameter = max(float(diameter), _ERASER_CURSOR_MIN_DIAMETER)
    ratio = max(math.ceil(device_pixel_ratio), 1)
    margin = 2.0
    # Lato pari: il centro dell'anello cade su un pixel intero, dove sta l'hotspot.
    logical_side = math.ceil(diameter + 2 * margin)
    logical_side += logical_side % 2
    physical_side = logical_side * ratio

    pixmap = QPixmap(physical_side, physical_side)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        center = QPointF(logical_side / 2, logical_side / 2)
        radius = diameter / 2
        # Doppio anello chiaro/scuro: visibile sia su sfondi chiari che scuri.
        painter.setPen(QPen(QColor(0, 0, 0, 160), 3))
        painter.drawEllipse(center, radius, radius)
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
        painter.drawEllipse(center, radius, radius)
    finally:
        painter.end()
    hotspot = logical_side // 2
    return QCursor(pixmap, hotspot, hotspot)


class WindowComponent(Protocol):
    """Sottoinsieme di ``QQmlComponent`` usato per creare le layer-surface."""

    def create(self) -> Any: ...

    def errors(self) -> list[Any]: ...


@dataclass
class _OverlayView:
    screen: QScreen
    window: QQuickWindow
    canvas: DrawingCanvas
    cursor_key: object = None


class OverlaySurface:
    """Possiede le finestre overlay e la loro policy di input/rendering.

    Ogni QScreen riceve una finestra creata da ``window_component`` (in
    produzione ``WaylandLayerSurface``): il compositor possiede stacking e
    geometria, mentre tutte le canvas leggono e scrivono nello stesso spazio di
    coordinate globali del desktop.
    """

    def __init__(
        self,
        drawing_adapter: DrawingAdapter,
        tool_adapter: ToolAdapter,
        *,
        window_component: WindowComponent,
    ) -> None:
        self._drawing_adapter = drawing_adapter
        self._tool_adapter = tool_adapter
        self._window_component = window_component
        self._screen_signals_connected = False
        self._bound_screens: list[QScreen] = []
        self._views: list[_OverlayView] = []
        self._shown = False

        drawing_adapter.activeChanged.connect(self._sync_input_mode)
        tool_adapter.currentToolChanged.connect(self._sync_cursor)
        tool_adapter.configChanged.connect(self._sync_cursor)

        self._bind_screen_signals()
        self._build_views()
        self.refresh_geometry()
        self._sync_cursor()

    @property
    def windows(self) -> tuple[QQuickWindow, ...]:
        return tuple(view.window for view in self._views)

    def show(self) -> None:
        self._shown = True
        for view in self._views:
            view.window.show()
        self._sync_input_mode()
        logger.info(
            "Overlay avviato: backend=%s, ruolo=layer-shell/top, superfici=%d",
            QGuiApplication.platformName().lower(),
            len(self._views),
        )

    def shutdown(self) -> None:
        self._shown = False
        self._unbind_screen_signals()
        for view in self._views:
            view.window.hide()

    def refresh_geometry(self) -> None:
        """Sincronizza porzione di desktop e origine globale di ogni canvas."""
        for view in self._views:
            geometry = view.screen.geometry()
            view.canvas.set_global_origin(QPointF(geometry.x(), geometry.y()))
            self._sync_canvas_size(view)

    def _build_views(self) -> None:
        for index, screen in enumerate(QGuiApplication.screens()):
            self._views.append(self._create_view(screen, index))

    def _create_window(self, index: int) -> QQuickWindow:
        component = self._window_component
        obj = component.create()
        if not isinstance(obj, QQuickWindow):
            if obj is not None:
                obj.deleteLater()
            errors = "; ".join(error.toString() for error in component.errors())
            raise RuntimeError(
                "La layer-surface overlay non ha creato un QQuickWindow: " + errors
            )

        window = obj
        window.setObjectName("overlayWindow" if index == 0 else f"overlayWindow{index}")
        window.setTitle("MagicScribe Overlay")
        return window

    def _create_view(self, screen: QScreen, index: int) -> _OverlayView:
        window = self._create_window(index)
        window.setScreen(screen)

        if not self._drawing_adapter.active:
            window.setFlag(Qt.WindowType.WindowTransparentForInput, True)

        content = window.contentItem()
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
            screen.logicalDotsPerInchChanged.connect(self._on_screen_geometry_changed)

    def _disconnect_screen_geometry_signals(self) -> None:
        for screen in self._bound_screens:
            for signal in (
                screen.geometryChanged,
                screen.virtualGeometryChanged,
                screen.logicalDotsPerInchChanged,
            ):
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
        was_shown = self._shown
        self._destroy_views()
        self._build_views()
        self.refresh_geometry()
        self._sync_cursor()
        if was_shown:
            self.show()

    def _on_screen_geometry_changed(self, *_args) -> None:
        self.refresh_geometry()
        self._sync_cursor()

    @staticmethod
    def _sync_canvas_size(view: _OverlayView) -> None:
        content = view.window.contentItem()
        view.canvas.setWidth(content.width())
        view.canvas.setHeight(content.height())

    def _sync_input_mode(self) -> None:
        """Alterna click-through e cattura input su tutte le superfici."""
        click_through = not self._drawing_adapter.active
        for view in self._views:
            self._set_qt_input_transparency(view.window, click_through)
        self._sync_cursor()

    @staticmethod
    def _set_qt_input_transparency(
        window: QQuickWindow,
        click_through: bool,
    ) -> None:
        """Aggiorna la wl_surface input region e ne forza il commit."""
        was_visible = window.isVisible()
        window.setFlag(
            Qt.WindowType.WindowTransparentForInput,
            click_through,
        )
        if was_visible and not window.isVisible():
            window.show()
        if was_visible:
            # QtWayland aggiorna wl_surface.set_input_region() in setWindowFlags,
            # ma la richiesta diventa effettiva solo al successivo surface commit.
            window.requestUpdate()

    def _sync_cursor(self) -> None:
        if not self._drawing_adapter.active:
            shape: Qt.CursorShape | None = Qt.CursorShape.ArrowCursor
        elif self._tool_adapter.currentTool == "eraser":
            shape = None
        else:
            shape = Qt.CursorShape.CrossCursor

        for view in self._views:
            if shape is None:
                # Lo scale dell'output (non quello della finestra) cambia insieme
                # a geometryChanged/logicalDotsPerInchChanged, a cui siamo collegati.
                key: object = (
                    float(self._tool_adapter.currentSize),
                    view.screen.devicePixelRatio(),
                )
            else:
                key = shape
            if key == view.cursor_key:
                continue
            view.cursor_key = key
            if shape is None:
                view.window.setCursor(_create_eraser_cursor(*key))
            else:
                view.window.setCursor(QCursor(shape))
