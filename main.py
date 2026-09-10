#!/usr/bin/env python3
"""Bootstrap production di MagicScribe per KDE Plasma / Wayland nativo."""

from __future__ import annotations

import faulthandler
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

_is_wayland_session = (
    os.environ.get("XDG_SESSION_TYPE") == "wayland"
    or bool(os.environ.get("WAYLAND_DISPLAY"))
)
if _is_wayland_session:
    requested = os.environ.get("QT_QPA_PLATFORM", "").lower()
    if requested in {"", "xcb"}:
        os.environ["QT_QPA_PLATFORM"] = "wayland"

from PySide6.QtCore import QTimer, QSize
from PySide6.QtGui import QIcon, QWindow
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from config.constants import AppMeta, LogDefaults, PathDefaults
from config.settings import Settings
from core.app_controller import AppController
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.shell_adapter import ShellAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.models.tool_list_model import ToolListModel
from ui.native.global_shortcuts import GlobalShortcutService
from ui.native.layer_shell import configure_layer_shell
from ui.native.single_instance import SingleInstanceGuard
from ui.native.window_coordinator import WindowCoordinator
from ui.quick.overlay_surface import OverlaySurface
from ui.tray_icon import TrayIcon


def _setup_logging() -> None:
    PathDefaults.LOG_DIR.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        PathDefaults.LOG_FILE,
        maxBytes=LogDefaults.MAX_BYTES,
        backupCount=LogDefaults.BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, LogDefaults.FILE_LEVEL, logging.DEBUG))
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, LogDefaults.CONSOLE_LEVEL, logging.WARNING))
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def _set_application_icon(app: QApplication, app_dir: Path) -> None:
    png_dir = app_dir / "assets" / "icons" / "png"
    svg_path = app_dir / "assets" / "icons" / "magicscribe.svg"
    if png_dir.exists():
        icon = QIcon()
        for size in (16, 22, 24, 32, 48, 64, 128, 256, 512):
            path = png_dir / f"magicscribe_{size}.png"
            if path.exists():
                icon.addFile(str(path), size=QSize(size, size))
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
    component = QQmlComponent(engine)
    component.loadFromModule("MagicScribe", "WaylandFloatingPalette")
    if not component.isReady():
        for error in component.errors():
            logger.critical("Errore QML WaylandFloatingPalette: %s", error.toString())
        raise SystemExit(1)

    obj = component.createWithInitialProperties(
        {"drawingAdapter": drawing_adapter, "shellAdapter": shell_adapter}
    )
    if not isinstance(obj, QWindow):
        if obj is not None:
            obj.deleteLater()
        raise SystemExit("WaylandFloatingPalette non ha creato una QWindow")
    return component, obj


def main() -> None:
    faulthandler.enable(all_threads=True)
    _setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Avvio %s v%s", AppMeta.NAME, AppMeta.VERSION)

    instance_guard = SingleInstanceGuard()
    if not instance_guard.acquire():
        logger.warning("%s è già in esecuzione", AppMeta.NAME)
        return

    try:
        app = QApplication(sys.argv)
        app.setApplicationName(AppMeta.NAME)
        app.setOrganizationName(AppMeta.ORG_NAME)
        app.setApplicationDisplayName(AppMeta.DISPLAY_NAME)
        app.setDesktopFileName(AppMeta.ORG_NAME)
        app.setQuitOnLastWindowClosed(True)

        platform_name = QApplication.platformName().lower()
        logger.info("Piattaforma Qt effettiva: %s", platform_name)
        if not _is_wayland_session or not platform_name.startswith("wayland"):
            logger.critical(
                "MagicScribe 2.x richiede KDE Plasma su Wayland nativo; "
                "sessione=%s, QPA=%s",
                os.environ.get("XDG_SESSION_TYPE", "sconosciuta"),
                platform_name,
            )
            raise SystemExit(2)
        logger.info("Backend Wayland nativo attivo")

        app_dir = Path(__file__).resolve().parent
        _set_application_icon(app, app_dir)

        settings = Settings(background_persistence=True)
        settings.load()
        controller = AppController(settings)
        drawing_adapter = DrawingAdapter(controller)
        tool_adapter = ToolAdapter(controller)
        tool_model = ToolListModel()
        window_coordinator = WindowCoordinator()
        global_shortcuts = GlobalShortcutService(controller)
        shell_adapter = ShellAdapter(window_coordinator, global_shortcuts)

        QQuickWindow.setDefaultAlphaBuffer(True)
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(app_dir / "ui" / "qml"))
        try:
            configure_layer_shell(engine)
        except RuntimeError as exc:
            logger.critical("Wayland layer-shell non disponibile: %s", exc)
            raise SystemExit(1) from exc

        engine.setInitialProperties(
            {
                "drawingAdapter": drawing_adapter,
                "toolAdapter": tool_adapter,
                "shellAdapter": shell_adapter,
                "toolModel": tool_model,
            }
        )

        overlay_surface = OverlaySurface(
            drawing_adapter,
            tool_adapter,
            qml_engine=engine,
        )
        overlay_surface.show()

        def ensure_window_order() -> None:
            overlay_surface.ensure_z_order()
            window_coordinator.ensure_z_order()

        drawing_adapter.activeChanged.connect(lambda: QTimer.singleShot(50, ensure_window_order))

        exit_code = 1
        try:
            engine.loadFromModule("MagicScribe", "WaylandControlPanel")
            roots = engine.rootObjects()
            if not roots or not isinstance(roots[0], QWindow):
                raise SystemExit("Impossibile creare WaylandControlPanel")

            control_window = roots[0]
            floating_component, floating_window = _create_floating_palette(
                engine,
                drawing_adapter,
                shell_adapter,
                logger,
            )
            window_coordinator.set_control_window(control_window)
            window_coordinator.set_floating_window(floating_window)

            if settings.get("show_control_on_start"):
                window_coordinator.show_control_panel()

            global_shortcuts.start("")
            tray = TrayIcon(controller, window_coordinator.restore_control_panel)
            QTimer.singleShot(200, ensure_window_order)

            logger.info("Applicazione avviata con shell e overlay Qt Quick")
            exit_code = app.exec()
            _ = tray, floating_component
        finally:
            global_shortcuts.shutdown()
            window_coordinator.shutdown()
            overlay_surface.shutdown()
            drawing_adapter.close()
            tool_adapter.close()
            settings.close()

        logger.info("Applicazione terminata (codice %d)", exit_code)
        raise SystemExit(exit_code)
    finally:
        instance_guard.release()


if __name__ == "__main__":
    main()
