"""Regression tests for the live Smooth stroke renderer."""

from __future__ import annotations

import pytest

from core.models import Point
from ui.drawing_engine import DrawingEngine


def _elements(path):
    return [
        (path.elementAt(index).x, path.elementAt(index).y)
        for index in range(path.elementCount())
    ]


def test_smooth_path_prefix_is_stable_when_points_are_appended() -> None:
    base = [
        Point(0, 0),
        Point(10, 8),
        Point(20, -3),
        Point(30, 12),
        Point(40, 5),
        Point(50, 18),
        Point(60, 10),
        Point(70, 22),
    ]
    extended = base + [
        Point(80, 4),
        Point(90, 24),
        Point(100, 16),
    ]

    before = _elements(DrawingEngine._smooth_path(base))
    after = _elements(DrawingEngine._smooth_path(extended))

    # Quadratic segments are represented by more path elements than the raw
    # polyline. This guards against Smooth silently regressing to Pen behavior.
    assert len(before) > len(base)
    assert len(after) > len(before)

    # Extending the stroke may append geometry, but must never rewrite the
    # already consolidated body of the line.
    for old_element, new_element in zip(before, after):
        assert new_element[0] == pytest.approx(old_element[0])
        assert new_element[1] == pytest.approx(old_element[1])


def test_smooth_filter_softens_local_pointer_jitter() -> None:
    points = [
        Point(0, 0),
        Point(10, 0),
        Point(20, 12),
        Point(30, 0),
    ]

    filtered = DrawingEngine._smooth_points(points)

    # The third raw sample has y=12; the causal filter must soften that spike
    # without requiring any future samples.
    assert filtered[2].y < 12
    assert filtered[2].y > 0


def test_smooth_path_rounds_a_deliberate_corner() -> None:
    points = [
        Point(0, 0),
        Point(40, 0),
        Point(40, 40),
        Point(80, 40),
    ]

    path = DrawingEngine._smooth_path(points)

    # A polyline with four points would have exactly four path elements.
    # The extra elements prove that the corner is represented by a curve.
    assert path.elementCount() > len(points)
