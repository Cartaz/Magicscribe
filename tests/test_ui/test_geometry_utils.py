"""Test per ui.geometry_utils."""

from core.models import Point
from ui.geometry_utils import point_line_distance, rdp_simplify


def test_point_line_distance_collinear() -> None:
    """Un punto sulla retta ha distanza zero."""
    a = Point(0, 0)
    b = Point(10, 0)
    p = Point(5, 0)
    assert point_line_distance(p, a, b) == 0.0


def test_point_line_distance_perpendicular() -> None:
    """Distanza perpendicolare corretta."""
    a = Point(0, 0)
    b = Point(10, 0)
    p = Point(5, 5)
    assert point_line_distance(p, a, b) == 5.0


def test_point_line_distance_degenerate_segment() -> None:
    """Se a == b, la distanza e' quella euclidea da a."""
    a = Point(3, 3)
    b = Point(3, 3)
    p = Point(3, 7)
    assert point_line_distance(p, a, b) == 4.0


def test_rdp_simplify_empty() -> None:
    """Lista vuota -> lista vuota."""
    assert rdp_simplify([], 1.0) == []


def test_rdp_simplify_single_point() -> None:
    """Singolo punto -> lista con quel punto."""
    pts = [Point(1, 2)]
    result = rdp_simplify(pts, 1.0)
    assert len(result) == 1
    assert result[0].x == 1 and result[0].y == 2


def test_rdp_simplify_two_points() -> None:
    """Due punti -> due punti (nessuna semplificazione)."""
    pts = [Point(0, 0), Point(10, 10)]
    result = rdp_simplify(pts, 1.0)
    assert len(result) == 2


def test_rdp_simplify_straight_line() -> None:
    """Punti collineari vengono ridotti a due estremi."""
    pts = [Point(0, 0), Point(5, 0), Point(10, 0), Point(15, 0)]
    result = rdp_simplify(pts, 0.5)
    assert len(result) == 2
    assert result[0].x == 0
    assert result[-1].x == 15


def test_rdp_simplify_preserves_deviation() -> None:
    """Punti che deviano oltre epsilon vengono mantenuti."""
    pts = [Point(0, 0), Point(5, 10), Point(10, 0)]
    result = rdp_simplify(pts, 1.0)
    assert len(result) == 3


def test_rdp_simplify_does_not_mutate_input() -> None:
    """La lista di input non deve essere modificata."""
    pts = [Point(0, 0), Point(5, 5), Point(10, 0)]
    original = list(pts)
    rdp_simplify(pts, 1.0)
    assert len(pts) == len(original)
