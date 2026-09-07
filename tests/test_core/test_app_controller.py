"""Test per core.app_controller.AppController."""

from core.app_controller import AppController
from core.models import ToolType, DrawingState, Stroke, Point
from config.settings import Settings


def _make_controller(tmp_path) -> AppController:
    settings = Settings(path=tmp_path / "controller_settings.json")
    return AppController(settings)


def test_toggle_drawing(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    assert controller.state.drawing_state == DrawingState.INACTIVE

    controller.toggle_drawing()
    assert controller.is_drawing_active()
    assert controller.state.drawing_state == DrawingState.ACTIVE

    controller.toggle_drawing()
    assert not controller.is_drawing_active()
    assert controller.state.drawing_state == DrawingState.INACTIVE


def test_toggle_visibility(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    assert controller.is_visible()

    controller.toggle_visibility()
    assert not controller.is_visible()

    controller.toggle_visibility()
    assert controller.is_visible()


def test_set_tool(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    assert controller.get_current_tool() == ToolType.PEN

    controller.set_tool(ToolType.ERASER)
    assert controller.get_current_tool() == ToolType.ERASER


def test_persisted_tool_is_single_source_of_truth(tmp_path) -> None:
    settings = Settings(path=tmp_path / "controller_settings.json")
    settings.set("last_tool", "circle")

    controller = AppController(settings)

    assert controller.get_current_tool() == ToolType.CIRCLE
    assert not hasattr(controller.state, "current_tool")


def test_create_stroke(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    stroke = controller.create_stroke(ToolType.PEN)
    assert stroke.tool_type == ToolType.PEN
    assert len(stroke.points) == 0


def test_finalize_stroke(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    stroke = Stroke(tool_type=ToolType.PEN)
    stroke.points.append(Point(x=10, y=20))
    controller.finalize_stroke(stroke)
    assert controller.stroke_manager.stroke_count == 1
