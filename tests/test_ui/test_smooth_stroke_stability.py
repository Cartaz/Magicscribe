"""Regression tests for the live Smooth stroke renderer."""

from __future__ import annotations

import math

import pytest

from core.models import Point
from ui.drawing_engine import DrawingEngine


def _elements(path):
    return [
        (path.elementAt(index).x, path.elementAt(index).y)
        for index in range(path.elementCount())
    ]


def _dense_polyline(vertices: list[Point], step: float = 2.0) -> list[Point]:
    points: list[Point] = []
    for start, end in zip(vertices, vertices[1:]):
        distance = math.hypot(end.x - start.x, end.y - start.y)
        count = max(1, int(distance / step))
        for index in range(count):
            t = index / count
            points.append(
                Point(
                    start.x + (end.x - start.x) * t,
                    start.y + (end.y - start.y) * t,
                )
            )
    points.append(vertices[-1])
    return points


def test_smooth_path_prefix_is_stable_when_points_are_appended() -> None:
    vertices = [
        Point(0, 0),
        Point(80, 50),
        Point(160, 5),
        Point(240, 70),
        Point(320, 15),
        Point(400, 65),
    ]
    base = _dense_polyline(vertices[:4])
    extended = base[:-1] + _dense_polyline(vertices[3:])

    before = _elements(DrawingEngine._smooth_path(base))
    after = _elements(DrawingEngine._smooth_path(extended))

    assert before
    assert len(after) > len(before)

    # Extending the dense mouse stream may append geometry, but must never
    # rewrite the already consolidated body of the line.
    for old_element, new_element in zip(before, after):
        assert new_element[0] == pytest.approx(old_element[0])
        assert new_element[1] == pytest.approx(old_element[1])


def test_smooth_spatial_resampling_collapses_dense_mouse_events() -> None:
    points = _dense_polyline([Point(0, 0), Point(320, 0)], step=1.0)

    controls = DrawingEngine._resample_smooth_controls(points)

    # Hundreds of raw mouse events must become a small, distance-based control
    # set. Otherwise a spline simply hugs the original Pen polyline.
    assert len(points) > 300
    assert 8 <= len(controls) <= 12


def test_smooth_filter_softens_spatial_pointer_turns() -> None:
    points = _dense_polyline(
        [Point(0, 0), Point(80, 0), Point(120, 80), Point(200, 0)],
        step=2.0,
    )

    sampled = DrawingEngine._resample_smooth_controls(points)
    filtered = DrawingEngine._smooth_points(points)

    assert len(filtered) == len(sampled)
    assert len(filtered) >= 4
    # Low-pass control points must not be identical to the raw spatial samples.
    assert any(
        abs(raw.x - smooth.x) > 1.0 or abs(raw.y - smooth.y) > 1.0
        for raw, smooth in zip(sampled[1:], filtered[1:])
    )


def test_smooth_path_rounds_a_deliberate_corner() -> None:
    points = _dense_polyline(
        [Point(0, 0), Point(120, 0), Point(120, 120), Point(240, 120)],
        step=2.0,
    )

    path = DrawingEngine._smooth_path(points)

    # The rendered path must use cubic curve elements, not a raw polyline.
    assert path.elementCount() > 4


def test_dense_mouse_zigzag_becomes_visibly_sinuous() -> None:
    vertices = [
        Point(0, 0),
        Point(100, 80),
        Point(200, 0),
        Point(300, 80),
        Point(400, 0),
        Point(500, 80),
        Point(600, 0),
    ]
    points = _dense_polyline(vertices, step=2.0)

    path = DrawingEngine._smooth_path(points)
    bounds = path.boundingRect()
    controls = DrawingEngine._smooth_points(points)

    # Real mouse input is dense. Smooth must still cut a meaningful amount from
    # the 80 px raw zig-zag amplitude instead of becoming visually identical to
    # Pen. The spatial controls also need to remain far fewer than raw events.
    assert len(points) > 300
    assert len(controls) < len(points) / 8
    assert bounds.height() < 60
    assert bounds.height() > 20
