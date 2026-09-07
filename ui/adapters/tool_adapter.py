"""Adapter QML per selezione e configurazione degli strumenti."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.app_controller import AppController
from core.event_bus import event_bus
from core.models import ToolType

logger = logging.getLogger(__name__)


def _tool_from_id(tool_id: str) -> ToolType | None:
    if not isinstance(tool_id, str):
        return None
    try:
        return ToolType[tool_id.strip().upper()]
    except KeyError:
        return None


class ToolAdapter(QObject):
    """Espone a QML solo lo stato dello strumento attivo e le sue mutazioni."""

    currentToolChanged = Signal()
    configChanged = Signal()

    def __init__(self, controller: AppController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        event_bus.subscribe("tool_changed", self._on_tool_changed)
        event_bus.subscribe("tool_config_changed", self._on_tool_config_changed)

    def _get_current_tool(self) -> str:
        return self._controller.get_current_tool().name.lower()

    currentTool = Property(str, _get_current_tool, notify=currentToolChanged)

    def _get_current_color(self) -> str:
        return self._controller.get_current_config().color

    currentColor = Property(str, _get_current_color, notify=configChanged)

    def _get_current_size(self) -> float:
        return float(self._controller.get_current_config().size)

    currentSize = Property(float, _get_current_size, notify=configChanged)

    def _get_color_available(self) -> bool:
        return self._controller.get_current_tool() != ToolType.ERASER

    colorAvailable = Property(bool, _get_color_available, notify=currentToolChanged)

    @Slot(str, name="selectTool")
    def select_tool(self, tool_id: str) -> None:
        tool = _tool_from_id(tool_id)
        if tool is None:
            logger.warning("ToolAdapter: strumento QML non valido: %r", tool_id)
            return
        self._controller.set_tool(tool)

    @Slot(str, name="setColor")
    def set_color(self, color: str) -> None:
        tool = self._controller.get_current_tool()
        if tool == ToolType.ERASER:
            return
        self._controller.tool_manager.set_color(tool, color)

    @Slot(float, name="setSize")
    def set_size(self, size: float) -> None:
        if not 1.0 <= size <= 100.0:
            logger.warning("ToolAdapter: dimensione fuori range: %r", size)
            return
        tool = self._controller.get_current_tool()
        self._controller.tool_manager.set_size(tool, size)

    def _on_tool_changed(self, **_kwargs) -> None:
        self.currentToolChanged.emit()
        self.configChanged.emit()

    def _on_tool_config_changed(self, tool_type: ToolType, **_kwargs) -> None:
        if tool_type == self._controller.get_current_tool():
            self.configChanged.emit()
