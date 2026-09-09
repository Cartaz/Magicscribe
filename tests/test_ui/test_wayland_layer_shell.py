"""Static guardrails for the KDE layer-shell QML boundary.

GitHub Actions runs with PySide6's offscreen QPA and does not provide the
CachyOS/Plasma system QML module. Runtime loading is therefore part of the local
Wayland gate; CI still verifies that the platform-specific QML keeps the roles
and input/focus policy we depend on.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QML_DIR = ROOT / "ui" / "qml" / "MagicScribe"


def _source(name: str) -> str:
    return (QML_DIR / name).read_text(encoding="utf-8")


def test_wayland_overlay_uses_top_layer_without_keyboard_focus() -> None:
    source = _source("WaylandLayerSurface.qml")
    assert "import org.kde.layershell 1.0 as LayerShell" in source
    assert "LayerShell.Window.LayerTop" in source
    assert "LayerShell.Window.KeyboardInteractivityNone" in source
    assert "LayerShell.Window.AnchorTop" in source
    assert "LayerShell.Window.AnchorBottom" in source
    assert "LayerShell.Window.AnchorLeft" in source
    assert "LayerShell.Window.AnchorRight" in source
    assert 'LayerShell.Window.scope: "magicscribe-overlay"' in source
    assert "flags: Qt.FramelessWindowHint" in source
    assert "Qt.Tool" not in source
    assert "WindowStaysOnTopHint" not in source
    assert "WindowDoesNotAcceptFocus" not in source


def test_wayland_shell_windows_are_above_overlay() -> None:
    control = _source("WaylandControlPanel.qml")
    floating = _source("WaylandFloatingPalette.qml")

    for source in (control, floating):
        assert "LayerShell.Window.LayerOverlay" in source
        assert "LayerShell.Window.margins" in source
        assert "layerShellPlacement: true" in source
        assert "flags: Qt.FramelessWindowHint" in source
        assert "WindowStaysOnTopHint" not in source
        assert "Qt.Tool" not in source

    assert "KeyboardInteractivityOnDemand" in control
    assert "KeyboardInteractivityNone" in floating


def test_layer_shell_drag_uses_margins_not_system_move() -> None:
    control = _source("ControlPanel.qml")
    floating = _source("FloatingPalette.qml")

    for source in (control, floating):
        assert "moveLayerShellBy" in source
        assert "xAxis.onActiveValueChanged" in source
        assert "yAxis.onActiveValueChanged" in source
        assert "active && !root.layerShellPlacement" in source


def test_qmldir_exports_wayland_components() -> None:
    qmldir = (QML_DIR / "qmldir").read_text(encoding="utf-8")
    assert "WaylandLayerSurface 1.0 WaylandLayerSurface.qml" in qmldir
    assert "WaylandControlPanel 1.0 WaylandControlPanel.qml" in qmldir
    assert "WaylandFloatingPalette 1.0 WaylandFloatingPalette.qml" in qmldir
