from dataclasses import FrozenInstanceError, fields

import pytest

from core.models import AppState, DrawingState, Point, Stroke, TOOL_SPECS, ToolConfig, ToolType


def test_drawing_state_contains_only_operational_states() -> None:
    assert tuple(DrawingState) == (DrawingState.INACTIVE, DrawingState.ACTIVE)


def test_runtime_models_contain_only_supported_state() -> None:
    assert [field.name for field in fields(Point)] == ["x", "y"]
    assert [field.name for field in fields(Stroke)] == [
        "tool_type",
        "points",
        "color",
        "size",
    ]
    assert [field.name for field in fields(ToolConfig)] == ["tool_type", "color", "size"]


def test_app_state_is_an_immutable_snapshot() -> None:
    state = AppState()
    with pytest.raises(FrozenInstanceError):
        state.annotations_visible = False  # type: ignore[misc]


def test_tool_specs_cover_each_tool_exactly_once() -> None:
    assert [spec.tool_type for spec in TOOL_SPECS] == list(ToolType)
    assert len({spec.key for spec in TOOL_SPECS}) == len(TOOL_SPECS)
    assert all(1 <= spec.default_size <= 100 for spec in TOOL_SPECS)
    eraser = next(spec for spec in TOOL_SPECS if spec.tool_type is ToolType.ERASER)
    assert eraser.supports_color is False
    assert eraser.color_key is None
