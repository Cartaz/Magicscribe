"""Configurazione centralizzata di MagicScribe.

Espone i moduli di configurazione: tema, costanti e impostazioni.
"""

from config.theme import ThemeColors
from config.constants import (
    AppMeta, UIDefaults, HotkeyDefaults, ToolDefaults,
    PathDefaults, LogDefaults,
)
from config.settings import Settings

__all__ = [
    "ThemeColors",
    "AppMeta",
    "UIDefaults",
    "HotkeyDefaults",
    "ToolDefaults",
    "PathDefaults",
    "LogDefaults",
    "Settings",
]
