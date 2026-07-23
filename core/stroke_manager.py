"""Gestore della cronologia dei tratti con undo/redo.

Mantiene due stack: uno per i tratti completati e uno
per i tratti annullati. Supporta una profondita' massima
configurabile.
"""

from __future__ import annotations

import logging
from typing import Optional

from core.models import Stroke
from core.event_bus import event_bus
from config.constants import ToolDefaults

logger = logging.getLogger(__name__)


class StrokeManager:
    """Gestisce la cronologia dei tratti con undo/redo.

    Attributes:
        _strokes: stack dei tratti completati.
        _redo_stack: stack dei tratti annullati (per redo).
        _max_depth: profondita' massima undo.
    """

    def __init__(self, max_depth: int = ToolDefaults.UNDO_MAX_DEPTH) -> None:
        self._strokes: list[Stroke] = []
        self._redo_stack: list[Stroke] = []
        self._max_depth: int = max_depth

    def add_stroke(self, stroke: Stroke) -> None:
        """Aggiunge un tratto completato alla cronologia.

        Svuota lo stack di redo (una nuova azione invalida il redo).

        Args:
            stroke: tratto completato da aggiungere.
        """
        self._strokes.append(stroke)
        self._redo_stack.clear()
        if len(self._strokes) > self._max_depth:
            self._strokes = self._strokes[-self._max_depth:]
        logger.debug("Tratto aggiunto (totale: %d)", len(self._strokes))
        event_bus.emit("strokes_changed", count=len(self._strokes))

    def undo(self) -> Optional[Stroke]:
        """Annulla l'ultimo tratto e lo sposta nello stack di redo.

        Returns:
            Il tratto annullato, oppure None se non ci sono tratti.
        """
        if not self._strokes:
            logger.debug("Undo non possibile: nessun tratto")
            return None
        stroke = self._strokes.pop()
        self._redo_stack.append(stroke)
        logger.debug(
            "Undo eseguito (rimanenti: %d, redo: %d)",
            len(self._strokes), len(self._redo_stack),
        )
        event_bus.emit("stroke_undone", stroke=stroke)
        event_bus.emit("strokes_changed", count=len(self._strokes))
        return stroke

    def redo(self) -> Optional[Stroke]:
        """Ripristina l'ultimo tratto annullato.

        Returns:
            Il tratto ripristinato, oppure None se non ci sono redo.
        """
        if not self._redo_stack:
            logger.debug("Redo non possibile: nessun tratto annullato")
            return None
        stroke = self._redo_stack.pop()
        self._strokes.append(stroke)
        logger.debug(
            "Redo eseguito (totale: %d, redo rimanenti: %d)",
            len(self._strokes), len(self._redo_stack),
        )
        event_bus.emit("stroke_redone", stroke=stroke)
        event_bus.emit("strokes_changed", count=len(self._strokes))
        return stroke

    def clear_all(self) -> None:
        """Rimuove tutti i tratti e svuota lo stack di redo."""
        count = len(self._strokes)
        self._strokes.clear()
        self._redo_stack.clear()
        logger.info("Schermo cancellato (%d tratti rimossi)", count)
        event_bus.emit("strokes_cleared")
        event_bus.emit("strokes_changed", count=0)

    def get_strokes(self) -> list[Stroke]:
        """Restituisce tutti i tratti completati (copia)."""
        return list(self._strokes)

    def get_visible_strokes(self) -> list[Stroke]:
        """Restituisce solo i tratti visibili."""
        return [s for s in self._strokes if s.visible]

    @property
    def stroke_count(self) -> int:
        """Numero di tratti nella cronologia."""
        return len(self._strokes)

    @property
    def can_undo(self) -> bool:
        """Se e' possibile annullare un tratto."""
        return len(self._strokes) > 0

    @property
    def can_redo(self) -> bool:
        """Se e' possibile ripristinare un tratto."""
        return len(self._redo_stack) > 0
