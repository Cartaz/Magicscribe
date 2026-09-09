"""Configurazione centralizzata di MagicScribe.

Espone costanti runtime e impostazioni persistenti.
"""

from config.constants import (
    AppMeta,
    HotkeyDefaults,
    ToolDefaults,
    PathDefaults,
    LogDefaults,
)
from config.settings import Settings

__all__ = [
    "AppMeta",
    "HotkeyDefaults",
    "ToolDefaults",
    "PathDefaults",
    "LogDefaults",
    "Settings",
]
