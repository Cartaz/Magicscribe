"""Icona nel system tray e menu contestuale nativo."""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from config.constants import HotkeyDefaults
from core.app_controller import AppController

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


def _application_tray_icon() -> QIcon:
    icon = QApplication.windowIcon()
    if not icon.isNull():
        return icon
    return QIcon.fromTheme("magicscribe")


class TrayIcon:
    def __init__(self, controller: AppController, show_control_panel: Callable[[], None], parent: QWidget | None = None) -> None:
        self._controller = controller
        self._show_control_panel = show_control_panel
        self._tray = QSystemTrayIcon(_application_tray_icon(), parent)
        self._build_menu()
        self._tray.activated.connect(self._on_activated)
        self._tray.setToolTip("MagicScribe — Annotazioni sullo schermo")
        self._tray.show()

    def _build_menu(self) -> None:
        menu = QMenu()
        act_show = QAction("Mostra finestra", self._tray)
        act_show.triggered.connect(self._show_control_panel)
        act_toggle = QAction(f"Attiva/Disattiva disegno ({HotkeyDefaults.TOGGLE_DRAW})", self._tray)
        act_toggle.triggered.connect(self._controller.toggle_drawing)
        act_visibility = QAction(f"Mostra/Nascondi annotazioni ({HotkeyDefaults.TOGGLE_VISIBILITY})", self._tray)
        act_visibility.triggered.connect(self._controller.toggle_visibility)
        act_clear = QAction(f"Cancella schermo ({HotkeyDefaults.CLEAR})", self._tray)
        act_clear.triggered.connect(self._controller.clear_screen)
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_toggle)
        menu.addAction(act_visibility)
        menu.addAction(act_clear)
        menu.addSeparator()
        act_quit = QAction("Esci da MagicScribe", self._tray)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(act_quit)
        self._tray.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_control_panel()

    def show_message(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 2500)
