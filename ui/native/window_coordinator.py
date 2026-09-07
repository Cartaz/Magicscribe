"""Coordinamento delle finestre native/Qt di MagicScribe."""

from __future__ import annotations

import logging

from PySide6.QtCore import QPoint
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class WindowCoordinator:
    """Possiede la policy di visibilita', posizione e z-order della shell Qt.

    Riceve solo finestre Qt; non conosce renderer, widget legacy o regole di
    dominio. Pannello e floating palette restano presentazione QML.
    """

    _FLOATING_MARGIN = 20

    def __init__(self, overlay_window: QWindow) -> None:
        self._overlay_window = overlay_window
        self._control_window: QWindow | None = None
        self._floating_window: QWindow | None = None
        self._last_control_pos: QPoint | None = None
        self._last_floating_pos: QPoint | None = None

    def set_control_window(self, window: QWindow) -> None:
        self._control_window = window

    def set_floating_window(self, window: QWindow) -> None:
        self._floating_window = window

    def show_control_panel(self) -> None:
        window = self._control_window
        if window is None:
            logger.warning("Pannello QML non ancora disponibile")
            return

        floating = self._floating_window
        if floating is not None and floating.isVisible():
            self._last_floating_pos = floating.position()
            floating.hide()

        if self._last_control_pos is not None:
            window.setPosition(self._last_control_pos)
        window.show()
        window.raise_()
        window.requestActivate()

    def minimize_to_floating(self) -> None:
        control = self._control_window
        floating = self._floating_window
        if control is None or floating is None:
            logger.warning("Shell QML incompleta: impossibile ridurre a floating palette")
            return

        self._last_control_pos = control.position()
        control.hide()

        target_pos = self._last_floating_pos
        if target_pos is None:
            target_pos = self._default_floating_position(floating)
        floating.setPosition(target_pos)
        floating.show()
        floating.raise_()
        logger.info("Pannello QML ridotto a floating palette")

    def restore_control_panel(self) -> None:
        self.show_control_panel()
        logger.info("Pannello QML ripristinato")

    def is_minimized_to_floating(self) -> bool:
        floating = self._floating_window
        return floating is not None and floating.isVisible()

    def ensure_z_order(self) -> None:
        self._overlay_window.lower()

        control = self._control_window
        if control is not None and control.isVisible():
            control.raise_()
            control.requestActivate()

        floating = self._floating_window
        if floating is not None and floating.isVisible():
            floating.raise_()

    def shutdown(self) -> None:
        floating = self._floating_window
        if floating is not None:
            floating.hide()

        control = self._control_window
        if control is not None:
            control.hide()

        self._overlay_window.hide()

    def quit_application(self) -> None:
        self.shutdown()
        QApplication.quit()

    def _default_floating_position(self, window: QWindow) -> QPoint:
        screen = window.screen() or QApplication.primaryScreen()
        if screen is None:
            return QPoint(100, 100)

        geometry = screen.availableGeometry()
        return QPoint(
            geometry.right() - window.width() - self._FLOATING_MARGIN,
            geometry.bottom() - window.height() - self._FLOATING_MARGIN,
        )
