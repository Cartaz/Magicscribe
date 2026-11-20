"""Cronologia dei tratti con undo/redo, senza dipendenze UI."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from core.models import Stroke

logger = logging.getLogger(__name__)

UNDO_MAX_DEPTH = 50


@dataclass(frozen=True, slots=True)
class _AddStroke:
    stroke: Stroke


@dataclass(frozen=True, slots=True)
class _ClearAll:
    cleared: tuple[Stroke, ...]


_Operation = _AddStroke | _ClearAll


class StrokeManager:
    """Possiede i tratti visibili e una cronologia di operazioni annullabili.

    ``max_depth`` limita solo quante operazioni si possono annullare: i tratti
    piu' vecchi della finestra di undo restano visibili, semplicemente non sono
    piu' annullabili.
    """

    def __init__(self, max_depth: int = UNDO_MAX_DEPTH) -> None:
        self._strokes: list[Stroke] = []
        self._undo_stack: list[_Operation] = []
        self._redo_stack: list[_Operation] = []
        self._max_depth = max_depth

    def add_stroke(self, stroke: Stroke) -> None:
        self._strokes.append(stroke)
        self._record(_AddStroke(stroke))
        logger.debug("Tratto aggiunto (totale: %d)", len(self._strokes))

    def clear_all(self) -> bool:
        """Rimuove tutti i tratti visibili come singola operazione annullabile."""
        if not self._strokes:
            return False
        self._record(_ClearAll(tuple(self._strokes)))
        self._strokes = []
        return True

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        operation = self._undo_stack.pop()
        if isinstance(operation, _AddStroke):
            self._strokes.pop()
        else:
            self._strokes = list(operation.cleared)
        self._redo_stack.append(operation)
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        operation = self._redo_stack.pop()
        if isinstance(operation, _AddStroke):
            self._strokes.append(operation.stroke)
        else:
            self._strokes = []
        self._undo_stack.append(operation)
        return True

    def get_strokes(self) -> list[Stroke]:
        return list(self._strokes)

    @property
    def stroke_count(self) -> int:
        return len(self._strokes)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def _record(self, operation: _Operation) -> None:
        self._undo_stack.append(operation)
        self._redo_stack.clear()
        if len(self._undo_stack) > self._max_depth:
            del self._undo_stack[: len(self._undo_stack) - self._max_depth]
