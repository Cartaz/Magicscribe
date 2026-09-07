"""Modelli dati centrali di MagicScribe.

Definisce le strutture dati immutabili utilizzate in tutto
l'applicazione: punti, tratti, configurazioni strumento.
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
    INACTIVE = auto()    # Disegno disattivato
    ACTIVE = auto()      # Disegno attivo, pronto per disegnare


@dataclass(frozen=True)
class Point:
    """Punto nello spazio dello schermo con pressione opzionale.

    Attributes:
        x: coordinata orizzontale in pixel.
        y: coordinata verticale in pixel.
        pressure: pressione del dispositivo (0.0-1.0), default 1.0.
    """
    x: float
    y: float
    pressure: float = 1.0


@dataclass
class Stroke:
    """Tratto di disegno completato o in corso.

    Attributes:
        tool_type: tipo di strumento usato.
        points: sequenza di punti del tratto.
        color: colore in formato hex o rgba.
        size: spessore della linea in pixel.
        fill_color: colore di riempimento (per cerchi/rettangoli).
        arrow_size: dimensione della freccia (0 = nessuna freccia).
        arrow_type: tipo di freccia ('start', 'end', 'double').
        visible: se il tratto e' visibile.
    """
    tool_type: ToolType
    points: list[Point] = field(default_factory=list)
    color: str = "#ff0000"
    size: float = 5.0
    fill_color: Optional[str] = None
    arrow_size: float = 0.0
    arrow_type: str = "end"
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
    """Configurazione di uno strumento di disegno.

    Attributes:
        tool_type: tipo di strumento.
        color: colore della linea.
        size: spessore della linea.
        fill_color: colore di riempimento opzionale.
        arrow_size: dimensione freccia.
        arrow_type: tipo di freccia.
    """
    tool_type: ToolType
    color: str = "#ff0000"
    size: float = 5.0
    fill_color: Optional[str] = None
    arrow_size: float = 0.0
    arrow_type: str = "end"


@dataclass
class AppState:
    """Stato globale dell'applicazione non posseduto da servizi dedicati.

    Lo strumento corrente appartiene esclusivamente a ToolManager; non viene
    duplicato qui, così ogni stato mutabile importante ha un solo proprietario.
    """
    drawing_state: DrawingState = DrawingState.INACTIVE
    annotations_visible: bool = True
