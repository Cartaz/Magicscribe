"""Coordinamento delle finestre native/Qt di MagicScribe."""

from __future__ import annotations

import logging

from PySide6.QtCore import QPoint
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QApplication

from ui.widgets.floating_icon import FloatingIcon

logger = logging.getLogger(__name__)


class WindowCoordinator:
    """Possiede la policy di visibilita' e z-order della shell Qt.

    Il pannello QML non decide come coordinarsi con l'overlay QWidget o con
    l'icona volante legacy: queste responsabilita' restano nel livello native.
    """

    def __init__(self, overlay) -> None:
        self._overlay = overlay
        self._control_window: QWindow | None = None
        self._last_control_pos: QPoint | None = None
        self._floating_icon = FloatingIcon(on_clicked=self.restore_control_panel)
        self._overlay.set_floating_icon(self._floating_icon)

    def set_control_window(self, window: QWindow) -> None:
        self._control_window = window

    def show_control_panel(self) -> None:
        window = self._control_window
        if window is None:
            logger.warning("Pannello QML non ancora disponibile")
            return

        self._floating_icon.hide()
        if self._last_control_pos is not None:
            window.setPosition(self._last_control_pos)
        window.show()
        window.raise_()
        window.requestActivate()

    def minimize_to_floating(self) -> None:
        window = self._control_window
        if window is None:
            return

        self._last_control_pos = window.position()
        window.hide()
        self._floating_icon.show_at()
        self._floating_icon.raise_()
        logger.info("Pannello QML ridotto a icona volante")

    def restore_control_panel(self) -> None:
        self.show_control_panel()
        logger.info("Pannello QML ripristinato")

    def is_minimized_to_floating(self) -> bool:
        return self._floating_icon.isVisible()

    def ensure_z_order(self) -> None:
        self._overlay.lower()
        if self._control_window is not None and self._control_window.isVisible():
            self._control_window.raise_()
            self._control_window.requestActivate()
        if self._floating_icon.isVisible():
            self._floating_icon.raise_()

    def shutdown(self) -> None:
        self._floating_icon.hide()

    def quit_application(self) -> None:
        self.shutdown()
        QApplication.quit()
