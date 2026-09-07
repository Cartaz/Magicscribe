#!/usr/bin/env python3
"""MagicScribe — bootstrap dell'applicazione.

M4 usa Qt Quick/QML per pannello di controllo e floating palette, mantenendo
l'overlay QWidget/QPainter legacy finche' la parita' del workflow di disegno
non sara' verificata. main.py resta limitato a wiring e lifecycle.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

# Mantiene la policy XWayland esistente durante la migrazione dell'overlay.
# Deve essere impostata prima di importare PySide6.
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
from ui.native.window_coordinator import WindowCoordinator
from ui.overlay_window import OverlayWindow
from ui.styles.breeze_dark import build_stylesheet
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
    """Crea servizi, adapter, shell Qt/QML e avvia l'event loop."""
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

    # QSS resta temporaneamente per il codice QWidget legacy ancora presente.
    # Le due finestre runtime della shell usano esclusivamente Theme.qml.
    app.setStyleSheet(build_stylesheet())

    settings = Settings(
        on_change=lambda key, val: event_bus.emit(
            "config_changed", key=key, value=val,
        ),
    )
    settings.load()
    controller = AppController(settings)

    # Overlay legacy: intenzionalmente preservato fino alla milestone M5.
    overlay = OverlayWindow(controller)
    overlay.show()

    window_coordinator = WindowCoordinator(overlay)
    drawing_adapter = DrawingAdapter(controller)
    tool_adapter = ToolAdapter(controller)
    tool_model = ToolListModel()
    shell_adapter = ShellAdapter(window_coordinator)

    # Deve precedere la creazione della prima QQuickWindow; prepara anche la
    # futura migrazione dell'overlay traslucido senza cambiare il renderer ora.
    QQuickWindow.setDefaultAlphaBuffer(True)

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
        window_coordinator.shutdown()
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

    tray = TrayIcon(controller, window_coordinator.restore_control_panel)

    if settings.get("show_control_on_start"):
        window_coordinator.show_control_panel()

    QTimer.singleShot(200, window_coordinator.ensure_z_order)

    # Mantiene riferimenti espliciti agli oggetti con lifecycle applicativo.
    runtime_refs = (
        engine,
        floating_component,
        floating_window,
        drawing_adapter,
        tool_adapter,
        tool_model,
        shell_adapter,
        tray,
        window_coordinator,
        overlay,
    )
    del runtime_refs  # i local restano vivi fino al ritorno da app.exec()

    logger.info("Applicazione avviata con shell QML")
    exit_code = app.exec()

    window_coordinator.shutdown()
    settings.save()
    logger.info("Applicazione terminata (codice %d)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
