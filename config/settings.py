"""Gestione delle impostazioni utente persistenti.

Le impostazioni sono salvate in JSON nella directory XDG_CONFIG_HOME.
Supporta load/save/get/set/reset con validazione difensiva e fallback ai default.
Nel runtime la persistenza puo' usare un writer seriale in background, cosi'
le mutazioni provenienti dalla UI non eseguono I/O sul GUI thread.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Optional

from config.constants import PathDefaults, ToolDefaults

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
_ALLOWED_TOOLS = {"pen", "eraser", "line", "rect", "circle", "smooth"}
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def _normalize_color(value: Any) -> tuple[bool, Any]:
    """Valida i formati colore gia' supportati dal DrawingEngine."""
    if not isinstance(value, str):
        return False, value

    candidate = value.strip()
    if (
        candidate.startswith("#")
        and len(candidate) in (7, 9)
        and all(ch in _HEX_DIGITS for ch in candidate[1:])
    ):
        return True, candidate.lower()

    if candidate.startswith("rgba(") and candidate.endswith(")"):
        parts = [part.strip() for part in candidate[5:-1].split(",")]
        if len(parts) != 4:
            return False, value
        try:
            red, green, blue = (int(parts[index]) for index in range(3))
            alpha = float(parts[3])
        except (TypeError, ValueError):
            return False, value
        if not all(0 <= channel <= 255 for channel in (red, green, blue)):
            return False, value
        if not 0.0 <= alpha <= 1.0:
            return False, value
        return True, f"rgba({red},{green},{blue},{alpha:g})"

    return False, value


def _normalize_value(key: str, value: Any) -> tuple[bool, Any]:
    """Valida e normalizza un valore di configurazione senza dipendere da Qt."""
    if key in _COLOR_KEYS:
        return _normalize_color(value)

    if key in _SIZE_KEYS:
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 1 <= float(value) <= 100
        ):
            return True, int(value)
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
    """Gestore impostazioni utente con persistenza JSON."""

    def __init__(
        self,
        on_change: Optional[Callable[[str, Any], None]] = None,
        path: Path | None = None,
        *,
        background_persistence: bool = False,
    ) -> None:
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._path: Path = path if path is not None else PathDefaults.SETTINGS_FILE
        self._on_change: Optional[Callable[[str, Any], None]] = on_change
        self._writer_lock = Lock()
        self._pending_snapshot: dict[str, Any] | None = None
        self._writer_running = False
        self._closed = False
        self._executor: ThreadPoolExecutor | None = (
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="magicscribe-settings")
            if background_persistence
            else None
        )

    def load(self) -> None:
        try:
            if not self._path.exists():
                logger.info("Nessun file impostazioni trovato, uso i default")
                return
            with self._path.open("r", encoding="utf-8") as fh:
                saved = json.load(fh)
            if not isinstance(saved, dict):
                logger.warning("Configurazione ignorata: la radice JSON deve essere un oggetto")
                return
            for key, value in saved.items():
                if key not in _DEFAULTS:
                    logger.debug("Chiave impostazione obsoleta/sconosciuta: %s", key)
                    continue
                valid, normalized = _normalize_value(key, value)
                if not valid:
                    logger.warning("Valore non valido per '%s': %r; uso il default", key, value)
                    continue
                self._data[key] = normalized
            logger.info("Impostazioni caricate da %s", self._path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Errore caricamento impostazioni: %s", exc)

    def save(self) -> None:
        """Flush sincrono esplicito; il runtime non lo usa nell'event loop."""
        if self._executor is not None:
            self._queue_save()
            self.flush()
            return
        self._write_snapshot(dict(self._data))

    def flush(self) -> None:
        executor = self._executor
        if executor is None:
            return
        marker = executor.submit(lambda: None)
        marker.result()

    def close(self) -> None:
        executor = self._executor
        if executor is None:
            self._closed = True
            return
        with self._writer_lock:
            if self._closed:
                return
            self._closed = True
            self._pending_snapshot = dict(self._data)
            if not self._writer_running:
                self._writer_running = True
                executor.submit(self._drain_pending_saves)
        executor.shutdown(wait=True)
        self._executor = None

    def get(self, key: str) -> Any:
        return self._data.get(key, _DEFAULTS.get(key))

    def is_valid(self, key: str, value: Any) -> bool:
        if key not in _DEFAULTS:
            return False
        valid, _normalized = _normalize_value(key, value)
        return valid

    def set(self, key: str, value: Any) -> bool:
        if self._closed:
            logger.warning("Settings gia' chiuso: mutazione ignorata per '%s'", key)
            return False
        if key not in _DEFAULTS:
            logger.warning("Chiave impostazione sconosciuta: %s", key)
            return False
        valid, normalized = _normalize_value(key, value)
        if not valid:
            logger.warning("Valore non valido per '%s': %r", key, value)
            return False
        old = self._data.get(key)
        if old == normalized:
            return True
        self._data[key] = normalized
        self._queue_save()
        if self._on_change:
            self._on_change(key, normalized)
        return True

    def reset(self) -> None:
        if self._closed:
            logger.warning("Settings gia' chiuso: reset ignorato")
            return
        self._data = dict(_DEFAULTS)
        self._queue_save()
        logger.info("Impostazioni ripristinate ai default")

    def all(self) -> dict[str, Any]:
        return dict(self._data)

    def _queue_save(self) -> None:
        snapshot = dict(self._data)
        executor = self._executor
        if executor is None:
            self._write_snapshot(snapshot)
            return
        with self._writer_lock:
            if self._closed:
                return
            self._pending_snapshot = snapshot
            if self._writer_running:
                return
            self._writer_running = True
            executor.submit(self._drain_pending_saves)

    def _drain_pending_saves(self) -> None:
        while True:
            with self._writer_lock:
                snapshot = self._pending_snapshot
                self._pending_snapshot = None
                if snapshot is None:
                    self._writer_running = False
                    return
            self._write_snapshot(snapshot)

    def _write_snapshot(self, snapshot: dict[str, Any]) -> None:
        temp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with temp_path.open("w", encoding="utf-8") as fh:
                json.dump(snapshot, fh, indent=2, ensure_ascii=False)
            temp_path.replace(self._path)
            logger.debug("Impostazioni salvate in %s", self._path)
        except OSError as exc:
            logger.error("Errore salvataggio impostazioni: %s", exc)
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                logger.debug("Impossibile rimuovere il file temporaneo %s", temp_path)
