"""Modelli e specifiche di dominio centrali di MagicScribe."""

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


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Configurazione di dominio stabile condivisa da settings e tool manager."""

    tool_type: ToolType
    default_size: int
    default_color: str | None

    @property
    def key(self) -> str:
        return self.tool_type.name.lower()

    @property
    def supports_color(self) -> bool:
        return self.default_color is not None

    @property
    def size_key(self) -> str:
        return "eraser_size" if self.tool_type is ToolType.ERASER else f"{self.key}_size"

    @property
    def color_key(self) -> str | None:
        return f"{self.key}_color" if self.supports_color else None


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(ToolType.PEN, 5, "#ff0000"),
    ToolSpec(ToolType.ERASER, 40, None),
    ToolSpec(ToolType.LINE, 3, "#27ae60"),
    ToolSpec(ToolType.RECT, 3, "#ff0000"),
    ToolSpec(ToolType.CIRCLE, 3, "#ff8800"),
    ToolSpec(ToolType.SMOOTH, 5, "#ff0000"),
)
TOOL_SPEC_BY_TYPE = {spec.tool_type: spec for spec in TOOL_SPECS}


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass
class Stroke:
    """Tratto completato o in corso; contiene solo dati consumati dal runtime."""

    tool_type: ToolType
    points: list[Point] = field(default_factory=list)
    color: str = "#ff0000"
    size: float = 5.0

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


@dataclass(frozen=True)
class AppState:
    """Snapshot immutabile dello stato globale non posseduto da altri servizi."""

    drawing_state: DrawingState = DrawingState.INACTIVE
    annotations_visible: bool = True
