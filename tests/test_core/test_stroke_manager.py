"""Test per core.stroke_manager.StrokeManager."""

from core.models import Point, Stroke, ToolType
from core.stroke_manager import UNDO_MAX_DEPTH, StrokeManager


def _make_stroke(x: float = 0) -> Stroke:
    return Stroke(tool_type=ToolType.PEN, points=[Point(x=x, y=0)])


def test_add_and_count() -> None:
    sm = StrokeManager()
    assert sm.stroke_count == 0
    sm.add_stroke(_make_stroke())
    assert sm.stroke_count == 1


def test_undo_redo_cycle() -> None:
    sm = StrokeManager()
    stroke = _make_stroke()
    sm.add_stroke(stroke)

    assert sm.undo() is True
    assert sm.stroke_count == 0
    assert sm.can_redo

    assert sm.redo() is True
    assert sm.get_strokes() == [stroke]
    assert not sm.can_redo


def test_undo_and_redo_on_empty_history_are_noops() -> None:
    sm = StrokeManager()
    assert sm.undo() is False
    assert sm.redo() is False


def test_add_clears_redo_stack() -> None:
    sm = StrokeManager()
    sm.add_stroke(_make_stroke())
    sm.undo()
    assert sm.can_redo
    sm.add_stroke(_make_stroke())
    assert not sm.can_redo


def test_clear_all_is_undoable_and_redoable() -> None:
    sm = StrokeManager()
    first, second = _make_stroke(1), _make_stroke(2)
    sm.add_stroke(first)
    sm.add_stroke(second)

    assert sm.clear_all() is True
    assert sm.stroke_count == 0

    assert sm.undo() is True
    assert sm.get_strokes() == [first, second]

    assert sm.redo() is True
    assert sm.stroke_count == 0

    # Dopo aver annullato il clear, undo prosegue sui singoli tratti.
    sm.undo()
    sm.undo()
    assert sm.get_strokes() == [first]


def test_clear_all_without_strokes_records_nothing() -> None:
    sm = StrokeManager()
    assert sm.clear_all() is False
    assert not sm.can_undo


def test_undo_depth_never_hides_visible_strokes() -> None:
    sm = StrokeManager(max_depth=3)
    strokes = [_make_stroke(index) for index in range(5)]
    for stroke in strokes:
        sm.add_stroke(stroke)

    assert sm.get_strokes() == strokes

    undone = 0
    while sm.undo():
        undone += 1
    assert undone == 3
    assert sm.get_strokes() == strokes[:2]


def test_default_depth_keeps_more_than_fifty_strokes_visible() -> None:
    sm = StrokeManager()
    first = _make_stroke(-1)
    sm.add_stroke(first)
    for index in range(UNDO_MAX_DEPTH + 10):
        sm.add_stroke(_make_stroke(index))
    assert sm.stroke_count == UNDO_MAX_DEPTH + 11
    assert sm.get_strokes()[0] is first


def test_get_strokes_returns_copy() -> None:
    sm = StrokeManager()
    sm.add_stroke(_make_stroke())
    snapshot = sm.get_strokes()
    snapshot.clear()
    assert sm.stroke_count == 1
