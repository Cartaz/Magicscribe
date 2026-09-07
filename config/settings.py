"""Gestione delle impostazioni utente persistenti.

Le impostazioni sono salvate in JSON nella directory XDG_CONFIG_HOME.
Supporta load/save/get/set/reset con validazione difensiva e fallback ai default.
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

_COLOR_KEYS = {
    "pen_color", "line_color", "rect_color", "circle_color", "smooth_color",
}
_SIZE_KEYS = {
    "pen_size", "eraser_size", "line_size", "rect_size", "circle_size",
    "smooth_size",
}
_HOTKEY_KEYS = {
    "hotkey_toggle", "hotkey_visibility", "hotkey_clear", "hotkey_undo",
    "hotkey_redo",
}
_ALLOWED_TOOLS = {"pen", "eraser", "line", "rect", "circle", "smooth"}


def _normalize_value(key: str, value: Any) -> tuple[bool, Any]:
    """Valida e normalizza un valore di configurazione senza dipendere da Qt."""
    if key in _COLOR_KEYS:
        if (
            isinstance(value, str)
            and len(value) == 7
            and value.startswith("#")
            and all(ch in "0123456789abcdefABCDEF" for ch in value[1:])
        ):
            return True, value.lower()
        return False, value

    if key in _SIZE_KEYS:
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 1 <= float(value) <= 100
        ):
            return True, int(value)
        return False, value

    if key == "overlay_opacity":
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 0.0 <= float(value) <= 1.0
        ):
            return True, float(value)
        return False, value

    if key in _HOTKEY_KEYS:
        if isinstance(value, str) and value.strip():
            return True, value.strip()
        return False, value

    if key == "show_control_on_start":
        return (True, value) if isinstance(value, bool) else (False, value)

    if key == "last_tool":
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in _ALLOWED_TOOLS:
                return True, normalized
        return False, value

    return False, value


class Settings:
    """Gestore impostazioni utente con persistenza JSON.

    Il percorso e' iniettabile per mantenere test e client indipendenti dal
    filesystem reale dell'utente. Valori sconosciuti o malformati vengono
    ignorati e sostituiti implicitamente dai default in codice.
    """

    def __init__(
        self,
        on_change: Optional[Callable[[str, Any], None]] = None,
        path: Path | None = None,
    ) -> None:
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._path: Path = path if path is not None else PathDefaults.SETTINGS_FILE
        self._on_change: Optional[Callable[[str, Any], None]] = on_change

    def load(self) -> None:
        """Carica le impostazioni; configurazioni malformate non bloccano l'avvio."""
        try:
            if not self._path.exists():
                logger.info("Nessun file impostazioni trovato, uso i default")
                return

            with self._path.open("r", encoding="utf-8") as fh:
                saved = json.load(fh)

            if not isinstance(saved, dict):
                logger.warning(
                    "Configurazione ignorata: la radice JSON deve essere un oggetto"
                )
                return

            for key, value in saved.items():
                if key not in _DEFAULTS:
                    logger.debug("Chiave impostazione obsoleta/sconosciuta: %s", key)
                    continue
                valid, normalized = _normalize_value(key, value)
                if not valid:
                    logger.warning(
                        "Valore non valido per '%s': %r; uso il default",
                        key,
                        value,
                    )
                    continue
                self._data[key] = normalized

            logger.info("Impostazioni caricate da %s", self._path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Errore caricamento impostazioni: %s", exc)

    def save(self) -> None:
        """Persiste le impostazioni correnti con sostituzione atomica del file."""
        temp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with temp_path.open("w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            temp_path.replace(self._path)
            logger.debug("Impostazioni salvate in %s", self._path)
        except OSError as exc:
            logger.error("Errore salvataggio impostazioni: %s", exc)
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                logger.debug("Impossibile rimuovere il file temporaneo %s", temp_path)

    def get(self, key: str) -> Any:
        """Restituisce il valore corrente o il default della chiave."""
        return self._data.get(key, _DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        """Valida, imposta e persiste una singola impostazione."""
        if key not in _DEFAULTS:
            logger.warning("Chiave impostazione sconosciuta: %s", key)
            return

        valid, normalized = _normalize_value(key, value)
        if not valid:
            logger.warning("Valore non valido per '%s': %r", key, value)
            return

        old = self._data.get(key)
        self._data[key] = normalized
        if old != normalized:
            self.save()
            if self._on_change:
                self._on_change(key, normalized)

    def reset(self) -> None:
        """Ripristina tutte le impostazioni ai valori predefiniti."""
        self._data = dict(_DEFAULTS)
        self.save()
        logger.info("Impostazioni ripristinate ai default")

    def all(self) -> dict[str, Any]:
        """Restituisce una copia di tutte le impostazioni correnti."""
        return dict(self._data)
