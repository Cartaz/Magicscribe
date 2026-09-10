"""Test della policy di posizionamento delle finestre shell."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize

import ui.native.window_coordinator as window_coordinator_module
from ui.native.window_coordinator import WindowCoordinator, _clamp_position_to_geometry


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


def test_native_wayland_delegates_top_level_positioning_to_compositor(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        window_coordinator_module,
        "_platform_name",
        lambda: "wayland",
    )
    assert window_coordinator_module._supports_absolute_top_level_positioning() is False


def test_xcb_keeps_absolute_top_level_positioning(monkeypatch) -> None:
    monkeypatch.setattr(
        window_coordinator_module,
        "_platform_name",
        lambda: "xcb",
    )
    assert window_coordinator_module._supports_absolute_top_level_positioning() is True


def test_native_wayland_does_not_fight_layer_shell_z_order(monkeypatch) -> None:
    monkeypatch.setattr(
        window_coordinator_module,
        "_platform_name",
        lambda: "wayland",
    )
    coordinator = WindowCoordinator()

    class _VisibleWindow:
        def isVisible(self) -> bool:
            return True

        def raise_(self) -> None:
            raise AssertionError("raise_ must not be used for a layer-surface")

        def requestActivate(self) -> None:
            raise AssertionError("requestActivate must not be used for layer stacking")

    coordinator._control_window = _VisibleWindow()
    coordinator._floating_window = _VisibleWindow()
    coordinator.ensure_z_order()
