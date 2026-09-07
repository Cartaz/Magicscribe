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


def test_qt_version_is_611_or_newer():
    assert tuple(int(p) for p in qVersion().split(".")[:3]) >= (6, 11, 0)


def test_runtime_compliance_guardrails():
    root = Path(__file__).resolve().parents[2]
    main_source = (root / "main.py").read_text(encoding="utf-8")
    tray_source = (root / "ui" / "tray_icon.py").read_text(encoding="utf-8")
    assert "PyQt6" not in main_source
    assert "build_stylesheet" not in main_source
    assert "setStyleSheet(" not in main_source
    assert "config.theme" not in tray_source
    assert "ThemeColors" not in tray_source
    assert "background_persistence=True" in main_source
    assert "settings.close()" in main_source
    assert (root / "core" / "geometry.py").is_file()
    assert not (root / "ui" / "geometry_utils.py").exists()
    assert not (root / "ui" / "event_bridge.py").exists()


def test_runtime_does_not_use_legacy_windows():
    root = Path(__file__).resolve().parents[2]
    sources = [(root / "main.py").read_text(encoding="utf-8"), (root / "ui" / "native" / "window_coordinator.py").read_text(encoding="utf-8")]
    assert all("FloatingIcon" not in source and "OverlayWindow" not in source for source in sources)


def test_neu_button_selected_and_pressed_use_inset_state():
    root = Path(__file__).resolve().parents[2]
    source = (root / "ui" / "qml" / "MagicScribe" / "NeuButton.qml").read_text(encoding="utf-8")
    assert "readonly property bool insetState: selected || pressed" in source
    assert "InsetSurface {" in source


def test_widget_modules_import_with_pyside6():
    import ui.drawing_engine  # noqa: F401
    import ui.main_window  # noqa: F401
    import ui.overlay_window  # noqa: F401
    import ui.tray_icon  # noqa: F401


def test_legacy_windows_construct_and_sync_under_pyside6(tmp_path):
    event_bus.clear()
    settings = Settings(path=tmp_path / "legacy.json")
    settings.set("last_tool", "circle")
    controller = AppController(settings)
    main_window = MainWindow(controller)
    overlay = OverlayWindow(controller)
    main_window.set_overlay(overlay)
    try:
        assert controller.get_current_tool() == ToolType.CIRCLE
        assert main_window._tool_selector._current == ToolType.CIRCLE
        assert len(main_window._shortcuts) == 7
        assert len(overlay._shortcuts) == 5
    finally:
        main_window.deleteLater()
        overlay.deleteLater()
        event_bus.clear()
        _APP.processEvents()
