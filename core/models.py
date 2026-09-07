"""Modelli dati centrali di MagicScribe.

Definisce le strutture dati usate dal dominio. Il core non dipende da Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class ToolType(Enum):
    PEN = auto()
    ERASER = auto()
    LINE = auto()
    RECT = auto()
    CIRCLE = auto()
    SMOOTH = auto()


class DrawingState(Enum):
    INACTIVE = auto()
    ACTIVE = auto()


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    pressure: float = 1.0


@dataclass
class Stroke:
    tool_type: ToolType
    points: list[Point] = field(default_factory=list)
    color: str = "#ff0000"
    size: float = 5.0
    fill_color: Optional[str] = None
    arrow_size: float = 0.0
    arrow_type: str = "end"
    visible: bool = True

    def is_shape(self) -> bool:
        return self.tool_type in (ToolType.LINE, ToolType.RECT, ToolType.CIRCLE)

    @property
    def start_point(self) -> Optional[Point]:
        return self.points[0] if self.points else None

    @property
    def end_point(self) -> Optional[Point]:
        return self.points[-1] if self.points else None


@dataclass(frozen=True)
class ToolConfig:
    tool_type: ToolType
    color: str = "#ff0000"
    size: float = 5.0
    fill_color: Optional[str] = None
    arrow_size: float = 0.0
    arrow_type: str = "end"


@dataclass
class AppState:
    """Stato globale non posseduto da servizi dedicati."""
    drawing_state: DrawingState = DrawingState.INACTIVE
    annotations_visible: bool = True
