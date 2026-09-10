"""Adapter QML per le azioni della shell applicativa."""

from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, Property, QRect, QTimer, Signal, Slot
from PySide6.QtGui import QCursor, QRegion

from config.constants import HotkeyDefaults
from ui.native.global_shortcuts import GlobalShortcutService
from ui.native.window_coordinator import WindowCoordinator


class ShellAdapter(QObject):
    """API QML minimale per finestra, minimizzazione e lifecycle."""

    globalDrawingShortcutsActiveChanged = Signal()

    def __init__(
        self,
        coordinator: WindowCoordinator,
        global_shortcuts: GlobalShortcutService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._coordinator = coordinator
        self._global_shortcuts = global_shortcuts
        if global_shortcuts is not None:
            global_shortcuts.activeChanged.connect(
                self.globalDrawingShortcutsActiveChanged.emit
            )

    @Property(str, constant=True)
    def toggleDrawingShortcut(self) -> str:
        return HotkeyDefaults.TOGGLE_DRAW

    @Property(str, constant=True)
    def visibilityShortcut(self) -> str:
        return HotkeyDefaults.TOGGLE_VISIBILITY

    @Property(str, constant=True)
    def clearShortcut(self) -> str:
        return HotkeyDefaults.CLEAR

    @Property(str, constant=True)
    def undoShortcut(self) -> str:
        return HotkeyDefaults.UNDO

    @Property(str, constant=True)
    def redoShortcut(self) -> str:
        return HotkeyDefaults.REDO

    @Property(str, constant=True)
    def minimizeShortcut(self) -> str:
        return HotkeyDefaults.MINIMIZE

    @Property(str, constant=True)
    def quitShortcut(self) -> str:
        return HotkeyDefaults.QUIT_APP

    @Property(bool, notify=globalDrawingShortcutsActiveChanged)
    def globalDrawingShortcutsActive(self) -> bool:
        service = self._global_shortcuts
        return service is not None and service.active

    @Property(float)
    def controlPanelX(self) -> float:
        window = self._coordinator._control_window
        if window is None:
            return 20.0
        value = window.property("layerShellPanelX")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 20.0

    @Property(float)
    def controlPanelY(self) -> float:
        window = self._coordinator._control_window
        if window is None:
            return 20.0
        value = window.property("layerShellPanelY")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 20.0

    @Slot(result=QPoint)
    def global_cursor_position(self) -> QPoint:
        """Restituisce l'ultima posizione globale del puntatore nota a Qt."""
        return QCursor.pos()

    def _set_window_input_region(
        self,
        window_attr: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        region = QRegion(
            QRect(
                round(x),
                round(y),
                max(1, round(width)),
                max(1, round(height)),
            )
        )

        def apply_region() -> None:
            # ShellAdapter e WindowCoordinator costituiscono lo stesso boundary UI;
            # le finestre vengono associate subito dopo la creazione QML.
            window = getattr(self._coordinator, window_attr)
            if window is not None:
                window.setMask(region)

        apply_region()
        # QWindow::setMask prima della creazione native non ha effetto; ripetiamo
        # nel prossimo giro dell'event loop per coprire il primo show().
        QTimer.singleShot(0, apply_region)

    @Slot(float, float, float, float)
    def set_control_input_region(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Limita l'input della control surface fullscreen al pannello visibile."""
        self._set_window_input_region(
            "_control_window", x, y, width, height
        )

    @Slot(float, float, float, float)
    def set_floating_input_region(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Limita l'input della floating surface fullscreen alla palette visibile."""
        self._set_window_input_region(
            "_floating_window", x, y, width, height
        )

    @Slot()
    def minimize_to_floating(self) -> None:
        self._coordinator.minimize_to_floating()

    @Slot()
    def restore_control_panel(self) -> None:
        self._coordinator.restore_control_panel()

    @Slot()
    def quit_application(self) -> None:
        self._coordinator.quit_application()
