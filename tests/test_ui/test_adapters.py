from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
from core.models import Point, Stroke, ToolType
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.models.tool_list_model import ToolListModel


def _controller(tmp_path):
    return AppController(Settings(path=tmp_path / "adapter.json"))


def test_drawing_adapter_reflects_history(tmp_path):
    event_bus.clear()
    controller = _controller(tmp_path)
    adapter = DrawingAdapter(controller)
    adapter.toggle_drawing()
    assert adapter.active is True
    controller.finalize_stroke(Stroke(tool_type=ToolType.PEN, points=[Point(1, 2)]))
    assert adapter.strokeCount == 1
    assert adapter.canUndo is True
    adapter.undo()
    assert adapter.canRedo is True
    event_bus.clear()


def test_tool_adapter_validates_boundary(tmp_path):
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
    adapter.set_color("rgba(12, 34, 56, 0.5)")
    assert adapter.currentColor == "rgba(12,34,56,0.5)"
    event_bus.clear()


def test_tool_list_model_exposes_stable_roles():
    model = ToolListModel()
    assert model.rowCount() == 6
    assert set(model.roleNames().values()) == {b"toolId", b"displayLabel", b"glyph", b"supportsColor"}
