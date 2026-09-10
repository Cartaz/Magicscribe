"""Cronologia dei tratti con undo/redo, senza dipendenze UI."""

from __future__ import annotations

import logging
from typing import Optional

from core.models import Stroke

logger = logging.getLogger(__name__)

UNDO_MAX_DEPTH = 50


class StrokeManager:
    def __init__(self, max_depth: int = UNDO_MAX_DEPTH) -> None:
        self._strokes: list[Stroke] = []
        self._redo_stack: list[Stroke] = []
        self._max_depth = max_depth

    def add_stroke(self, stroke: Stroke) -> None:
        self._strokes.append(stroke)
        self._redo_stack.clear()
        if len(self._strokes) > self._max_depth:
            self._strokes = self._strokes[-self._max_depth:]
        logger.debug("Tratto aggiunto (totale: %d)", len(self._strokes))

    def undo(self) -> Optional[Stroke]:
        if not self._strokes:
            return None
        stroke = self._strokes.pop()
        self._redo_stack.append(stroke)
        return stroke

    def redo(self) -> Optional[Stroke]:
        if not self._redo_stack:
            return None
        stroke = self._redo_stack.pop()
        self._strokes.append(stroke)
        return stroke

    def clear_all(self) -> bool:
        changed = bool(self._strokes or self._redo_stack)
        self._strokes.clear()
        self._redo_stack.clear()
        return changed

    def get_strokes(self) -> list[Stroke]:
        return list(self._strokes)

    @property
    def stroke_count(self) -> int:
        return len(self._strokes)

    @property
    def can_undo(self) -> bool:
        return bool(self._strokes)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)
