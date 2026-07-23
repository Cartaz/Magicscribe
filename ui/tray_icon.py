"""Icona nel system tray e menu contestuale.

Gestisce l'icona nell'area di notifica con un menu
che replica le azioni principali dell'applicazione.
La chiusura tramite X o Ctrl+Q termina completamente l'app.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QAction,
)
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from core.app_controller import AppController
from core.event_bus import event_bus
from config.theme import ThemeColors as C

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


def _create_tray_icon() -> QIcon:
    """Crea l'icona SVG-like per il system tray.

    Returns:
        QIcon con il logo di MagicScribe (penna stilografica stilizzata).
    """
    px = QPixmap(22, 22)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(C.PRIMARY)))
    p.setPen(QPen(Qt.PenStyle.NoPen))
    p.drawRoundedRect(2, 2, 18, 18, 4, 4)
    p.setPen(QPen(QColor(C.SELECTION_TEXT), 2))
    p.drawLine(6, 16, 11, 8)
    p.drawLine(11, 8, 16, 13)
    p.end()
    return QIcon(px)


class TrayIcon:
    """Gestore dell'icona nel system tray e del menu contestuale.

    Attributes:
        _controller: riferimento al controller dell'app.
        _tray: QSystemTrayIcon.
        _main_window: riferimento alla finestra principale (per toggle).
    """

    def __init__(
        self,
        controller: AppController,
        main_window,
        parent: QWidget | None = None,
    ) -> None:
        self._controller = controller
        self._main_window = main_window
        self._tray = QSystemTrayIcon(_create_tray_icon(), parent)
        self._build_menu()
        self._connect_signals()
        self._tray.setToolTip("MagicScribe — Annotazioni sullo schermo")
        self._tray.show()

    def _build_menu(self) -> None:
        """Costruisce il menu contestuale del tray."""
        menu = QMenu()

        act_show = QAction("Mostra finestra", self._tray)
        act_show.triggered.connect(self._show_main_window)

        act_toggle = QAction("Attiva/Disattiva disegno (F9)", self._tray)
        act_toggle.triggered.connect(self._controller.toggle_drawing)

        act_visibility = QAction("Mostra/Nascondi annotazioni", self._tray)
        act_visibility.triggered.connect(self._controller.toggle_visibility)

        act_clear = QAction("Cancella schermo (Shift+F9)", self._tray)
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

    def _connect_signals(self) -> None:
        """Connette i segnali del tray."""
        self._tray.activated.connect(self._on_activated)

    def _on_activated(
        self, reason: QSystemTrayIcon.ActivationReason,
    ) -> None:
        """Gestisce il click sull'icona del tray.

        Args:
            reason: motivo dell'attivazione.
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_main_window()

    def _show_main_window(self) -> None:
        """Mostra e porta in primo piano la finestra principale.

        Se la GUI e' ridotta a icona volante, la ripristina.
        """
        if (
            hasattr(self._main_window, 'is_minimized_to_floating')
            and self._main_window.is_minimized_to_floating()
        ):
            # Usa il metodo pubblico (preferito) o fallback a quello privato
            restore = getattr(
                self._main_window, 'restore_from_floating',
                self._main_window._restore_from_floating,
            )
            restore()
        else:
            self._main_window.show()
            self._main_window.activateWindow()
            self._main_window.raise_()

    def show_message(self, title: str, message: str) -> None:
        """Mostra una notifica dal tray.

        Args:
            title: titolo della notifica.
            message: corpo del messaggio.
        """
        self._tray.showMessage(
            title, message,
            QSystemTrayIcon.MessageIcon.Information, 2500,
        )
