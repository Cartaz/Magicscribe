"""Ownership delle finestre shell Wayland e della loro geometria d'interazione."""

from __future__ import annotations

import logging

from PySide6.QtCore import QPointF, QRect, QTimer
from PySide6.QtGui import QRegion, QWindow
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class WindowCoordinator:
    """Unico owner delle finestre control/floating e delle operazioni fra esse."""

    def __init__(self) -> None:
        self._control_window: QWindow | None = None
        self._floating_window: QWindow | None = None

    def set_control_window(self, window: QWindow) -> None:
        self._control_window = window
        primary = QApplication.primaryScreen()
        if primary is not None:
            window.setScreen(primary)

    def set_floating_window(self, window: QWindow) -> None:
        self._floating_window = window
        primary = QApplication.primaryScreen()
        if primary is not None:
            window.setScreen(primary)

    def show_control_panel(self) -> None:
        control = self._control_window
        if control is None:
            logger.warning("Pannello QML non ancora disponibile")
            return
        floating = self._floating_window
        if floating is not None and floating.isVisible():
            floating.hide()
        control.show()

    def minimize_to_floating(self) -> None:
        control = self._control_window
        floating = self._floating_window
        if control is None or floating is None:
            logger.warning("Shell QML incompleta: impossibile ridurre la toolbar")
            return
        control.hide()
        floating.show()

    def restore_control_panel(self) -> None:
        self._align_control_logo_to_floating()
        self.show_control_panel()

    def is_minimized_to_floating(self) -> bool:
        floating = self._floating_window
        return floating is not None and floating.isVisible()

    def ensure_z_order(self) -> None:
        """No-op intenzionale: lo stacking appartiene al protocollo layer-shell."""

    def shutdown(self) -> None:
        if self._floating_window is not None:
            self._floating_window.hide()
        if self._control_window is not None:
            self._control_window.hide()

    def quit_application(self) -> None:
        self.shutdown()
        QApplication.quit()

    @staticmethod
    def _numeric_property(window: QWindow, name: str, fallback: float) -> float:
        try:
            return float(window.property(name))
        except (TypeError, ValueError):
            return fallback

    def control_panel_position(self) -> QPointF:
        window = self._control_window
        if window is None:
            return QPointF(20.0, 20.0)
        return QPointF(
            self._numeric_property(window, "layerShellPanelX", 20.0),
            self._numeric_property(window, "layerShellPanelY", 20.0),
        )

    def control_logo_center(self) -> QPointF:
        window = self._control_window
        if window is not None:
            logo = window.findChild(QQuickItem, "minimizeButton")
            if logo is not None:
                return logo.mapToScene(QPointF(logo.width() / 2.0, logo.height() / 2.0))
        panel = self.control_panel_position()
        return QPointF(panel.x() + 52.0, panel.y() + 50.0)

    def floating_palette_center(self) -> QPointF | None:
        window = self._floating_window
        if window is None:
            return None
        x = self._numeric_property(window, "layerShellPaletteX", float("nan"))
        y = self._numeric_property(window, "layerShellPaletteY", float("nan"))
        width = self._numeric_property(window, "paletteWidth", float("nan"))
        height = self._numeric_property(window, "paletteHeight", float("nan"))
        if any(value != value for value in (x, y, width, height)):
            return None
        return QPointF(x + width / 2.0, y + height / 2.0)

    def _align_control_logo_to_floating(self) -> None:
        control = self._control_window
        floating_center = self.floating_palette_center()
        if control is None or floating_center is None:
            return
        logo_center = self.control_logo_center()
        panel = self.control_panel_position()
        control.setProperty(
            "layerShellPanelX",
            panel.x() + floating_center.x() - logo_center.x(),
        )
        control.setProperty(
            "layerShellPanelY",
            panel.y() + floating_center.y() - logo_center.y(),
        )

    def set_control_input_region(self, x: float, y: float, width: float, height: float) -> None:
        self._set_window_input_region("control", x, y, width, height)

    def set_floating_input_region(self, x: float, y: float, width: float, height: float) -> None:
        self._set_window_input_region("floating", x, y, width, height)

    def _set_window_input_region(
        self,
        kind: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        region = QRegion(
            QRect(round(x), round(y), max(1, round(width)), max(1, round(height)))
        )

        def apply_region() -> None:
            window = self._control_window if kind == "control" else self._floating_window
            if window is not None:
                window.setMask(region)

        apply_region()
        QTimer.singleShot(0, apply_region)
