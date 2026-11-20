"""Offscreen checks for draggable shell hosts and their input regions."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QWindow
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from core.app_controller import AppController
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.shell_adapter import ShellAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.models.tool_list_model import ToolListModel
from ui.native.window_coordinator import WindowCoordinator

_APP = QApplication.instance() or QApplication([])
_QML_ROOT = Path(__file__).resolve().parents[2] / "ui" / "qml"


@pytest.fixture
def shell(tmp_path):
    settings = Settings(path=tmp_path / "regions.json")
    controller = AppController(settings)
    drawing_adapter = DrawingAdapter(controller)
    tool_adapter = ToolAdapter(controller)
    tool_model = ToolListModel()
    coordinator = WindowCoordinator()
    shell_adapter = ShellAdapter(coordinator)

    engine = QQmlApplicationEngine()
    qml_warnings: list[str] = []
    engine.warnings.connect(
        lambda errors: qml_warnings.extend(error.toString() for error in errors)
    )
    engine.addImportPath(str(_QML_ROOT))
    engine.setInitialProperties(
        {
            "drawingAdapter": drawing_adapter,
            "toolAdapter": tool_adapter,
            "shellAdapter": shell_adapter,
            "toolModel": tool_model,
        }
    )
    engine.loadFromModule("MagicScribe", "ControlPanel")
    control = engine.rootObjects()[0]
    floating_component = QQmlComponent(engine)
    floating_component.loadFromModule("MagicScribe", "FloatingPalette")
    floating = floating_component.createWithInitialProperties(
        {"drawingAdapter": drawing_adapter, "shellAdapter": shell_adapter}
    )
    assert isinstance(control, QWindow) and isinstance(floating, QWindow)
    coordinator.set_control_window(control)
    coordinator.set_floating_window(floating)
    control.resize(800, 900)
    floating.resize(800, 900)
    coordinator.show_control_panel()
    _settle()
    try:
        yield coordinator, control, floating
        _settle()
        assert qml_warnings == []
    finally:
        coordinator.shutdown()
        floating.deleteLater()
        floating_component.deleteLater()
        engine.deleteLater()
        drawing_adapter.close()
        tool_adapter.close()
        settings.close()
        _settle()


def _settle() -> None:
    for _ in range(3):
        _APP.processEvents()


def _host_rect(window: QWindow, host_name: str) -> QRect:
    host = window.findChild(QQuickItem, host_name)
    assert host is not None, host_name
    return QRect(round(host.x()), round(host.y()), round(host.width()), round(host.height()))


def test_control_mask_follows_toolbar_host(shell) -> None:
    _coordinator, control, _floating = shell
    host = _host_rect(control, "toolbarHost")
    assert host.topLeft() == QPoint(20, 20)
    assert control.mask().boundingRect() == host

    control.setProperty("layerShellPanelX", 300.0)
    _settle()
    assert control.mask().boundingRect() == _host_rect(control, "toolbarHost")
    assert _host_rect(control, "toolbarHost").x() == 300


def test_control_host_is_clamped_when_surface_shrinks(shell) -> None:
    _coordinator, control, _floating = shell
    control.setProperty("layerShellPanelX", 600.0)
    _settle()
    control.resize(500, 900)
    _settle()
    host = _host_rect(control, "toolbarHost")
    assert host.right() + 1 == 500
    assert control.mask().boundingRect() == host


def test_dragging_the_logo_moves_toolbar_and_mask(shell) -> None:
    _coordinator, control, _floating = shell
    logo = control.findChild(QQuickItem, "minimizeButton")
    start = logo.mapToScene(QPointF(logo.width() / 2, logo.height() / 2)).toPoint()
    QTest.mousePress(control, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    for step in range(1, 21):
        QTest.mouseMove(control, start + QPoint(step * 10, step * 5))
        _APP.processEvents()
    QTest.mouseRelease(
        control, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + QPoint(200, 100)
    )
    _settle()

    host = _host_rect(control, "toolbarHost")
    assert host.x() > 20 and host.y() > 20
    assert control.mask().boundingRect() == host
    assert control.isVisible()


def test_floating_palette_mask_follows_its_host(shell) -> None:
    coordinator, _control, floating = shell
    coordinator.minimize_to_floating()
    _settle()
    host = _host_rect(floating, "paletteHost")
    assert floating.mask().boundingRect() == host

    floating.resize(host.right() - 10, 900)
    _settle()
    clamped = _host_rect(floating, "paletteHost")
    assert clamped.right() + 1 == floating.width()
    assert floating.mask().boundingRect() == clamped
