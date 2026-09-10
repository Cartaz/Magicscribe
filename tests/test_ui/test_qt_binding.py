"""Smoke test del binding Qt e dei guardrail della migrazione."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import qVersion


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


def test_legacy_qwidget_fallback_is_removed() -> None:
    root = Path(__file__).resolve().parents[2]
    legacy_paths = [
        root / "config" / "theme.py",
        root / "ui" / "main_window.py",
        root / "ui" / "main_window_components.py",
        root / "ui" / "overlay_window.py",
        root / "ui" / "styles",
        root / "ui" / "widgets",
    ]
    assert [path.relative_to(root).as_posix() for path in legacy_paths if path.exists()] == []


def test_runtime_shell_has_no_legacy_window_references() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime_files = [
        root / "main.py",
        root / "ui" / "native" / "window_coordinator.py",
        root / "ui" / "quick" / "overlay_surface.py",
        root / "ui" / "quick" / "drawing_canvas.py",
    ]
    forbidden = ("FloatingIcon", "MainWindow", "OverlayWindow")
    offenders = [
        path.relative_to(root).as_posix()
        for path in runtime_files
        if any(token in path.read_text(encoding="utf-8") for token in forbidden)
    ]
    assert offenders == []


def test_x11_diagnostic_rollback_is_removed() -> None:
    root = Path(__file__).resolve().parents[2]
    assert not (root / "ui" / "native" / "x11_input_shape.py").exists()
    overlay_source = (root / "ui" / "quick" / "overlay_surface.py").read_text(
        encoding="utf-8"
    )
    assert "set_x11_click_through" not in overlay_source
    assert "ui.native.x11_input_shape" not in overlay_source


def test_production_runtime_does_not_load_qss() -> None:
    root = Path(__file__).resolve().parents[2]
    main_source = (root / "main.py").read_text(encoding="utf-8")
    tray_source = (root / "ui" / "tray_icon.py").read_text(encoding="utf-8")

    assert "build_stylesheet" not in main_source
    assert "setStyleSheet(" not in main_source
    assert "ui.styles" not in main_source
    assert "config.theme" not in tray_source


def test_runtime_uses_background_settings_persistence_and_deterministic_close() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "main.py").read_text(encoding="utf-8")
    assert "background_persistence=True" in source
    assert "settings.close()" in source


def test_pure_geometry_lives_in_core_and_dead_event_bridge_is_removed() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "core" / "geometry.py").is_file()
    assert not (root / "ui" / "geometry_utils.py").exists()
    assert not (root / "ui" / "event_bridge.py").exists()
    drawing_engine = (root / "ui" / "drawing_engine.py").read_text(encoding="utf-8")
    assert "ui.geometry_utils" not in drawing_engine
    assert "from core.models import" in drawing_engine


def test_neu_button_pressed_state_does_not_toggle_effect_layers() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "ui" / "qml" / "MagicScribe" / "NeuButton.qml"
    ).read_text(encoding="utf-8")
    assert "readonly property bool insetState" not in source
    assert "visible: control.selected" in source
    assert "opacity: control.pressed ? 0.72 : 1.0" in source
    assert "border.width: control.pressed || control.activeFocus ? 1 : 0" in source


def test_production_ui_modules_import_with_pyside6() -> None:
    import ui.drawing_engine  # noqa: F401
    import ui.quick.drawing_canvas  # noqa: F401
    import ui.quick.overlay_surface  # noqa: F401
    import ui.tray_icon  # noqa: F401
