"""Behavioral tests for the Wayland shell window owner."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from ui.native.window_coordinator import WindowCoordinator

_APP = QApplication.instance() or QApplication([])


def _windows() -> tuple[QQuickWindow, QQuickWindow]:
    control = QQuickWindow()
    control.setProperty("layerShellPanelX", 100.0)
    control.setProperty("layerShellPanelY", 200.0)
    floating = QQuickWindow()
    floating.setProperty("layerShellPaletteX", 371.0)
    floating.setProperty("layerShellPaletteY", 571.0)
    floating.setProperty("paletteWidth", 58.0)
    floating.setProperty("paletteHeight", 58.0)
    return control, floating


def test_minimize_and_restore_own_visibility_transition() -> None:
    control, floating = _windows()
    coordinator = WindowCoordinator()
    coordinator.set_control_window(control)
    coordinator.set_floating_window(floating)

    coordinator.show_control_panel()
    coordinator.minimize_to_floating()
    assert control.isVisible() is False
    assert floating.isVisible() is True

    coordinator.restore_control_panel()
    assert control.isVisible() is True
    assert floating.isVisible() is False

    coordinator.shutdown()
    control.deleteLater()
    floating.deleteLater()
    _APP.processEvents()


def test_restore_aligns_toolbar_logo_to_current_floating_center() -> None:
    control, floating = _windows()
    coordinator = WindowCoordinator()
    coordinator.set_control_window(control)
    coordinator.set_floating_window(floating)
    floating.show()
    _APP.processEvents()

    # Senza un QML child materializzato il fallback del logo è panel + (52, 50).
    # Il centro floating è (400, 600), quindi panel deve diventare (348, 550).
    coordinator.restore_control_panel()
    assert control.property("layerShellPanelX") == 348.0
    assert control.property("layerShellPanelY") == 550.0

    coordinator.shutdown()
    control.deleteLater()
    floating.deleteLater()
    _APP.processEvents()


def test_restore_without_visible_floating_palette_does_not_move_toolbar() -> None:
    control, floating = _windows()
    coordinator = WindowCoordinator()
    coordinator.set_control_window(control)
    coordinator.set_floating_window(floating)
    coordinator.show_control_panel()
    _APP.processEvents()

    coordinator.restore_control_panel()
    assert control.property("layerShellPanelX") == 100.0
    assert control.property("layerShellPanelY") == 200.0

    coordinator.shutdown()
    control.deleteLater()
    floating.deleteLater()
    _APP.processEvents()


def test_input_regions_are_applied_by_the_window_owner() -> None:
    control, floating = _windows()
    coordinator = WindowCoordinator()
    coordinator.set_control_window(control)
    coordinator.set_floating_window(floating)
    coordinator.set_control_input_region(10, 20, 100, 200)
    coordinator.set_floating_input_region(30, 40, 58, 58)
    _APP.processEvents()

    assert not control.mask().isEmpty()
    assert not floating.mask().isEmpty()

    coordinator.shutdown()
    control.deleteLater()
    floating.deleteLater()
    _APP.processEvents()
