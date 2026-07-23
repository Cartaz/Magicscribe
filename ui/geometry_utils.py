"""Algoritmi geometrici di utilita' per il motore di rendering.

Contiene la semplificazione Ramer-Douglas-Peucker e calcoli
di distanza, separati da drawing_engine.py per rispettare il
limite di 300 righe per file (§5.1.3).
"""

from __future__ import annotations

import math

from core.models import Point


def point_line_distance(p: Point, a: Point, b: Point) -> float:
    """Distanza perpendicolare di un punto da una retta definita da due punti.

    Args:
        p: punto di cui calcolare la distanza.
        a: primo punto che definisce la retta.
        b: secondo punto che definisce la retta.

    Returns:
        Distanza perpendicolare in pixel.
    """
    dx, dy = b.x - a.x, b.y - a.y
    norm = math.sqrt(dx * dx + dy * dy)
    if norm == 0:
        return math.sqrt((p.x - a.x) ** 2 + (p.y - a.y) ** 2)
    return abs(dy * p.x - dx * p.y + b.x * a.y - b.y * a.x) / norm


def rdp_simplify(points: list[Point], epsilon: float) -> list[Point]:
    """Semplificazione Ramer-Douglas-Peucker.

    Riduce il numero di punti mantenendo la forma approssimata
    entro una tolleranza epsilon.

    Args:
        points: sequenza di punti da semplificare.
        epsilon: tolleranza massima di deviazione in pixel.

    Returns:
        Lista semplificata di punti.
    """
    if len(points) <= 2:
        return list(points)

    dmax = 0.0
    index = 0
    end = len(points) - 1

    for i in range(1, end):
        d = point_line_distance(points[i], points[0], points[end])
        if d > dmax:
            index = i
            dmax = d

    if dmax > epsilon:
        left = rdp_simplify(points[:index + 1], epsilon)
        right = rdp_simplify(points[index:], epsilon)
        return left[:-1] + right
    return [points[0], points[end]]
