"""Adapter QML per selezione e configurazione degli strumenti."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.app_controller import AppController
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
    currentToolChanged = Signal()
    configChanged = Signal()

    def __init__(self, controller: AppController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._closed = False
        controller.add_tool_listener(self._on_tool_changed)
        controller.add_tool_config_listener(self._on_tool_config_changed)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._controller.remove_tool_listener(self._on_tool_changed)
        self._controller.remove_tool_config_listener(self._on_tool_config_changed)

    currentTool = Property(
        str,
        lambda self: self._controller.get_current_tool().name.lower(),
        notify=currentToolChanged,
    )
    currentColor = Property(
        str,
        lambda self: self._controller.get_current_config().color,
        notify=configChanged,
    )
    currentSize = Property(
        float,
        lambda self: float(self._controller.get_current_config().size),
        notify=configChanged,
    )
    colorAvailable = Property(
        bool,
        lambda self: self._controller.get_current_tool() is not ToolType.ERASER,
        notify=currentToolChanged,
    )

    @Slot(str)
    def select_tool(self, tool_id: str) -> None:
        tool = _tool_from_id(tool_id)
        if tool is None:
            logger.warning("ToolAdapter: strumento QML non valido: %r", tool_id)
            return
        self._controller.set_tool(tool)

    @Slot(str)
    def set_color(self, color: str) -> None:
        self._controller.set_tool_color(color)

    @Slot(float)
    def set_size(self, size: float) -> None:
        self._controller.set_tool_size(size)

    def _on_tool_changed(self) -> None:
        self.currentToolChanged.emit()

    def _on_tool_config_changed(self) -> None:
        self.configChanged.emit()
