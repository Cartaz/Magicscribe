"""Palette Breeze Dark del fallback QWidget legacy.

Il runtime Qt Quick usa esclusivamente `ui/qml/MagicScribe/Theme.qml`.
Questo modulo resta in-tree solo finche' il gate di parita' desktop non
consente di rimuovere la UI QWidget precedente.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _ThemeColors:
    """Token del solo fallback QWidget legacy."""
    PRIMARY: str = "#00bfa5"
    PRIMARY_DARK: str = "#00695c"
    PRIMARY_PRESSED: str = "#004d40"
    PRIMARY_HOVER: str = "#00d6b8"
    DANGER: str = "#db4105"
    DANGER_DARK: str = "#7a2400"
    DANGER_PRESSED: str = "#5c1a00"
    SUCCESS: str = "#27ae60"
    BG_MAIN: str = "#1b1e20"
    BG_CARD: str = "#232629"
    BG_SURFACE: str = "#2a2e32"
    BG_SURFACE_HOVER: str = "#31363b"
    BG_TOOLTIP: str = "#2a2e32"
    BORDER: str = "#3f4347"
    BORDER_ACTIVE: str = "#00bfa5"
    TEXT_PRIMARY: str = "#eff0f1"
    TEXT_SECONDARY: str = "#a0a4a8"
    TEXT_DIM: str = "#7f8c8d"
    TEXT_DISABLED: str = "#6b7076"
    SHORTCUT_BG: str = "rgba(255, 255, 255, 0.08)"
    SHORTCUT_BORDER: str = "#3f4347"
    OVERLAY_GRID: str = "rgba(255, 255, 255, 0.05)"
    SELECTION_BG: str = "#00695c"
    SELECTION_TEXT: str = "#ffffff"


ThemeColors = _ThemeColors()
