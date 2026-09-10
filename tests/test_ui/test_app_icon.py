"""Regression checks for the canonical MagicScribe application icon."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[2]
ICON_PATH = ROOT / "assets" / "icons" / "magicscribe.svg"


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
