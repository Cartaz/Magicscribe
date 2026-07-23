"""Gestione delle impostazioni utente persistenti.

Le impostazioni sono salvate in JSON nella directory XDG_CONFIG_HOME.
Supporta load/save/get/set/reset con eventi tramite event bus.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from config.constants import PathDefaults, ToolDefaults, HotkeyDefaults

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "pen_color": ToolDefaults.PEN_COLOR,
    "pen_size": ToolDefaults.PEN_SIZE,
    "eraser_size": ToolDefaults.ERASER_SIZE,
    "line_color": ToolDefaults.LINE_COLOR,
    "line_size": ToolDefaults.LINE_SIZE,
    "rect_color": ToolDefaults.RECT_COLOR,
    "rect_size": ToolDefaults.RECT_SIZE,
    "circle_color": ToolDefaults.CIRCLE_COLOR,
    "circle_size": ToolDefaults.CIRCLE_SIZE,
    "smooth_color": ToolDefaults.SMOOTH_COLOR,
    "smooth_size": ToolDefaults.SMOOTH_SIZE,
    "overlay_opacity": ToolDefaults.OVERLAY_OPACITY,
    "hotkey_toggle": HotkeyDefaults.TOGGLE_DRAW,
    "hotkey_visibility": HotkeyDefaults.TOGGLE_VISIBILITY,
    "hotkey_clear": HotkeyDefaults.CLEAR,
    "hotkey_undo": HotkeyDefaults.UNDO,
    "hotkey_redo": HotkeyDefaults.REDO,
    "show_control_on_start": True,
    "last_tool": "pen",
}


class Settings:
    """Gestore impostazioni utente con persistenza JSON.

    Attributes:
        _data: dizionario corrente delle impostazioni.
        _path: percorso del file di impostazioni.
        _on_change: callback opzionale invocata ad ogni modifica.
    """

    def __init__(
        self,
        on_change: Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        """Inizializza il gestore impostazioni.

        Args:
            on_change: callback opzionale (key, value) invocata su ogni set().
        """
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._path: Path = PathDefaults.SETTINGS_FILE
        self._on_change: Optional[Callable[[str, Any], None]] = on_change

    def load(self) -> None:
        """Carica le impostazioni dal disco. Se il file non esiste, usa i default."""
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as fh:
                    saved = json.load(fh)
                self._data.update(
                    {k: v for k, v in saved.items() if k in _DEFAULTS}
                )
                logger.info("Impostazioni caricate da %s", self._path)
            else:
                logger.info("Nessun file impostazioni trovato, uso i default")
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Errore caricamento impostazioni: %s", exc)

    def save(self) -> None:
        """Persiste le impostazioni correnti su disco."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            logger.debug("Impostazioni salvate in %s", self._path)
        except OSError as exc:
            logger.error("Errore salvataggio impostazioni: %s", exc)

    def get(self, key: str) -> Any:
        """Restituisce il valore di un'impostazione.

        Args:
            key: chiave dell'impostazione.

        Returns:
            Il valore corrente o il default se la chiave non esiste.
        """
        return self._data.get(key, _DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        """Imposta un valore e persiste su disco.

        Args:
            key: chiave dell'impostazione.
            value: nuovo valore.
        """
        if key not in _DEFAULTS:
            logger.warning("Chiave impostazione sconosciuta: %s", key)
            return
        old = self._data.get(key)
        self._data[key] = value
        if old != value:
            self.save()
            if self._on_change:
                self._on_change(key, value)

    def reset(self) -> None:
        """Ripristina tutte le impostazioni ai valori predefiniti."""
        self._data = dict(_DEFAULTS)
        self.save()
        logger.info("Impostazioni ripristinate ai default")

    def all(self) -> dict[str, Any]:
        """Restituisce una copia di tutte le impostazioni correnti."""
        return dict(self._data)
