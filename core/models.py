"""Modelli dati centrali di MagicScribe.

Definisce le strutture dati utilizzate in tutta l'applicazione: punti, tratti,
configurazioni strumento e stato operativo minimo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class ToolType(Enum):
    """Tipi di strumenti di disegno disponibili."""
    PEN = auto()
    ERASER = auto()
    LINE = auto()
    RECT = auto()
    CIRCLE = auto()
    SMOOTH = auto()


class DrawingState(Enum):
    """Stato operativo del motore di disegno."""
    INACTIVE = auto()
    ACTIVE = auto()


@dataclass(frozen=True)
class Point:
    """Punto nello spazio dello schermo con pressione opzionale."""
    x: float
    y: float
    pressure: float = 1.0


@dataclass
class Stroke:
    """Tratto di disegno completato o in corso.

    Contiene soltanto stato attualmente configurabile e consumato dal runtime.
    Eventuali future capacità (riempimenti, frecce, ecc.) vanno introdotte con
    una feature completa, non come campi dormienti nel modello canonico.
    """
    tool_type: ToolType
    points: list[Point] = field(default_factory=list)
    color: str = "#ff0000"
    size: float = 5.0
    visible: bool = True

    def is_shape(self) -> bool:
        """Restituisce True se il tratto e' una forma geometrica."""
        return self.tool_type in (ToolType.LINE, ToolType.RECT, ToolType.CIRCLE)

    @property
    def start_point(self) -> Optional[Point]:
        """Il primo punto del tratto (per le forme geometriche)."""
        return self.points[0] if self.points else None

    @property
    def end_point(self) -> Optional[Point]:
        """L'ultimo punto del tratto (per le forme geometriche)."""
        return self.points[-1] if self.points else None


@dataclass(frozen=True)
class ToolConfig:
    """Configurazione realmente supportata da uno strumento di disegno."""
    tool_type: ToolType
    color: str = "#ff0000"
    size: float = 5.0


@dataclass
class AppState:
    """Stato globale dell'applicazione non posseduto da servizi dedicati.

    Lo strumento corrente appartiene esclusivamente a ToolManager; non viene
    duplicato qui, così ogni stato mutabile importante ha un solo proprietario.
    """
    drawing_state: DrawingState = DrawingState.INACTIVE
    annotations_visible: bool = True
