#!/usr/bin/env python3
"""MagicScribe — Annotazioni sullo schermo, standalone.

Punto di ingresso dell'applicazione. Si limita a importare,
configurare e avviare i moduli senza contenere logica propria.

COMPATIBILITA' WAYLAND:
Su Wayland nativo, QWidget.move() e' ignorato dal compositor,
QCursor.pos() restituisce coordinate relative alla finestra, e
X11BypassWindowManagerHint non ha effetto. Per garantire il
funzionamento completo, adottiamo una strategia a due livelli:

1. Forziamo QT_QPA_PLATFORM=xcb per usare XWayland, dove tutte
   le API X11 funzionano correttamente (move, cursor, bypass WM).
2. L'icona volante usa QWindow.startSystemMove() come metodo
   primario per il drag, che funziona su qualsiasi compositor.

Il QT_QPA_PLATFORM DEVE essere impostato PRIMA di importare
qualsiasi modulo PySide6.
"""

from __future__ import annotations

import os
import sys

# Forza il backend X11/XWayland su Wayland.
# DEVE essere impostato PRIMA di importare PySide6.
_is_wayland = (
    os.environ.get("XDG_SESSION_TYPE") == "wayland"
    or bool(os.environ.get("WAYLAND_DISPLAY"))
)
if _is_wayland and not os.environ.get("QT_QPA_PLATFORM"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QTimer, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from config.constants import AppMeta, PathDefaults, LogDefaults
from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
from ui.main_window import MainWindow
from ui.overlay_window import OverlayWindow
from ui.tray_icon import TrayIcon
from ui.styles.breeze_dark import build_stylesheet


def _setup_logging() -> None:
    """Configura il sistema di logging con rotazione file."""
    PathDefaults.LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        PathDefaults.LOG_FILE,
        maxBytes=LogDefaults.MAX_BYTES,
        backupCount=LogDefaults.BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(
        getattr(logging, LogDefaults.FILE_LEVEL, logging.DEBUG),
    )
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(
        getattr(logging, LogDefaults.CONSOLE_LEVEL, logging.WARNING),
    )
    console_fmt = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_fmt)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def main() -> None:
    """Orchestratore principale dell'applicazione MagicScribe."""
    _setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Avvio %s v%s", AppMeta.NAME, AppMeta.VERSION)
    logger.info(
        "Piattaforma Qt: %s (sessione: %s)",
        os.environ.get("QT_QPA_PLATFORM", "auto"),
        os.environ.get("XDG_SESSION_TYPE", "sconosciuto"),
    )

    app = QApplication(sys.argv)
    app.setApplicationName(AppMeta.NAME)
    app.setOrganizationName(AppMeta.ORG_NAME)
    app.setApplicationDisplayName(AppMeta.DISPLAY_NAME)
    app.setDesktopFileName(AppMeta.ORG_NAME)

    app_dir = Path(__file__).resolve().parent
    png_dir = app_dir / "assets" / "icons" / "png"
    svg_path = app_dir / "assets" / "icons" / "magicscribe.svg"
    if png_dir.exists():
        icon = QIcon()
        for size in (16, 22, 24, 32, 48, 64, 128, 256, 512):
            png_path = png_dir / f"magicscribe_{size}.png"
            if png_path.exists():
                icon.addFile(str(png_path), size=QSize(size, size))
        if not icon.isNull():
            app.setWindowIcon(icon)
        else:
            app.setWindowIcon(QIcon(str(svg_path)))
    elif svg_path.exists():
        app.setWindowIcon(QIcon(str(svg_path)))

    app.setQuitOnLastWindowClosed(True)
    app.setStyleSheet(build_stylesheet())

    settings = Settings(
        on_change=lambda key, val: event_bus.emit(
            "config_changed", key=key, value=val,
        ),
    )
    settings.load()

    controller = AppController(settings)

    main_window = MainWindow(controller)
    overlay = OverlayWindow(controller)
    overlay.show()
    main_window.set_overlay(overlay)
    tray = TrayIcon(controller, main_window)

    def _ensure_z_order() -> None:
        overlay.lower()
        if main_window.isVisible():
            main_window.raise_()
            main_window.activateWindow()

    if settings.get("show_control_on_start"):
        main_window.show()

    QTimer.singleShot(200, _ensure_z_order)

    logger.info("Applicazione avviata con successo")
    exit_code = app.exec()

    settings.save()
    logger.info("Applicazione terminata (codice %d)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
