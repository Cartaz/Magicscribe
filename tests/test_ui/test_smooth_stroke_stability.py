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

    assert len(before) == len(base)
    assert len(after) == len(extended)
    assert len(after) > len(before)

    for old_element, new_element in zip(before, after):
        assert new_element[0] == pytest.approx(old_element[0])
        assert new_element[1] == pytest.approx(old_element[1])


def test_smooth_path_filters_local_pointer_jitter() -> None:
    points = [
        Point(0, 0),
        Point(10, 0),
        Point(20, 12),
        Point(30, 0),
    ]

    elements = _elements(DrawingEngine._smooth_path(points))

    # The third raw sample has y=12; the causal three-sample filter must soften
    # that spike without requiring any future samples.
    assert elements[2][1] < 12
    assert elements[2][1] > 0
