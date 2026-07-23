"""Gestore degli strumenti di disegno e loro configurazione.

Fornisce le definizioni degli strumenti disponibili, gestisce
lo strumento corrente e le configurazioni colore/dimensione.
"""

from __future__ import annotations

import logging
from dataclasses import replace

from core.models import ToolType, ToolConfig
from core.event_bus import event_bus
from config.settings import Settings

logger = logging.getLogger(__name__)


def _parse_tool_type(value: object) -> ToolType:
    """Converte un valore (stringa/ToolType) in ToolType con fallback PEN.

    Tollerante rispetto a valori salvati corrotti o non validi: in caso
    di errore restituisce ToolType.PEN e logga un warning, invece di
    propagare un'eccezione che bloccherebbe l'avvio dell'app.

    Args:
        value: valore da convertire (tipicamente una stringa letta
            dal file impostazioni).

    Returns:
        Il ToolType corrispondente, oppure ToolType.PEN se non valido.
    """
    if isinstance(value, ToolType):
        return value
    if isinstance(value, str):
        try:
            return ToolType[value.strip().upper()]
        except KeyError:
            logger.warning(
                "Strumento non riconosciuto '%s', uso PEN come fallback",
                value,
            )
    else:
        logger.warning(
            "Tipo inatteso per last_tool: %r, uso PEN come fallback",
            type(value).__name__,
        )
    return ToolType.PEN


class ToolManager:
    """Gestisce gli strumenti di disegno e le loro configurazioni.

    Attributes:
        _settings: riferimento al gestore impostazioni.
        _current_tool: strumento attualmente selezionato.
        _configs: mappa ToolType -> ToolConfig.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._current_tool: ToolType = _parse_tool_type(
            settings.get("last_tool")
        )
        self._configs: dict[ToolType, ToolConfig] = self._build_configs()

    def _build_configs(self) -> dict[ToolType, ToolConfig]:
        """Costruisce le configurazioni degli strumenti dalle impostazioni."""
        return {
            ToolType.PEN: ToolConfig(
                tool_type=ToolType.PEN,
                color=self._settings.get("pen_color"),
                size=self._settings.get("pen_size"),
            ),
            ToolType.ERASER: ToolConfig(
                tool_type=ToolType.ERASER,
                size=self._settings.get("eraser_size"),
            ),
            ToolType.LINE: ToolConfig(
                tool_type=ToolType.LINE,
                color=self._settings.get("line_color"),
                size=self._settings.get("line_size"),
            ),
            ToolType.RECT: ToolConfig(
                tool_type=ToolType.RECT,
                color=self._settings.get("rect_color"),
                size=self._settings.get("rect_size"),
            ),
            ToolType.CIRCLE: ToolConfig(
                tool_type=ToolType.CIRCLE,
                color=self._settings.get("circle_color"),
                size=self._settings.get("circle_size"),
                fill_color=None,
            ),
            ToolType.SMOOTH: ToolConfig(
                tool_type=ToolType.SMOOTH,
                color=self._settings.get("smooth_color"),
                size=self._settings.get("smooth_size"),
            ),
        }

    def current_tool(self) -> ToolType:
        """Restituisce lo strumento correntemente selezionato."""
        return self._current_tool

    def current_config(self) -> ToolConfig:
        """Restituisce la configurazione dello strumento corrente."""
        return self._configs[self._current_tool]

    def config_for(self, tool_type: ToolType) -> ToolConfig:
        """Restituisce la configurazione di uno strumento specifico.

        Args:
            tool_type: tipo di strumento.

        Returns:
            La configurazione dello strumento richiesto.
        """
        return self._configs[tool_type]

    def set_tool(self, tool_type: ToolType) -> None:
        """Seleziona uno strumento come attivo.

        Args:
            tool_type: tipo di strumento da selezionare.
        """
        if tool_type == self._current_tool:
            return
        old = self._current_tool
        self._current_tool = tool_type
        self._settings.set("last_tool", tool_type.name.lower())
        logger.info("Strumento cambiato: %s -> %s", old.name, tool_type.name)
        event_bus.emit("tool_changed", old_tool=old, new_tool=tool_type)

    def set_color(self, tool_type: ToolType, color: str) -> None:
        """Imposta il colore di uno strumento.

        La gomma (ERASER) non ha colore: la chiamata viene ignorata
        per evitare di scrivere una chiave di impostazione inesistente.

        Args:
            tool_type: tipo di strumento.
            color: colore in formato hex.
        """
        if tool_type == ToolType.ERASER:
            logger.debug("set_color ignorato per ERASER (nessun colore)")
            return
        self._configs[tool_type] = replace(
            self._configs[tool_type], color=color,
        )
        setting_key = f"{tool_type.name.lower()}_color"
        self._settings.set(setting_key, color)
        event_bus.emit("tool_config_changed", tool_type=tool_type)

    def set_size(self, tool_type: ToolType, size: float) -> None:
        """Imposta la dimensione di uno strumento.

        Args:
            tool_type: tipo di strumento.
            size: dimensione in pixel.
        """
        self._configs[tool_type] = replace(
            self._configs[tool_type], size=size,
        )
        if tool_type == ToolType.ERASER:
            self._settings.set("eraser_size", int(size))
        else:
            setting_key = f"{tool_type.name.lower()}_size"
            self._settings.set(setting_key, int(size))
        event_bus.emit("tool_config_changed", tool_type=tool_type)

    def all_tools(self) -> list[ToolType]:
        """Restituisce la lista di tutti gli strumenti disponibili."""
        return list(ToolType)
