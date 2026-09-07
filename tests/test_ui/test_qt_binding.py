"""Smoke test del binding Qt usato dalla UI."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
from core.models import ToolType
from ui.main_window import MainWindow
from ui.overlay_window import OverlayWindow

_APP = QApplication.instance() or QApplication([])


def test_qt_version_is_611_or_newer() -> None:
    version = tuple(int(part) for part in qVersion().split(".")[:3])
    assert version >= (6, 11, 0)


def test_no_pyqt6_references_remain_in_runtime_sources() -> None:
    root = Path(__file__).resolve().parents[2]
    candidates = [root / "main.py", *sorted((root / "ui").rglob("*.py"))]
    offenders = [
        path.relative_to(root).as_posix()
        for path in candidates
        if "PyQt6" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_runtime_shell_does_not_use_legacy_floating_widget() -> None:
    """Il widget floating legacy resta solo nel fallback/test QWidget."""
    root = Path(__file__).resolve().parents[2]
    runtime_files = [
        root / "main.py",
        root / "ui" / "native" / "window_coordinator.py",
    ]
    offenders = [
        path.relative_to(root).as_posix()
        for path in runtime_files
        if "FloatingIcon" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_runtime_does_not_use_legacy_overlay_widget() -> None:
    """M5 deve usare QQuickWindow/QQuickPaintedItem nel bootstrap runtime."""
    root = Path(__file__).resolve().parents[2]
    runtime_files = [
        root / "main.py",
        root / "ui" / "native" / "window_coordinator.py",
        root / "ui" / "quick" / "overlay_surface.py",
        root / "ui" / "quick" / "drawing_canvas.py",
    ]
    offenders = [
        path.relative_to(root).as_posix()
        for path in runtime_files
        if "OverlayWindow" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_widget_modules_import_with_pyside6() -> None:
    import ui.drawing_engine  # noqa: F401
    import ui.event_bridge  # noqa: F401
    import ui.main_window  # noqa: F401
    import ui.overlay_window  # noqa: F401
    import ui.tray_icon  # noqa: F401


def test_legacy_windows_construct_and_sync_under_pyside6(tmp_path) -> None:
    """Il fallback legacy resta costruibile finche' la parita' desktop e' aperta."""
    event_bus.clear()
    settings = Settings(path=tmp_path / "ui_settings.json")
    settings.set("last_tool", "circle")
    controller = AppController(settings)

    main_window = MainWindow(controller)
    overlay = OverlayWindow(controller)
    main_window.set_overlay(overlay)

    try:
        assert controller.get_current_tool() == ToolType.CIRCLE
        assert main_window._tool_selector._current == ToolType.CIRCLE
        assert main_window._color_size_picker._tool_type == ToolType.CIRCLE
        assert len(main_window._shortcuts) == 7
        assert len(overlay._shortcuts) == 5
    finally:
        main_window.deleteLater()
        overlay.deleteLater()
        event_bus.clear()
        _APP.processEvents()
