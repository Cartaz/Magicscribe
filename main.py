#!/usr/bin/env python3
"""MagicScribe — bootstrap dell'applicazione.

Qt Quick possiede l'intera shell runtime; Python mantiene wiring, lifecycle,
integrazione desktop e stato canonico. Il core applicativo resta indipendente
dalla presentazione QML.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

# Manteniamo temporaneamente XWayland finche' la parita' desktop/Wayland non
# viene verificata separatamente. Deve precedere qualsiasi import PySide6.
_is_wayland = (
    os.environ.get("XDG_SESSION_TYPE") == "wayland"
    or bool(os.environ.get("WAYLAND_DISPLAY"))
)
if _is_wayland and not os.environ.get("QT_QPA_PLATFORM"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtCore import QTimer, QSize
from PySide6.QtGui import QIcon, QWindow
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from config.constants import AppMeta, PathDefaults, LogDefaults
from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.shell_adapter import ShellAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.models.tool_list_model import ToolListModel
from ui.native.global_shortcuts import GlobalShortcutService
from ui.native.window_coordinator import WindowCoordinator
from ui.quick.overlay_surface import OverlaySurface
from ui.tray_icon import TrayIcon


def _setup_logging() -> None:
    """Configura logging su file rotante e stderr."""
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
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(
        getattr(logging, LogDefaults.CONSOLE_LEVEL, logging.WARNING),
    )
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def _set_application_icon(app: QApplication, app_dir: Path) -> None:
    """Carica le icone pre-renderizzate senza duplicare policy altrove."""
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
            return

    if svg_path.exists():
        app.setWindowIcon(QIcon(str(svg_path)))


def _portal_parent_window(window: QWindow) -> str:
    """Restituisce il parent_window XDG per il backend Qt attuale."""
    if QApplication.platformName().lower() != "xcb":
        return ""
    xid = int(window.winId())
    return f"x11:{xid:x}" if xid else ""


def _create_floating_palette(
    engine: QQmlApplicationEngine,
    drawing_adapter: DrawingAdapter,
    shell_adapter: ShellAdapter,
    logger: logging.Logger,
) -> tuple[QQmlComponent, QWindow]:
    """Istanzia la seconda top-level window QML con dipendenze esplicite."""
    component = QQmlComponent(engine)
    component.loadFromModule("MagicScribe", "FloatingPalette")

    if not component.isReady():
        for error in component.errors():
            logger.critical("Errore QML FloatingPalette: %s", error.toString())
        raise SystemExit(1)

    obj = component.createWithInitialProperties({
        "drawingAdapter": drawing_adapter,
        "shellAdapter": shell_adapter,
    })
    if not isinstance(obj, QWindow):
        for error in component.errors():
            logger.critical("Errore creazione FloatingPalette: %s", error.toString())
        if obj is not None:
            obj.deleteLater()
        raise SystemExit(1)

    return component, obj


def main() -> None:
    """Crea servizi, adapter, superfici Qt Quick e avvia l'event loop."""
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
    app.setQuitOnLastWindowClosed(True)

    app_dir = Path(__file__).resolve().parent
    _set_application_icon(app, app_dir)

    settings = Settings(
        on_change=lambda key, val: event_bus.emit(
            "config_changed", key=key, value=val,
        ),
        background_persistence=True,
    )
    settings.load()
    controller = AppController(settings)

    drawing_adapter = DrawingAdapter(controller)
    tool_adapter = ToolAdapter(controller)
    tool_model = ToolListModel()

    # Deve precedere la creazione di qualsiasi QQuickWindow traslucida.
    QQuickWindow.setDefaultAlphaBuffer(True)

    overlay_surface = OverlaySurface(drawing_adapter, tool_adapter)
    overlay_surface.show()
    window_coordinator = WindowCoordinator(overlay_surface.window)
    global_shortcuts = GlobalShortcutService(controller)
    shell_adapter = ShellAdapter(window_coordinator, global_shortcuts)

    drawing_adapter.activeChanged.connect(
        lambda: QTimer.singleShot(50, window_coordinator.ensure_z_order)
    )

    exit_code = 1
    try:
        engine = QQmlApplicationEngine()
        qml_import_root = app_dir / "ui" / "qml"
        engine.addImportPath(str(qml_import_root))
        engine.setInitialProperties({
            "drawingAdapter": drawing_adapter,
            "toolAdapter": tool_adapter,
            "shellAdapter": shell_adapter,
            "toolModel": tool_model,
        })
        engine.loadFromModule("MagicScribe", "ControlPanel")

        roots = engine.rootObjects()
        if not roots or not isinstance(roots[0], QWindow):
            logger.critical("Impossibile creare il pannello QML MagicScribe")
            raise SystemExit(1)

        control_window = roots[0]
        floating_component, floating_window = _create_floating_palette(
            engine,
            drawing_adapter,
            shell_adapter,
            logger,
        )
        window_coordinator.set_control_window(control_window)
        window_coordinator.set_floating_window(floating_window)

        global_shortcuts.start(_portal_parent_window(control_window))
        tray = TrayIcon(controller, window_coordinator.restore_control_panel)

        if settings.get("show_control_on_start"):
            window_coordinator.show_control_panel()

        QTimer.singleShot(200, window_coordinator.ensure_z_order)

        logger.info("Applicazione avviata con shell e overlay Qt Quick")
        exit_code = app.exec()
    finally:
        global_shortcuts.shutdown()
        window_coordinator.shutdown()
        settings.close()

    logger.info("Applicazione terminata (codice %d)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
