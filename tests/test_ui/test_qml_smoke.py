"""Smoke test offscreen della shell Qt Quick/QML MagicScribe."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QWindow
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlExpression
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.shell_adapter import ShellAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.models.tool_list_model import ToolListModel
from ui.native.window_coordinator import WindowCoordinator
from ui.quick.overlay_surface import OverlaySurface

_APP = QApplication.instance() or QApplication([])


def test_qml_shell_loads_and_transitions_offscreen(tmp_path) -> None:
    """Carica overlay Quick + due finestre QML e verifica il lifecycle shell."""
    event_bus.clear()
    settings = Settings(path=tmp_path / "qml_settings.json")
    controller = AppController(settings)
    drawing_adapter = DrawingAdapter(controller)
    tool_adapter = ToolAdapter(controller)
    tool_model = ToolListModel()

    QQuickWindow.setDefaultAlphaBuffer(True)
    overlay_surface = OverlaySurface(drawing_adapter, tool_adapter)
    coordinator = WindowCoordinator(overlay_surface.window)
    shell_adapter = ShellAdapter(coordinator)

    engine = QQmlApplicationEngine()
    qml_root = Path(__file__).resolve().parents[2] / "ui" / "qml"
    engine.addImportPath(str(qml_root))
    engine.setInitialProperties({
        "drawingAdapter": drawing_adapter,
        "toolAdapter": tool_adapter,
        "shellAdapter": shell_adapter,
        "toolModel": tool_model,
    })

    failures = []
    engine.objectCreationFailed.connect(lambda url: failures.append(url.toString()))
    engine.loadFromModule("MagicScribe", "ControlPanel")
    _APP.processEvents()

    floating_component = QQmlComponent(engine)
    floating_component.loadFromModule("MagicScribe", "FloatingPalette")
    assert floating_component.isReady(), floating_component.errorString()

    floating_object = floating_component.createWithInitialProperties({
        "drawingAdapter": drawing_adapter,
        "shellAdapter": shell_adapter,
    })
    _APP.processEvents()

    try:
        roots = engine.rootObjects()
        assert failures == []
        assert len(roots) == 1

        control_window = roots[0]
        assert isinstance(control_window, QWindow)
        assert control_window.objectName() == "controlPanel"
        assert control_window.isVisible() is False

        assert overlay_surface.window.objectName() == "overlayWindow"
        assert overlay_surface.canvas.objectName() == "drawingCanvas"

        assert isinstance(floating_object, QWindow)
        floating_window = floating_object
        assert floating_window.objectName() == "floatingPalette"
        assert floating_window.isVisible() is False

        # Esercita realmente il boundary QML -> Python. In PySide6 6.11.2 con
        # Python 3.14 gli Slot rinominati tramite @Slot(name=...) possono
        # segfaultare proprio in questo passaggio; usiamo il nome Python nativo.
        expression = QQmlExpression(
            engine.rootContext(),
            control_window,
            "drawingAdapter.toggle_drawing()",
        )
        expression.evaluate()
        assert not expression.hasError(), expression.error().toString()
        assert drawing_adapter.active is True
        drawing_adapter.toggle_drawing()
        assert drawing_adapter.active is False

        overlay_surface.show()
        coordinator.set_control_window(control_window)
        coordinator.set_floating_window(floating_window)

        coordinator.show_control_panel()
        _APP.processEvents()
        assert overlay_surface.window.isVisible() is True
        assert control_window.isVisible() is True
        assert floating_window.isVisible() is False
        assert coordinator.is_minimized_to_floating() is False

        coordinator.minimize_to_floating()
        _APP.processEvents()
        assert control_window.isVisible() is False
        assert floating_window.isVisible() is True
        assert coordinator.is_minimized_to_floating() is True

        shell_adapter.restore_control_panel()
        _APP.processEvents()
        assert control_window.isVisible() is True
        assert floating_window.isVisible() is False
        assert coordinator.is_minimized_to_floating() is False
    finally:
        if isinstance(floating_object, QWindow):
            floating_object.hide()
            floating_object.deleteLater()
        coordinator.shutdown()
        overlay_surface.window.deleteLater()
        floating_component.deleteLater()
        engine.deleteLater()
        event_bus.clear()
        _APP.processEvents()
