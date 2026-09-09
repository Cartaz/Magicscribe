"""Test della policy di posizionamento delle finestre shell."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize

from ui.native.window_coordinator import _clamp_position_to_geometry


def test_clamp_keeps_window_inside_positive_geometry() -> None:
    geometry = QRect(0, 0, 1920, 1080)
    size = QSize(104, 700)

    assert _clamp_position_to_geometry(QPoint(-50, -20), size, geometry) == QPoint(0, 0)
    assert _clamp_position_to_geometry(QPoint(1900, 1000), size, geometry) == QPoint(1816, 380)


def test_clamp_supports_negative_monitor_coordinates() -> None:
    geometry = QRect(-1920, 0, 1920, 1080)
    size = QSize(58, 58)

    assert _clamp_position_to_geometry(QPoint(-2100, 1200), size, geometry) == QPoint(-1920, 1022)
    assert _clamp_position_to_geometry(QPoint(-300, 200), size, geometry) == QPoint(-300, 200)


def test_clamp_pins_oversized_window_to_geometry_origin() -> None:
    geometry = QRect(100, 50, 80, 60)
    size = QSize(104, 700)

    assert _clamp_position_to_geometry(QPoint(999, 999), size, geometry) == QPoint(100, 50)
