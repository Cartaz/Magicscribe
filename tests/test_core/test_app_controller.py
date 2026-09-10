"""Tests for the application ownership boundary."""

from dataclasses import FrozenInstanceError

import pytest

from config.settings import Settings
from core.app_controller import AppController
from core.models import DrawingState, Point, Stroke, ToolType


def _make_controller(tmp_path) -> AppController:
    return AppController(Settings(path=tmp_path / "controller.json"))


def test_state_snapshot_is_immutable(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    assert controller.state.drawing_state is DrawingState.INACTIVE
    with pytest.raises(FrozenInstanceError):
        controller.state.annotations_visible = False  # type: ignore[misc]


def test_state_changes_notify_explicit_listeners(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    drawing_changes: list[bool] = []
    visibility_changes: list[bool] = []
    controller.add_drawing_listener(lambda: drawing_changes.append(controller.is_drawing_active()))
    controller.add_visibility_listener(lambda: visibility_changes.append(controller.is_visible()))

    controller.toggle_drawing()
    controller.toggle_visibility()
    assert drawing_changes == [True]
    assert visibility_changes == [False]


def test_history_api_does_not_expose_manager(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    changes: list[int] = []
    controller.add_history_listener(lambda: changes.append(controller.stroke_count()))
    stroke = Stroke(tool_type=ToolType.PEN, points=[Point(1, 2)])
    controller.finalize_stroke(stroke)
    assert controller.stroke_count() == 1
    assert controller.can_undo()
    assert controller.strokes_snapshot() == [stroke]
    assert changes == [1]
    assert not hasattr(controller, "stroke_manager")


def test_tool_workflow_has_single_public_owner(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    tool_changes: list[str] = []
    config_changes: list[float] = []
    controller.add_tool_listener(lambda: tool_changes.append(controller.get_current_tool().name))
    controller.add_tool_config_listener(
        lambda: config_changes.append(controller.get_current_config().size)
    )

    controller.set_tool(ToolType.CIRCLE)
    controller.set_tool_size(12)
    assert controller.get_current_tool() is ToolType.CIRCLE
    assert controller.get_current_config().size == 12.0
    assert tool_changes == ["CIRCLE"]
    assert config_changes == [3.0, 12.0]
    assert not hasattr(controller, "settings")
    assert not hasattr(controller, "tool_manager")


def test_empty_stroke_is_not_committed(tmp_path) -> None:
    controller = _make_controller(tmp_path)
    controller.finalize_stroke(Stroke(tool_type=ToolType.PEN))
    assert controller.stroke_count() == 0
