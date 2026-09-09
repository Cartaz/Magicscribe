"""Coordinamento delle finestre shell Qt di MagicScribe."""

from __future__ import annotations

import logging

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QGuiApplication, QScreen, QWindow
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


def _platform_name() -> str:
    return QGuiApplication.platformName().lower()


def _supports_absolute_top_level_positioning() -> bool:
    """XDG Shell non espone il posizionamento assoluto delle top-level."""
    return not _platform_name().startswith("wayland")


def _clamp_position_to_geometry(
    target: QPoint,
    window_size: QSize,
    geometry: QRect,
) -> QPoint:
    """Mantiene l'intera finestra dentro una geometria disponibile."""
    width = max(1, window_size.width())
    height = max(1, window_size.height())

    max_x = geometry.right() - width + 1
    max_y = geometry.bottom() - height + 1

    if max_x < geometry.left():
        x = geometry.left()
    else:
        x = min(max(target.x(), geometry.left()), max_x)

    if max_y < geometry.top():
        y = geometry.top()
    else:
        y = min(max(target.y(), geometry.top()), max_y)

    return QPoint(x, y)


class WindowCoordinator:
    """Possiede visibilita' e lifecycle della shell QML.

    Su X11/offscreen mantiene placement, reclamp, raise e activation espliciti.
    Su Wayland nativo non emula quelle operazioni: layer-shell possiede stacking,
    anchors, margins e keyboard interactivity; il QML aggiorna direttamente i
    margini durante il drag.
    """

    _CONTROL_MARGIN = 20
    _FLOATING_MARGIN = 20

    def __init__(self) -> None:
        self._control_window: QWindow | None = None
        self._floating_window: QWindow | None = None
        self._last_control_pos: QPoint | None = None
        self._last_floating_pos: QPoint | None = None
        self._screen_signals_connected = False
        self._bound_screens: list[QScreen] = []
        self._absolute_positioning = _supports_absolute_top_level_positioning()

        if self._absolute_positioning:
            self._bind_screen_signals()
        else:
            logger.info(
                "Wayland nativo: placement e stacking shell delegati a layer-shell"
            )

    def set_control_window(self, window: QWindow) -> None:
        self._control_window = window
        if not self._absolute_positioning:
            primary = QApplication.primaryScreen()
            if primary is not None:
                window.setScreen(primary)

    def set_floating_window(self, window: QWindow) -> None:
        self._floating_window = window
        if not self._absolute_positioning:
            primary = QApplication.primaryScreen()
            if primary is not None:
                window.setScreen(primary)

    def show_control_panel(self) -> None:
        window = self._control_window
        if window is None:
            logger.warning("Pannello QML non ancora disponibile")
            return

        floating = self._floating_window
        if floating is not None and floating.isVisible():
            if self._absolute_positioning:
                self._last_floating_pos = self._clamp_position(
                    floating,
                    floating.position(),
                )
            floating.hide()

        if self._absolute_positioning:
            target_pos = self._last_control_pos
            if target_pos is None:
                target_pos = self._default_control_position(window)
            target_pos = self._clamp_position(window, target_pos)
            self._last_control_pos = target_pos
            window.setPosition(target_pos)

        window.show()
        if self._absolute_positioning:
            window.raise_()
            window.requestActivate()

    def minimize_to_floating(self) -> None:
        control = self._control_window
        floating = self._floating_window
        if control is None or floating is None:
            logger.warning("Shell QML incompleta: impossibile ridurre a floating palette")
            return

        if self._absolute_positioning:
            self._last_control_pos = self._clamp_position(
                control,
                control.position(),
            )
        control.hide()

        if self._absolute_positioning:
            target_pos = self._last_floating_pos
            if target_pos is None:
                target_pos = self._default_floating_position(floating)
            target_pos = self._clamp_position(floating, target_pos)
            self._last_floating_pos = target_pos
            floating.setPosition(target_pos)

        floating.show()
        if self._absolute_positioning:
            floating.raise_()
        logger.info("Pannello QML ridotto a floating palette")

    def restore_control_panel(self) -> None:
        self.show_control_panel()
        logger.info("Pannello QML ripristinato")

    def is_minimized_to_floating(self) -> bool:
        floating = self._floating_window
        return floating is not None and floating.isVisible()

    def ensure_z_order(self) -> None:
        if not self._absolute_positioning:
            # Le layer-surface hanno un ordine definito dal protocollo, non da
            # raise_/activation delle normali finestre Qt.
            return

        control = self._control_window
        if control is not None and control.isVisible():
            control.raise_()
            control.requestActivate()

        floating = self._floating_window
        if floating is not None and floating.isVisible():
            floating.raise_()

    def shutdown(self) -> None:
        self._unbind_screen_signals()

        floating = self._floating_window
        if floating is not None:
            floating.hide()

        control = self._control_window
        if control is not None:
            control.hide()

    def quit_application(self) -> None:
        self.shutdown()
        QApplication.quit()

    def _bind_screen_signals(self) -> None:
        if not self._absolute_positioning:
            return
        app = QApplication.instance()
        if app is not None and not self._screen_signals_connected:
            app.screenAdded.connect(self._on_screen_topology_changed)
            app.screenRemoved.connect(self._on_screen_topology_changed)
            app.primaryScreenChanged.connect(self._on_screen_topology_changed)
            self._screen_signals_connected = True
        self._rebind_screen_geometry_signals()

    def _rebind_screen_geometry_signals(self) -> None:
        if not self._absolute_positioning:
            return
        self._disconnect_screen_geometry_signals()
        self._bound_screens = list(QApplication.screens())
        for screen in self._bound_screens:
            screen.geometryChanged.connect(self._on_screen_geometry_changed)
            screen.availableGeometryChanged.connect(self._on_screen_geometry_changed)

    def _disconnect_screen_geometry_signals(self) -> None:
        for screen in self._bound_screens:
            for signal in (screen.geometryChanged, screen.availableGeometryChanged):
                try:
                    signal.disconnect(self._on_screen_geometry_changed)
                except (RuntimeError, TypeError):
                    pass
        self._bound_screens = []

    def _unbind_screen_signals(self) -> None:
        self._disconnect_screen_geometry_signals()
        if not self._screen_signals_connected:
            return
        app = QApplication.instance()
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
        self._reclamp_shell_windows()

    def _on_screen_geometry_changed(self, *_args) -> None:
        self._reclamp_shell_windows()

    def _reclamp_shell_windows(self) -> None:
        if not self._absolute_positioning:
            return

        control = self._control_window
        if control is not None:
            if self._last_control_pos is not None:
                self._last_control_pos = self._clamp_position(
                    control,
                    self._last_control_pos,
                )
            if control.isVisible():
                control.setPosition(
                    self._clamp_position(control, control.position())
                )

        floating = self._floating_window
        if floating is not None:
            if self._last_floating_pos is not None:
                self._last_floating_pos = self._clamp_position(
                    floating,
                    self._last_floating_pos,
                )
            if floating.isVisible():
                floating.setPosition(
                    self._clamp_position(floating, floating.position())
                )

    def _clamp_position(self, window: QWindow, target: QPoint) -> QPoint:
        center = QPoint(
            target.x() + max(0, window.width() // 2),
            target.y() + max(0, window.height() // 2),
        )
        screen = (
            QApplication.screenAt(center)
            or QApplication.screenAt(target)
            or QApplication.primaryScreen()
        )
        if screen is None:
            return target
        return _clamp_position_to_geometry(
            target,
            QSize(window.width(), window.height()),
            screen.availableGeometry(),
        )

    def _default_control_position(self, window: QWindow) -> QPoint:
        """Posiziona la toolbar sul lato sinistro su backend che lo consentono."""
        screen = window.screen() or QApplication.primaryScreen()
        if screen is None:
            return QPoint(100, 100)

        geometry = screen.availableGeometry()
        x = geometry.left() + self._CONTROL_MARGIN
        if window.height() + 2 * self._CONTROL_MARGIN <= geometry.height():
            y = geometry.top() + (geometry.height() - window.height()) // 2
        else:
            y = geometry.top() + self._CONTROL_MARGIN
        return _clamp_position_to_geometry(
            QPoint(x, y),
            QSize(window.width(), window.height()),
            geometry,
        )

    def _default_floating_position(self, window: QWindow) -> QPoint:
        screen = window.screen() or QApplication.primaryScreen()
        if screen is None:
            return QPoint(100, 100)

        geometry = screen.availableGeometry()
        return _clamp_position_to_geometry(
            QPoint(
                geometry.right() - window.width() - self._FLOATING_MARGIN + 1,
                geometry.bottom() - window.height() - self._FLOATING_MARGIN + 1,
            ),
            QSize(window.width(), window.height()),
            geometry,
        )
