"""Costanti globali dell'applicazione MagicScribe.

Organizzate per dominio funzionale in classi dedicate.
I percorsi sono calcolati dinamicamente tramite pathlib e XDG.
"""

from __future__ import annotations

import os
from pathlib import Path


def _xdg_config_home() -> Path:
    """Ritorna il percorso XDG_CONFIG_HOME per l'utente corrente."""
    return Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))


def _xdg_state_home() -> Path:
    """Ritorna il percorso XDG_STATE_HOME per l'utente corrente."""
    return Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state"))


class AppMeta:
    """Metadati dell'applicazione."""
    NAME: str = "MagicScribe"
    DISPLAY_NAME: str = "MagicScribe"
    DESCRIPTION: str = "Annotazioni sullo schermo — standalone"
    VERSION: str = "2.0.0"
    ORG_NAME: str = "magicscribe"
    DOMAIN: str = "org.magicscribe"


class PathDefaults:
    """Percorsi predefiniti calcolati dinamicamente."""
    CONFIG_DIR: Path = _xdg_config_home() / AppMeta.ORG_NAME
    SETTINGS_FILE: Path = _xdg_config_home() / AppMeta.ORG_NAME / "settings.json"
    LOG_DIR: Path = _xdg_state_home() / AppMeta.ORG_NAME
    LOG_FILE: Path = _xdg_state_home() / AppMeta.ORG_NAME / "magicscribe.log"
    DESKTOP_FILE: Path = (
        Path.home() / ".local" / "share" / "applications"
        / f"{AppMeta.ORG_NAME}.desktop"
    )


class UIDefaults:
    """Valori predefiniti per l'interfaccia utente."""
    WINDOW_MIN_WIDTH: int = 300
    WINDOW_MAX_WIDTH: int = 340
    WINDOW_MIN_HEIGHT: int = 500
    CARD_PADDING: int = 12
    CARD_MARGIN: int = 8
    CARD_RADIUS: int = 6
    BORDER_WIDTH: int = 1
    BUTTON_HEIGHT: int = 30
    STATUS_DOT_SIZE: int = 10
    SHORTCUT_BADGE_WIDTH: int = 64
    ANIMATION_DURATION_MS: int = 200


class HotkeyDefaults:
    """Scorciatoie da tastiera predefinite."""
    TOGGLE_DRAW: str = "F9"
    TOGGLE_VISIBILITY: str = "Ctrl+Shift+F9"
    CLEAR: str = "Shift+F9"
    UNDO: str = "F8"
    REDO: str = "Shift+F8"
    MINIMIZE: str = "Ctrl+M"
    QUIT_APP: str = "Ctrl+Q"


class ToolDefaults:
    """Valori predefiniti per gli strumenti di disegno.

    Nota: i colori di default usano solo la palette conforme
    a Breeze Dark (nessun blu come accento, §5.1.1).
    """
    PEN_COLOR: str = "#ff0000"
    PEN_SIZE: int = 5
    ERASER_SIZE: int = 40
    LINE_COLOR: str = "#27ae60"
    LINE_SIZE: int = 3
    RECT_COLOR: str = "#ff0000"
    RECT_SIZE: int = 3
    CIRCLE_COLOR: str = "#ff8800"
    CIRCLE_SIZE: int = 3
    SMOOTH_COLOR: str = "#ff0000"
    SMOOTH_SIZE: int = 5
    OVERLAY_OPACITY: float = 0.75
    UNDO_MAX_DEPTH: int = 50


class LogDefaults:
    """Parametri di logging."""
    MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
    BACKUP_COUNT: int = 3
    CONSOLE_LEVEL: str = "WARNING"
    FILE_LEVEL: str = "DEBUG"
