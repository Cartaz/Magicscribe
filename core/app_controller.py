"""Controller principale dell'applicazione MagicScribe.

Orchestra i moduli core e fornisce l'interfaccia pubblica che il livello UI
utilizza per interagire con la logica applicativa. Non importa moduli Qt.
"""

from __future__ import annotations

import logging

from config.constants import ToolDefaults
from config.settings import Settings
from core.event_bus import event_bus
from core.models import AppState, DrawingState, Stroke, ToolConfig, ToolType
from core.stroke_manager import StrokeManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)


class AppController:
    """Coordina i proprietari canonici dello stato applicativo."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stroke_manager = StrokeManager(max_depth=ToolDefaults.UNDO_MAX_DEPTH)
        self._tool_manager = ToolManager(settings)
        self._state = AppState()

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def stroke_manager(self) -> StrokeManager:
        return self._stroke_manager

    @property
    def tool_manager(self) -> ToolManager:
        return self._tool_manager

    @property
    def settings(self) -> Settings:
        return self._settings

    def toggle_drawing(self) -> None:
        if self._state.drawing_state == DrawingState.INACTIVE:
            self._state.drawing_state = DrawingState.ACTIVE
            logger.info("Disegno ATTIVATO")
        else:
            self._state.drawing_state = DrawingState.INACTIVE
            logger.info("Disegno DISATTIVATO")
        event_bus.emit("drawing_toggled", active=self.is_drawing_active())

    def toggle_visibility(self) -> None:
        self._state.annotations_visible = not self._state.annotations_visible
        logger.info("Visibilita' annotazioni: %s", self._state.annotations_visible)
        event_bus.emit(
            "visibility_toggled",
            visible=self._state.annotations_visible,
        )

    def clear_screen(self) -> None:
        self._stroke_manager.clear_all()

    def undo(self) -> None:
        self._stroke_manager.undo()

    def redo(self) -> None:
        self._stroke_manager.redo()

    def is_drawing_active(self) -> bool:
        return self._state.drawing_state != DrawingState.INACTIVE

    def is_visible(self) -> bool:
        return self._state.annotations_visible

    def create_stroke(self, tool_type: ToolType) -> Stroke:
        """Crea un tratto usando soltanto la configurazione supportata."""
        config = self._tool_manager.config_for(tool_type)
        return Stroke(
            tool_type=config.tool_type,
            color=config.color,
            size=config.size,
        )

    def finalize_stroke(self, stroke: Stroke) -> None:
        if stroke.points:
            self._stroke_manager.add_stroke(stroke)

    def set_tool(self, tool_type: ToolType) -> None:
        """Seleziona uno strumento; ToolManager ne e' l'unico proprietario."""
        self._tool_manager.set_tool(tool_type)

    def get_current_tool(self) -> ToolType:
        return self._tool_manager.current_tool()

    def get_current_config(self) -> ToolConfig:
        return self._tool_manager.current_config()
