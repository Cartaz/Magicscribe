"""Controller applicativo: unico boundary mutabile esposto alla UI."""

from __future__ import annotations

from dataclasses import replace
import logging
from typing import Callable

from config.settings import Settings
from core.models import AppState, DrawingState, Stroke, ToolConfig, ToolType
from core.stroke_manager import StrokeManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)
Listener = Callable[[], None]


class AppController:
    """Possiede stato e workflow applicativi; il core non importa Qt."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._strokes = StrokeManager()
        self._tools = ToolManager(settings)
        self._state = AppState()
        self._drawing_listeners: list[Listener] = []
        self._visibility_listeners: list[Listener] = []
        self._history_listeners: list[Listener] = []
        self._tool_listeners: list[Listener] = []
        self._tool_config_listeners: list[Listener] = []

    @property
    def state(self) -> AppState:
        """Snapshot immutabile dello stato applicativo."""
        return self._state

    @staticmethod
    def _subscribe(bucket: list[Listener], listener: Listener) -> None:
        if listener not in bucket:
            bucket.append(listener)

    @staticmethod
    def _unsubscribe(bucket: list[Listener], listener: Listener) -> None:
        if listener in bucket:
            bucket.remove(listener)

    @staticmethod
    def _notify(bucket: list[Listener]) -> None:
        for listener in tuple(bucket):
            try:
                listener()
            except Exception:
                logger.exception("Listener applicativo fallito: %r", listener)

    def add_drawing_listener(self, listener: Listener) -> None:
        self._subscribe(self._drawing_listeners, listener)

    def remove_drawing_listener(self, listener: Listener) -> None:
        self._unsubscribe(self._drawing_listeners, listener)

    def add_visibility_listener(self, listener: Listener) -> None:
        self._subscribe(self._visibility_listeners, listener)

    def remove_visibility_listener(self, listener: Listener) -> None:
        self._unsubscribe(self._visibility_listeners, listener)

    def add_history_listener(self, listener: Listener) -> None:
        self._subscribe(self._history_listeners, listener)

    def remove_history_listener(self, listener: Listener) -> None:
        self._unsubscribe(self._history_listeners, listener)

    def add_tool_listener(self, listener: Listener) -> None:
        self._subscribe(self._tool_listeners, listener)

    def remove_tool_listener(self, listener: Listener) -> None:
        self._unsubscribe(self._tool_listeners, listener)

    def add_tool_config_listener(self, listener: Listener) -> None:
        self._subscribe(self._tool_config_listeners, listener)

    def remove_tool_config_listener(self, listener: Listener) -> None:
        self._unsubscribe(self._tool_config_listeners, listener)

    def toggle_drawing(self) -> None:
        next_state = (
            DrawingState.ACTIVE
            if self._state.drawing_state is DrawingState.INACTIVE
            else DrawingState.INACTIVE
        )
        self._state = replace(self._state, drawing_state=next_state)
        self._notify(self._drawing_listeners)

    def toggle_visibility(self) -> None:
        self._state = replace(
            self._state,
            annotations_visible=not self._state.annotations_visible,
        )
        self._notify(self._visibility_listeners)

    def clear_screen(self) -> None:
        if self._strokes.clear_all():
            self._notify(self._history_listeners)

    def undo(self) -> None:
        if self._strokes.undo() is not None:
            self._notify(self._history_listeners)

    def redo(self) -> None:
        if self._strokes.redo() is not None:
            self._notify(self._history_listeners)

    def is_drawing_active(self) -> bool:
        return self._state.drawing_state is DrawingState.ACTIVE

    def is_visible(self) -> bool:
        return self._state.annotations_visible

    def can_undo(self) -> bool:
        return self._strokes.can_undo

    def can_redo(self) -> bool:
        return self._strokes.can_redo

    def stroke_count(self) -> int:
        return self._strokes.stroke_count

    def strokes_snapshot(self) -> list[Stroke]:
        return self._strokes.get_strokes()

    def create_stroke(self, tool_type: ToolType) -> Stroke:
        config = self._tools.config_for(tool_type)
        return Stroke(
            tool_type=config.tool_type,
            color=config.color,
            size=config.size,
        )

    def finalize_stroke(self, stroke: Stroke) -> None:
        if not stroke.points:
            return
        self._strokes.add_stroke(stroke)
        self._notify(self._history_listeners)

    def set_tool(self, tool_type: ToolType) -> None:
        if self._tools.set_tool(tool_type):
            self._notify(self._tool_listeners)
            self._notify(self._tool_config_listeners)

    def set_tool_color(self, color: str) -> None:
        if self._tools.set_color(self.get_current_tool(), color):
            self._notify(self._tool_config_listeners)

    def set_tool_size(self, size: float) -> None:
        if self._tools.set_size(self.get_current_tool(), size):
            self._notify(self._tool_config_listeners)

    def get_current_tool(self) -> ToolType:
        return self._tools.current_tool()

    def get_current_config(self) -> ToolConfig:
        return self._tools.current_config()
