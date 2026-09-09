"""Test per core.stroke_manager.StrokeManager."""

from core.models import Stroke, Point, ToolType
from core.stroke_manager import StrokeManager


def _make_stroke() -> Stroke:
    """Crea uno Stroke di test con un punto."""
    s = Stroke(tool_type=ToolType.PEN)
    s.points.append(Point(x=0, y=0))
    return s


def test_add_and_count() -> None:
    """add_stroke incrementa il contatore."""
    sm = StrokeManager()
    assert sm.stroke_count == 0
    sm.add_stroke(_make_stroke())
    assert sm.stroke_count == 1


def test_undo_redo_cycle() -> None:
    """Undo sposta nello stack redo, redo ripristina."""
    sm = StrokeManager()
    stroke = _make_stroke()
    sm.add_stroke(stroke)

    undone = sm.undo()
    assert undone is stroke
    assert sm.stroke_count == 0
    assert sm.can_redo

    redone = sm.redo()
    assert redone is stroke
    assert sm.stroke_count == 1
    assert not sm.can_redo


def test_undo_empty_returns_none() -> None:
    """Undo su stack vuoto restituisce None."""
    sm = StrokeManager()
    assert sm.undo() is None


def test_redo_empty_returns_none() -> None:
    """Redo su stack redo vuoto restituisce None."""
    sm = StrokeManager()
    assert sm.redo() is None


def test_add_clears_redo_stack() -> None:
    """Una nuova add_stroke invalida il redo stack."""
    sm = StrokeManager()
    sm.add_stroke(_make_stroke())
    sm.undo()
    assert sm.can_redo
    sm.add_stroke(_make_stroke())
    assert not sm.can_redo


def test_clear_all() -> None:
    """clear_all rimuove tutti i tratti e svuota il redo."""
    sm = StrokeManager()
    sm.add_stroke(_make_stroke())
    sm.add_stroke(_make_stroke())
    sm.undo()
    sm.clear_all()
    assert sm.stroke_count == 0
    assert not sm.can_undo
    assert not sm.can_redo


def test_max_depth_trims_oldest() -> None:
    """Oltre max_depth, i tratti piu' vecchi vengono scartati."""
    sm = StrokeManager(max_depth=3)
    for _ in range(5):
        sm.add_stroke(_make_stroke())
    assert sm.stroke_count == 3


def test_get_strokes_returns_copy() -> None:
    """get_strokes restituisce una copia, non la lista interna."""
    sm = StrokeManager()
    sm.add_stroke(_make_stroke())
    snapshot = sm.get_strokes()
    snapshot.clear()
    # La lista interna non deve essere modificata
    assert sm.stroke_count == 1


def test_finalize_empty_stroke_noop() -> None:
    """Aggiungere uno stroke senza punti tramite add_stroke e' permesso
    (il filtraggio avviene nel controller)."""
    sm = StrokeManager()
    empty = Stroke(tool_type=ToolType.PEN)
    sm.add_stroke(empty)
    assert sm.stroke_count == 1
