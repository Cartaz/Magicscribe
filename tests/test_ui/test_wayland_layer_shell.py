"""Static guardrails only for behavior CI cannot execute without KDE layer-shell."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QML_DIR = ROOT / "ui" / "qml" / "MagicScribe"


def _source(name: str) -> str:
    return (QML_DIR / name).read_text(encoding="utf-8")


def test_wayland_overlay_has_the_required_layer_role() -> None:
    source = _source("WaylandLayerSurface.qml")
    assert "import org.kde.layershell 1.0 as LayerShell" in source
    assert "LayerShell.Window.LayerTop" in source
    assert "LayerShell.Window.KeyboardInteractivityNone" in source
    for anchor in ("AnchorTop", "AnchorBottom", "AnchorLeft", "AnchorRight"):
        assert f"LayerShell.Window.{anchor}" in source
    assert 'LayerShell.Window.scope: "magicscribe-overlay"' in source


def test_wayland_shell_surfaces_are_stationary_overlay_layers() -> None:
    control = _source("WaylandControlPanel.qml")
    floating = _source("WaylandFloatingPalette.qml")
    for source in (control, floating):
        assert "LayerShell.Window.LayerOverlay" in source
        for anchor in ("AnchorTop", "AnchorBottom", "AnchorLeft", "AnchorRight"):
            assert f"LayerShell.Window.{anchor}" in source
        for side in ("left", "top", "right", "bottom"):
            assert f"LayerShell.Window.margins.{side}: 0" in source
        assert "layerShellPlacement" not in source
        assert "layerShellFullscreen" not in source
    assert "KeyboardInteractivityOnDemand" in control
    assert "KeyboardInteractivityNone" in floating


def test_control_drag_moves_only_the_internal_host() -> None:
    source = _source("ControlPanel.qml")
    assert "id: toolbarHost" in source
    assert "target: toolbarHost" in source
    assert "root.shellAdapter.set_control_input_region(" in source
    assert "onXChanged: root.syncLayerShellInputRegion()" in source
    assert "onYChanged: root.syncLayerShellInputRegion()" in source
    assert "startSystemMove" not in source
    assert "layerShellPlacement" not in source
    assert "layerShellFullscreen" not in source
    assert "layerShellMargin" not in source
    assert "LayerShell.Window.margins" not in source


def test_floating_drag_and_minimize_restore_use_internal_coordinates() -> None:
    source = _source("FloatingPalette.qml")
    assert "id: paletteHost" in source
    assert "target: paletteHost" in source
    assert "root.shellAdapter.set_floating_input_region(" in source
    assert "root.shellAdapter.controlLogoCenterX" in source
    assert "root.shellAdapter.controlLogoCenterY" in source
    assert "- paletteHost.width / 2" in source
    assert "- paletteHost.height / 2" in source
    assert "startSystemMove" not in source
    assert "layerShellPlacement" not in source
    assert "layerShellFullscreen" not in source
    assert "LayerShell.Window.margins" not in source


def test_qmldir_exports_only_live_components() -> None:
    qmldir = (QML_DIR / "qmldir").read_text(encoding="utf-8")
    assert "WaylandLayerSurface 1.0 WaylandLayerSurface.qml" in qmldir
    assert "WaylandControlPanel 1.0 WaylandControlPanel.qml" in qmldir
    assert "WaylandFloatingPalette 1.0 WaylandFloatingPalette.qml" in qmldir
    assert "NeuButton" not in qmldir
    assert "ShortcutBadge" not in qmldir
