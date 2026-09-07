"""Test degli adapter QML e del modello strumenti."""

from __future__ import annotations

from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
from core.models import Point, Stroke, ToolType
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.models.tool_list_model import ToolListModel


def _controller(tmp_path) -> AppController:
    settings = Settings(path=tmp_path / "adapter_settings.json")
    return AppController(settings)


def test_drawing_adapter_reflects_controller_and_history(tmp_path) -> None:
    event_bus.clear()
    controller = _controller(tmp_path)
    adapter = DrawingAdapter(controller)
    active_changes = []
    history_changes = []
    adapter.activeChanged.connect(lambda: active_changes.append(True))
    adapter.historyChanged.connect(lambda: history_changes.append(True))

    adapter.toggle_drawing()
    assert adapter.active is True
    assert len(active_changes) == 1

    stroke = Stroke(tool_type=ToolType.PEN, points=[Point(1, 2)])
    controller.finalize_stroke(stroke)
    assert adapter.strokeCount == 1
    assert adapter.canUndo is True
    assert len(history_changes) == 1

    adapter.undo()
    assert adapter.canRedo is True
    event_bus.clear()


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
