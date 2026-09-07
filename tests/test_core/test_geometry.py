from core.geometry import point_line_distance, rdp_simplify
from core.models import Point


def test_distance_and_degenerate_segment():
    assert point_line_distance(Point(5, 5), Point(0, 0), Point(10, 0)) == 5.0
    assert point_line_distance(Point(3, 7), Point(3, 3), Point(3, 3)) == 4.0


def test_rdp_edge_cases_and_straight_line():
    assert rdp_simplify([], 1.0) == []
    points = [Point(0, 0), Point(5, 0), Point(10, 0)]
    assert rdp_simplify(points, 0.5) == [points[0], points[-1]]


def test_rdp_preserves_deviation_without_mutating_input():
    points = [Point(0, 0), Point(5, 10), Point(10, 0)]
    original = list(points)
    assert len(rdp_simplify(points, 1.0)) == 3
    assert points == original
