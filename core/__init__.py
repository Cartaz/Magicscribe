"""Framework-agnostic application core for MagicScribe."""

from core.app_controller import AppController
from core.models import (
    AppState,
    DrawingState,
    Point,
    Stroke,
    TOOL_SPECS,
    ToolConfig,
    ToolSpec,
    ToolType,
)
from core.stroke_manager import StrokeManager
from core.tool_manager import ToolManager

__all__ = [
    "AppController",
    "AppState",
    "DrawingState",
    "Point",
    "Stroke",
    "TOOL_SPECS",
    "ToolConfig",
    "ToolSpec",
    "ToolType",
    "StrokeManager",
    "ToolManager",
]
