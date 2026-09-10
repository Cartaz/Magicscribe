"""Tests for the Settings-backed tool domain boundary."""

from config.settings import Settings
from core.models import TOOL_SPECS, ToolType
from core.tool_manager import ToolManager, _parse_tool_type


def _make(tmp_path):
    settings = Settings(path=tmp_path / "tools.json")
    return settings, ToolManager(settings)


def test_parse_tool_type_is_defensive() -> None:
    assert _parse_tool_type("pen") is ToolType.PEN
    assert _parse_tool_type(" Circle ") is ToolType.CIRCLE
    assert _parse_tool_type("laser") is ToolType.PEN
    assert _parse_tool_type(None) is ToolType.PEN


def test_configs_are_derived_live_from_settings(tmp_path) -> None:
    settings, manager = _make(tmp_path)
    settings.set("pen_size", 17)
    settings.set("pen_color", "#00ff00")
    config = manager.config_for(ToolType.PEN)
    assert config.size == 17.0
    assert config.color == "#00ff00"


def test_reset_cannot_desynchronize_tool_manager(tmp_path) -> None:
    settings, manager = _make(tmp_path)
    manager.set_tool(ToolType.CIRCLE)
    manager.set_size(ToolType.CIRCLE, 18)
    settings.reset()
    assert manager.current_tool() is ToolType.PEN
    assert manager.config_for(ToolType.CIRCLE).size == 3.0


def test_mutations_validate_through_settings(tmp_path) -> None:
    settings, manager = _make(tmp_path)
    assert manager.set_color(ToolType.PEN, "not-a-color") is False
    assert manager.set_size(ToolType.PEN, 0) is False
    assert manager.config_for(ToolType.PEN).color == "#ff0000"
    assert manager.config_for(ToolType.PEN).size == 5.0
    assert settings.get("pen_color") == "#ff0000"


def test_eraser_has_no_color_setting(tmp_path) -> None:
    settings, manager = _make(tmp_path)
    assert manager.set_color(ToolType.ERASER, "#00ff00") is False
    assert settings.get("eraser_color") is None


def test_setters_report_real_changes_only(tmp_path) -> None:
    _settings, manager = _make(tmp_path)
    assert manager.set_tool(ToolType.PEN) is False
    assert manager.set_tool(ToolType.CIRCLE) is True
    assert manager.set_size(ToolType.CIRCLE, 12) is True
    assert manager.set_size(ToolType.CIRCLE, 12) is False


def test_all_tools_match_canonical_specs(tmp_path) -> None:
    _settings, manager = _make(tmp_path)
    assert manager.all_tools() == [spec.tool_type for spec in TOOL_SPECS]
