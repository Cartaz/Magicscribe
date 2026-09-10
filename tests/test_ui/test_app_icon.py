"""Regression checks for the canonical MagicScribe application icon."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[2]
ICON_PATH = ROOT / "assets" / "icons" / "magicscribe.svg"
CONTROL_PANEL_QML = ROOT / "ui" / "qml" / "MagicScribe" / "ControlPanel.qml"
FLOATING_PALETTE_QML = ROOT / "ui" / "qml" / "MagicScribe" / "FloatingPalette.qml"


def test_canonical_svg_icon_renders_with_transparent_outer_background() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    assert ICON_PATH.is_file()

    icon = QIcon(str(ICON_PATH))
    assert not icon.isNull()

    image = icon.pixmap(128, 128).toImage()
    assert not image.isNull()
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(64, 64).alpha() > 0


def test_qml_branding_uses_canonical_svg_directly() -> None:
    expected = '../../../assets/icons/magicscribe.svg'
    control_panel = CONTROL_PANEL_QML.read_text(encoding="utf-8")
    floating_palette = FLOATING_PALETTE_QML.read_text(encoding="utf-8")

    assert f'source: "{expected}"' in control_panel
    assert f'source: "{expected}"' in floating_palette
    assert "magicscribe_48.png" not in control_panel
    assert "magicscribe_48.png" not in floating_palette


def test_no_raster_copy_of_application_icon_is_kept() -> None:
    png_dir = ROOT / "assets" / "icons" / "png"
    assert not png_dir.exists() or not any(png_dir.glob("magicscribe_*.png"))
