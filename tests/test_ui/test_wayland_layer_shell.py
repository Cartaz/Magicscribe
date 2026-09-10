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
        assert "LayerShell.Window.margins.left:" in source
        assert "LayerShell.Window.margins.top:" in source
        assert "LayerShell.Window.margins.right:" in source
        assert "LayerShell.Window.margins.bottom:" in source
        assert "LayerShell.Window.margins: ({" not in source
        assert "layerShellPlacement: true" in source
        assert "flags: Qt.FramelessWindowHint" in source
        assert "WindowStaysOnTopHint" not in source
        assert "Qt.Tool" not in source

    assert "KeyboardInteractivityOnDemand" in control
    assert "KeyboardInteractivityNone" in floating


def test_wayland_control_drag_moves_item_inside_stationary_surface() -> None:
    control = _source("ControlPanel.qml")
    wayland = _source("WaylandControlPanel.qml")

    assert "layerShellFullscreen: true" in wayland
    assert "LayerShell.Window.AnchorTop" in wayland
    assert "LayerShell.Window.AnchorBottom" in wayland
    assert "LayerShell.Window.AnchorLeft" in wayland
    assert "LayerShell.Window.AnchorRight" in wayland
    assert "LayerShell.Window.margins.left: 0" in wayland
    assert "LayerShell.Window.margins.top: 0" in wayland

    assert "id: toolbarHost" in control
    assert "target: root.layerShellFullscreen ? toolbarHost : null" in control
    assert "root.shellAdapter.set_control_input_region(" in control
    assert "onXChanged: root.syncLayerShellInputRegion()" in control
    assert "onYChanged: root.syncLayerShellInputRegion()" in control

    # The control surface itself must remain stationary during the gesture.
    assert "setWaylandDragMargins" not in wayland
    assert "global_cursor_position()" not in wayland
    assert "pressGlobalX" not in wayland
    assert "pressGlobalY" not in wayland


def test_wayland_floating_drag_moves_item_inside_stationary_surface() -> None:
    floating = _source("FloatingPalette.qml")
    wayland = _source("WaylandFloatingPalette.qml")
    shell_adapter = (ROOT / "ui" / "adapters" / "shell_adapter.py").read_text(
        encoding="utf-8"
    )

    assert "layerShellFullscreen: true" in wayland
    assert "LayerShell.Window.AnchorTop" in wayland
    assert "LayerShell.Window.AnchorBottom" in wayland
    assert "LayerShell.Window.AnchorLeft" in wayland
    assert "LayerShell.Window.AnchorRight" in wayland
    assert "LayerShell.Window.margins.left: 0" in wayland
    assert "LayerShell.Window.margins.top: 0" in wayland

    assert "id: paletteHost" in floating
    assert "target: root.layerShellFullscreen ? paletteHost : null" in floating
    assert "root.shellAdapter.set_floating_input_region(" in floating
    assert "onXChanged: root.syncLayerShellInputRegion()" in floating
    assert "onYChanged: root.syncLayerShellInputRegion()" in floating
    assert "root.shellAdapter.controlLogoCenterX" in floating
    assert "root.shellAdapter.controlLogoCenterY" in floating
    assert "- paletteHost.width / 2" in floating
    assert "- paletteHost.height / 2" in floating
    assert "def set_floating_input_region(" in shell_adapter
    assert "def controlLogoCenterX(" in shell_adapter
    assert "def controlLogoCenterY(" in shell_adapter
    assert 'findChild(QQuickItem, "minimizeButton")' in shell_adapter
    assert "mapToScene(" in shell_adapter

    # Never move the layer-surface itself from pointer-local coordinates.
    assert "setWaylandDragMargins" not in wayland
    assert "moveLayerShellBy" not in floating
    assert "xAxis.onActiveValueChanged" not in floating
    assert "yAxis.onActiveValueChanged" not in floating

    # Minimize must align to the actual logo, not merely to toolbarHost's corner.
    assert "root.shellAdapter.controlPanelX" not in floating
    assert "root.shellAdapter.controlPanelY" not in floating

    # Restore is the exact inverse: move toolbarHost so its logo center matches
    # the current floating icon center before showing the control panel again.
    assert "def _floating_palette_center(" in shell_adapter
    assert "def _align_control_logo_to_floating(" in shell_adapter
    assert "self._align_control_logo_to_floating()" in shell_adapter
    assert 'control.setProperty(\n            "layerShellPanelX"' in shell_adapter
    assert 'control.setProperty(\n            "layerShellPanelY"' in shell_adapter


def test_qmldir_exports_wayland_components() -> None:
    qmldir = (QML_DIR / "qmldir").read_text(encoding="utf-8")
    assert "WaylandLayerSurface 1.0 WaylandLayerSurface.qml" in qmldir
    assert "WaylandControlPanel 1.0 WaylandControlPanel.qml" in qmldir
    assert "WaylandFloatingPalette 1.0 WaylandFloatingPalette.qml" in qmldir
