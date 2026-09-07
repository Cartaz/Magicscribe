"""Gestore degli strumenti di disegno e delle loro configurazioni."""

from __future__ import annotations

import logging
from dataclasses import replace

from config.settings import Settings
from core.event_bus import event_bus
from core.models import ToolConfig, ToolType

logger = logging.getLogger(__name__)


def _parse_tool_type(value: object) -> ToolType:
    if isinstance(value, ToolType):
        return value
    if isinstance(value, str):
        try:
            return ToolType[value.strip().upper()]
        except KeyError:
            logger.warning("Strumento non riconosciuto '%s', uso PEN come fallback", value)
    else:
        logger.warning("Tipo inatteso per last_tool: %r, uso PEN come fallback", type(value).__name__)
    return ToolType.PEN


class ToolManager:
    """Possiede lo strumento corrente e le configurazioni canoniche."""
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._current_tool: ToolType = _parse_tool_type(settings.get("last_tool"))
        self._configs: dict[ToolType, ToolConfig] = self._build_configs()

    def _build_configs(self) -> dict[ToolType, ToolConfig]:
        return {
            ToolType.PEN: ToolConfig(ToolType.PEN, self._settings.get("pen_color"), self._settings.get("pen_size")),
            ToolType.ERASER: ToolConfig(ToolType.ERASER, size=self._settings.get("eraser_size")),
            ToolType.LINE: ToolConfig(ToolType.LINE, self._settings.get("line_color"), self._settings.get("line_size")),
            ToolType.RECT: ToolConfig(ToolType.RECT, self._settings.get("rect_color"), self._settings.get("rect_size")),
            ToolType.CIRCLE: ToolConfig(ToolType.CIRCLE, self._settings.get("circle_color"), self._settings.get("circle_size"), fill_color=None),
            ToolType.SMOOTH: ToolConfig(ToolType.SMOOTH, self._settings.get("smooth_color"), self._settings.get("smooth_size")),
        }

    def current_tool(self) -> ToolType:
        return self._current_tool

    def current_config(self) -> ToolConfig:
        return self._configs[self._current_tool]

    def config_for(self, tool_type: ToolType) -> ToolConfig:
        return self._configs[tool_type]

    def set_tool(self, tool_type: ToolType) -> None:
        if tool_type == self._current_tool:
            return
        if not self._settings.set("last_tool", tool_type.name.lower()):
            logger.warning("Cambio strumento rifiutato: %s", tool_type.name)
            return
        old = self._current_tool
        self._current_tool = tool_type
        logger.info("Strumento cambiato: %s -> %s", old.name, tool_type.name)
        event_bus.emit("tool_changed", old_tool=old, new_tool=tool_type)

    def set_color(self, tool_type: ToolType, color: str) -> None:
        if tool_type == ToolType.ERASER:
            return
        setting_key = f"{tool_type.name.lower()}_color"
        if not self._settings.set(setting_key, color):
            logger.warning("Colore rifiutato per %s: %r", tool_type.name, color)
            return
        normalized = self._settings.get(setting_key)
        if self._configs[tool_type].color == normalized:
            return
        self._configs[tool_type] = replace(self._configs[tool_type], color=normalized)
        event_bus.emit("tool_config_changed", tool_type=tool_type)

    def set_size(self, tool_type: ToolType, size: float) -> None:
        setting_key = "eraser_size" if tool_type == ToolType.ERASER else f"{tool_type.name.lower()}_size"
        if not self._settings.set(setting_key, size):
            logger.warning("Dimensione rifiutata per %s: %r", tool_type.name, size)
            return
        normalized = float(self._settings.get(setting_key))
        if float(self._configs[tool_type].size) == normalized:
            return
        self._configs[tool_type] = replace(self._configs[tool_type], size=normalized)
        event_bus.emit("tool_config_changed", tool_type=tool_type)

    def all_tools(self) -> list[ToolType]:
        return list(ToolType)
