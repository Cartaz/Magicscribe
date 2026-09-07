"""Algoritmi geometrici puri usati dal renderer."""

from __future__ import annotations

import math

from core.models import Point


def point_line_distance(p: Point, a: Point, b: Point) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    norm = math.sqrt(dx * dx + dy * dy)
    if norm == 0:
        return math.sqrt((p.x - a.x) ** 2 + (p.y - a.y) ** 2)
    return abs(dy * p.x - dx * p.y + b.x * a.y - b.y * a.x) / norm


def rdp_simplify(points: list[Point], epsilon: float) -> list[Point]:
    if len(points) <= 2:
        return list(points)
    dmax = 0.0
    index = 0
    end = len(points) - 1
    for i in range(1, end):
        distance = point_line_distance(points[i], points[0], points[end])
        if distance > dmax:
            index = i
            dmax = distance
    if dmax > epsilon:
        left = rdp_simplify(points[:index + 1], epsilon)
        right = rdp_simplify(points[index:], epsilon)
        return left[:-1] + right
    return [points[0], points[end]]
