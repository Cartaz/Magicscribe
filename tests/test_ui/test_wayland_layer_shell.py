"""Layer-shell roles that CI cannot exercise without a KDE compositor.

The surfaces only make sense with these roles (stacking layer, keyboard
policy, fullscreen anchoring), so a silent change here would break the app
on Plasma while every offscreen test keeps passing.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

_QML_DIR = Path(__file__).resolve().parents[2] / "ui" / "qml" / "MagicScribe"
_ASSIGNMENT = re.compile(r"^LayerShell\.Window\.([\w.]+):\s*(.*)$")
_ALL_ANCHORS = {
    "LayerShell.Window.AnchorTop",
    "LayerShell.Window.AnchorBottom",
    "LayerShell.Window.AnchorLeft",
    "LayerShell.Window.AnchorRight",
}


def _layer_shell_properties(name: str) -> dict[str, str]:
    properties: dict[str, str] = {}
    current: str | None = None
    for raw_line in (_QML_DIR / f"{name}.qml").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        match = _ASSIGNMENT.match(line)
        if match:
            current = match.group(1)
            properties[current] = match.group(2)
        elif current is not None and line.startswith("|"):
            properties[current] += f" {line}"
        else:
            current = None
    return properties


def _anchors(properties: dict[str, str]) -> set[str]:
    return {anchor.strip() for anchor in properties["anchors"].split("|")}


@pytest.mark.parametrize(
    ("name", "layer", "keyboard"),
    [
        ("WaylandLayerSurface", "LayerTop", "KeyboardInteractivityNone"),
        ("WaylandControlPanel", "LayerOverlay", "KeyboardInteractivityOnDemand"),
        ("WaylandFloatingPalette", "LayerOverlay", "KeyboardInteractivityNone"),
    ],
)
def test_surface_has_its_layer_shell_role(name: str, layer: str, keyboard: str) -> None:
    properties = _layer_shell_properties(name)

    assert properties["layer"] == f"LayerShell.Window.{layer}"
    assert properties["keyboardInteractivity"] == f"LayerShell.Window.{keyboard}"
    assert _anchors(properties) == _ALL_ANCHORS
    assert properties["exclusionZone"] == "-1"


@pytest.mark.parametrize("name", ["WaylandControlPanel", "WaylandFloatingPalette"])
def test_shell_surfaces_cover_the_whole_output(name: str) -> None:
    properties = _layer_shell_properties(name)

    for side in ("left", "top", "right", "bottom"):
        assert properties[f"margins.{side}"] == "0"
