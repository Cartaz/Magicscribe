"""Test degli adapter QML e del modello strumenti."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF

from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
from core.models import Point, Stroke, ToolType
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.shell_adapter import ShellAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.models.tool_list_model import ToolListModel


def _controller(tmp_path) -> AppController:
    settings = Settings(path=tmp_path / "adapter_settings.json")
    return AppController(settings)


def test_drawing_adapter_actions_are_synchronous(tmp_path) -> None:
    event_bus.clear()
    controller = _controller(tmp_path)
    adapter = DrawingAdapter(controller)
    active_changes = []
    adapter.activeChanged.connect(lambda: active_changes.append(True))

    adapter.toggle_drawing()

    assert adapter.active is True
    assert active_changes == [True]
    event_bus.clear()


def test_drawing_adapter_reflects_history_after_actions(tmp_path) -> None:
    event_bus.clear()
    controller = _controller(tmp_path)
    adapter = DrawingAdapter(controller)
    history_changes = []
    adapter.historyChanged.connect(lambda: history_changes.append(True))

    stroke = Stroke(tool_type=ToolType.PEN, points=[Point(1, 2)])
    controller.finalize_stroke(stroke)
    assert adapter.strokeCount == 1
    assert adapter.canUndo is True
    assert len(history_changes) == 1

    adapter.undo()
    assert adapter.canRedo is True
    event_bus.clear()


def test_drawing_adapter_close_unsubscribes_owned_events(tmp_path) -> None:
    event_bus.clear()
    controller = _controller(tmp_path)
    adapter = DrawingAdapter(controller)
    active_changes = []
    history_changes = []
    adapter.activeChanged.connect(lambda: active_changes.append(True))
    adapter.historyChanged.connect(lambda: history_changes.append(True))

    adapter.close()
    adapter.close()
    controller.toggle_drawing()
    controller.finalize_stroke(
        Stroke(tool_type=ToolType.PEN, points=[Point(1, 2)])
    )

    assert adapter.active is True
    assert adapter.strokeCount == 1
    assert active_changes == []
    assert history_changes == []
    event_bus.clear()


def test_qml_adapters_never_alias_slot_names() -> None:
    """PySide6 6.11.2/Python 3.14 can crash on QML -> @Slot(name=...)."""
    root = Path(__file__).resolve().parents[2]
    alias_pattern = re.compile(
        r"^\s*@Slot\([^)]*\bname\s*=",
        re.MULTILINE,
    )

    for relative_path in (
        "ui/adapters/drawing_adapter.py",
        "ui/adapters/tool_adapter.py",
        "ui/adapters/shell_adapter.py",
    ):
        source = (root / relative_path).read_text(encoding="utf-8")
        assert alias_pattern.search(source) is None, relative_path


def test_qml_calls_native_snake_case_slot_names() -> None:
    root = Path(__file__).resolve().parents[2] / "ui" / "qml" / "MagicScribe"
    source = "\n".join(
        (root / name).read_text(encoding="utf-8")
        for name in ("ControlPanel.qml", "FloatingPalette.qml")
    )

    for call in (
        "toggle_drawing(",
        "toggle_visibility(",
        "clear_screen(",
        "select_tool(",
        "set_color(",
        "set_size(",
        "minimize_to_floating(",
        "restore_control_panel(",
        "quit_application(",
    ):
        assert call in source

    for old_call in (
        "toggleDrawing(",
        "toggleVisibility(",
        "clearScreen(",
        "selectTool(",
        "setColor(",
        "setSize(",
        "minimizeToFloating(",
        "restoreControlPanel(",
        "quitApplication(",
    ):
        assert old_call not in source


def test_wayland_restore_aligns_toolbar_logo_to_current_floating_center() -> None:
    class FakeWindow:
        def __init__(self, properties: dict[str, float]) -> None:
            self.properties = dict(properties)

        def property(self, name: str):
            return self.properties.get(name)

        def setProperty(self, name: str, value) -> bool:  # noqa: N802
            self.properties[name] = value
            return True

    class FakeCoordinator:
        def __init__(self) -> None:
            self._absolute_positioning = False
            self._control_window = FakeWindow(
                {"layerShellPanelX": 100.0, "layerShellPanelY": 200.0}
            )
            self._floating_window = FakeWindow(
                {
                    "layerShellPaletteX": 371.0,
                    "layerShellPaletteY": 571.0,
                    "paletteWidth": 58.0,
                    "paletteHeight": 58.0,
                }
            )
            self.restored = False

        def restore_control_panel(self) -> None:
            self.restored = True

    coordinator = FakeCoordinator()
    adapter = ShellAdapter(coordinator)  # type: ignore[arg-type]

    # Il logo corrente e' a (152, 250), quindi il suo offset dal toolbarHost
    # e' (52, 50). La floating icon ha centro (400, 600): il toolbarHost deve
    # traslare a (348, 550) per mantenere la corrispondenza 1:1 al restore.
    adapter._control_logo_center = lambda: QPointF(152.0, 250.0)  # type: ignore[method-assign]

    adapter.restore_control_panel()

    assert coordinator._control_window.property("layerShellPanelX") == pytest.approx(348.0)
    assert coordinator._control_window.property("layerShellPanelY") == pytest.approx(550.0)
    assert coordinator.restored is True


def test_tool_adapter_uses_canonical_tool_manager(tmp_path) -> None:
    event_bus.clear()
    controller = _controller(tmp_path)
    adapter = ToolAdapter(controller)

    adapter.select_tool("circle")
    assert controller.get_current_tool() == ToolType.CIRCLE
    assert adapter.currentTool == "circle"
    assert adapter.colorAvailable is True

    adapter.set_color("#00ff00")
    adapter.set_size(12.0)
    assert adapter.currentColor == "#00ff00"
    assert adapter.currentSize == 12.0

    adapter.select_tool("eraser")
    assert adapter.colorAvailable is False
    event_bus.clear()


def test_tool_adapter_close_unsubscribes_owned_events(tmp_path) -> None:
    event_bus.clear()
    controller = _controller(tmp_path)
    adapter = ToolAdapter(controller)
    current_changes = []
    config_changes = []
    adapter.currentToolChanged.connect(lambda: current_changes.append(True))
    adapter.configChanged.connect(lambda: config_changes.append(True))

    adapter.close()
    adapter.close()
    controller.set_tool(ToolType.CIRCLE)
    controller.tool_manager.set_size(ToolType.CIRCLE, 12)

    assert adapter.currentTool == "circle"
    assert adapter.currentSize == 12.0
    assert current_changes == []
    assert config_changes == []
    event_bus.clear()


def test_tool_adapter_rejects_invalid_ui_values(tmp_path) -> None:
    event_bus.clear()
    controller = _controller(tmp_path)
    adapter = ToolAdapter(controller)
    original_color = adapter.currentColor

    adapter.select_tool("laser")
    adapter.set_size(0.0)
    adapter.set_color("not-a-color")

    assert controller.get_current_tool() == ToolType.PEN
    assert adapter.currentSize == 5.0
    assert adapter.currentColor == original_color
    event_bus.clear()


def test_tool_adapter_accepts_renderer_supported_rgba(tmp_path) -> None:
    event_bus.clear()
    controller = _controller(tmp_path)
    adapter = ToolAdapter(controller)

    adapter.set_color("rgba(12, 34, 56, 0.5)")
    assert adapter.currentColor == "rgba(12,34,56,0.5)"
    event_bus.clear()


def test_tool_list_model_exposes_stable_roles() -> None:
    model = ToolListModel()
    roles = model.roleNames()

    assert model.rowCount() == 6
    assert set(roles.values()) == {
        b"toolId", b"displayLabel", b"glyph", b"supportsColor",
    }

    first = model.index(0, 0)
    second = model.index(1, 0)
    assert model.data(first, model.ToolIdRole) == "pen"
    assert model.data(second, model.ToolIdRole) == "eraser"
    assert model.data(second, model.SupportsColorRole) is False
