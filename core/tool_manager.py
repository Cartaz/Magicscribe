"""Accesso di dominio agli strumenti con Settings come unica source of truth."""

from __future__ import annotations

import logging

from config.settings import Settings
from core.models import TOOL_SPEC_BY_TYPE, ToolConfig, ToolType

logger = logging.getLogger(__name__)


def _parse_tool_type(value: object) -> ToolType:
    if isinstance(value, ToolType):
        return value
    if isinstance(value, str):
        try:
            return ToolType[value.strip().upper()]
        except KeyError:
            logger.warning("Strumento non riconosciuto '%s', uso PEN", value)
    else:
        logger.warning("Tipo inatteso per last_tool: %r, uso PEN", type(value).__name__)
    return ToolType.PEN


class ToolManager:
    """Boundary di dominio per Settings; non mantiene copie cached dei valori."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def current_tool(self) -> ToolType:
        return _parse_tool_type(self._settings.get("last_tool"))

    def current_config(self) -> ToolConfig:
        return self.config_for(self.current_tool())

    def config_for(self, tool_type: ToolType) -> ToolConfig:
        spec = TOOL_SPEC_BY_TYPE[tool_type]
        color = "#000000"
        if spec.color_key is not None:
            color = str(self._settings.get(spec.color_key))
        return ToolConfig(
            tool_type=tool_type,
            color=color,
            size=float(self._settings.get(spec.size_key)),
        )

    def set_tool(self, tool_type: ToolType) -> bool:
        old = self.current_tool()
        if old is tool_type:
            return False
        if not self._settings.set("last_tool", tool_type.name.lower()):
            return False
        return self.current_tool() is not old

    def set_color(self, tool_type: ToolType, color: str) -> bool:
        spec = TOOL_SPEC_BY_TYPE[tool_type]
        if spec.color_key is None:
            return False
        before = self._settings.get(spec.color_key)
        if not self._settings.set(spec.color_key, color):
            return False
        return self._settings.get(spec.color_key) != before

    def set_size(self, tool_type: ToolType, size: float) -> bool:
        spec = TOOL_SPEC_BY_TYPE[tool_type]
        before = self._settings.get(spec.size_key)
        if not self._settings.set(spec.size_key, size):
            return False
        return self._settings.get(spec.size_key) != before

    def all_tools(self) -> list[ToolType]:
        return list(ToolType)
