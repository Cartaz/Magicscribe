"""Architectural guardrails for the strategic runtime boundary."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import qVersion

ROOT = Path(__file__).resolve().parents[2]


def test_qt_version_is_611_or_newer() -> None:
    version = tuple(int(part) for part in qVersion().split(".")[:3])
    assert version >= (6, 11, 0)


def test_runtime_uses_only_pyside6() -> None:
    candidates = [ROOT / "main.py", *sorted((ROOT / "ui").rglob("*.py"))]
    assert [
        path.relative_to(ROOT).as_posix()
        for path in candidates
        if "PyQt6" in path.read_text(encoding="utf-8")
    ] == []


def test_production_runtime_has_no_x11_rollback() -> None:
    candidates = [
        ROOT / "main.py",
        ROOT / "install.sh",
        ROOT / "ui" / "native" / "window_coordinator.py",
        ROOT / "ui" / "quick" / "overlay_surface.py",
    ]
    forbidden = ("x11_input_shape", "set_x11_click_through", "libx11", "libxext")
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in candidates
        if any(token in path.read_text(encoding="utf-8").lower() for token in forbidden)
    ]
    assert offenders == []


def test_wayland_is_the_only_production_qpa_contract() -> None:
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "richiede KDE Plasma su Wayland nativo" in source
    assert 'loadFromModule("MagicScribe", "WaylandControlPanel")' in source
    assert '"WaylandFloatingPalette"' in source
    assert '"ControlPanel" if' not in source


def test_shell_adapter_never_reaches_into_coordinator_privates() -> None:
    source = (ROOT / "ui" / "adapters" / "shell_adapter.py").read_text(encoding="utf-8")
    for token in ("._control_window", "._floating_window", "._absolute_positioning"):
        assert token not in source
    assert "setMask(" not in source
    assert "findChild(" not in source


def test_dead_cross_cutting_abstractions_are_removed() -> None:
    for relative in (
        "core/event_bus.py",
        "core/exceptions.py",
        "core/geometry.py",
        "tests/test_core/test_event_bus.py",
        "tests/test_core/test_geometry.py",
    ):
        assert not (ROOT / relative).exists()


def test_dependency_metadata_is_consolidated() -> None:
    assert (ROOT / "pyproject.toml").is_file()
    for relative in (
        "requirements.txt",
        "requirements-dev.txt",
        "constraints-release.txt",
        "constraints-ci.txt",
        "scripts/verify_release_constraints.py",
    ):
        assert not (ROOT / relative).exists()


def test_runtime_uses_background_settings_persistence_and_deterministic_close() -> None:
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "background_persistence=True" in source
    assert "settings.close()" in source


def test_legacy_qwidget_shell_is_removed() -> None:
    legacy_paths = [
        ROOT / "config" / "theme.py",
        ROOT / "ui" / "main_window.py",
        ROOT / "ui" / "overlay_window.py",
        ROOT / "ui" / "styles",
        ROOT / "ui" / "widgets",
    ]
    assert [path.relative_to(ROOT).as_posix() for path in legacy_paths if path.exists()] == []


def test_production_ui_modules_import() -> None:
    import ui.drawing_engine  # noqa: F401
    import ui.quick.drawing_canvas  # noqa: F401
    import ui.quick.overlay_surface  # noqa: F401
    import ui.tray_icon  # noqa: F401
