"""Costanti applicative non derivate dal dominio strumenti."""

from __future__ import annotations

import os
from pathlib import Path


def _xdg_config_home() -> Path:
    return Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))


def _xdg_state_home() -> Path:
    return Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state"))


def _xdg_data_home() -> Path:
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))


class AppMeta:
    NAME: str = "MagicScribe"
    DISPLAY_NAME: str = "MagicScribe"
    DESCRIPTION: str = "Annotazioni sullo schermo — standalone"
    VERSION: str = "2.0.0"
    ORG_NAME: str = "magicscribe"
    DOMAIN: str = "org.magicscribe"


class PathDefaults:
    CONFIG_DIR: Path = _xdg_config_home() / AppMeta.ORG_NAME
    SETTINGS_FILE: Path = CONFIG_DIR / "settings.json"
    LOG_DIR: Path = _xdg_state_home() / AppMeta.ORG_NAME
    LOG_FILE: Path = LOG_DIR / "magicscribe.log"
    DESKTOP_FILE: Path = _xdg_data_home() / "applications" / f"{AppMeta.ORG_NAME}.desktop"


class HotkeyDefaults:
    """Unica sorgente di verità delle scorciatoie runtime."""

    TOGGLE_DRAW: str = "F9"
    TOGGLE_VISIBILITY: str = "Ctrl+Shift+F9"
    CLEAR: str = "Shift+F9"
    UNDO: str = "F8"
    REDO: str = "Shift+F8"
    MINIMIZE: str = "Ctrl+M"
    QUIT_APP: str = "Ctrl+Q"


class LogDefaults:
    MAX_BYTES: int = 5 * 1024 * 1024
    BACKUP_COUNT: int = 3
    CONSOLE_LEVEL: str = "WARNING"
    FILE_LEVEL: str = "DEBUG"
