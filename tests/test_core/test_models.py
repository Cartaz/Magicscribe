from dataclasses import fields

from core.models import DrawingState, Point, Stroke, ToolConfig


def test_drawing_state_contains_only_operational_states() -> None:
    assert tuple(DrawingState) == (DrawingState.INACTIVE, DrawingState.ACTIVE)


def test_point_contains_only_captured_state() -> None:
    assert [field.name for field in fields(Point)] == ["x", "y"]


def test_stroke_contains_only_runtime_supported_state() -> None:
    assert [field.name for field in fields(Stroke)] == [
        "tool_type",
        "points",
        "color",
        "size",
    ]


def test_tool_config_contains_only_configurable_state() -> None:
    assert [field.name for field in fields(ToolConfig)] == [
        "tool_type",
        "color",
        "size",
    ]
