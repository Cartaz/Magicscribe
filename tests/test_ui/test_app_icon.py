"""Regression check for the canonical MagicScribe application icon."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

ICON_PATH = Path(__file__).resolve().parents[2] / "assets" / "icons" / "magicscribe.svg"


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


def test_toolbar_logo_is_a_filter_free_mark_without_its_own_ring() -> None:
    # Drawn for 22-30 px: SVG filters and the app icon's thin orange ring
    # blur at that size; the button draws the ring and halo instead.
    logo = ICON_PATH.parent / "toolbar" / "logo.svg"
    source = logo.read_text(encoding="utf-8")
    assert "<filter" not in source
    assert "<circle" not in source

    image = QIcon(str(logo)).pixmap(30, 30).toImage()
    assert image.pixelColor(0, 29).alpha() == 0
    assert image.pixelColor(15, 15).alpha() > 0


def _mark(source: str) -> list[str]:
    # The mark group holds one nested group (the pen): it ends at the second </g>.
    start = source.index('<g id="mark">')
    end = source.index("</g>", source.index("</g>", start) + 1)
    return [line.strip() for line in source[start:end].splitlines()]


def test_app_icon_embeds_the_toolbar_mark_without_filters() -> None:
    # .desktop, tray and window show the same mark as the toolbar logo.
    app_icon = ICON_PATH.read_text(encoding="utf-8")
    toolbar_logo = (ICON_PATH.parent / "toolbar" / "logo.svg").read_text(encoding="utf-8")
    assert "<filter" not in app_icon
    assert _mark(app_icon) == _mark(toolbar_logo)
