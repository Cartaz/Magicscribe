"""Adapter QML per le azioni della shell applicativa."""

from __future__ import annotations

from PySide6.QtCore import QObject, Property, Slot

from config.constants import HotkeyDefaults
from ui.native.window_coordinator import WindowCoordinator


class ShellAdapter(QObject):
    """API QML minimale per finestra, minimizzazione e lifecycle."""

    def __init__(
        self,
        coordinator: WindowCoordinator,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._coordinator = coordinator

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

    @Slot(name="minimizeToFloating")
    def minimize_to_floating(self) -> None:
        self._coordinator.minimize_to_floating()

    @Slot(name="restoreControlPanel")
    def restore_control_panel(self) -> None:
        self._coordinator.restore_control_panel()

    @Slot(name="quitApplication")
    def quit_application(self) -> None:
        self._coordinator.quit_application()
