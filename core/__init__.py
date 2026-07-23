"""Moduli core di MagicScribe.

Espone i componenti principali della logica di business.
Il livello core NON importa mai moduli Qt (§5.1.4b).
"""

from core.app_controller import AppController
from core.models import ToolType, DrawingState, AppState, Stroke, Point, ToolConfig
from core.stroke_manager import StrokeManager
from core.tool_manager import ToolManager
from core.event_bus import EventBus, event_bus
from core.exceptions import (
    MagicScribeError, ConfigError, DrawingError, StrokeError, ToolError,
)

__all__ = [
    "AppController",
    "ToolType",
    "DrawingState",
    "AppState",
    "Stroke",
    "Point",
    "ToolConfig",
    "StrokeManager",
    "ToolManager",
    "EventBus",
    "event_bus",
    "MagicScribeError",
    "ConfigError",
    "DrawingError",
    "StrokeError",
    "ToolError",
]
