"""Test per core.tool_manager.ToolManager."""

from config.settings import Settings
from core.models import ToolType
from core.tool_manager import ToolManager, _parse_tool_type


def _make_settings(tmp_path) -> Settings:
    settings = Settings(path=tmp_path / "tm_settings.json")
    settings.load()
    return settings


def test_parse_tool_type_valid_string() -> None:
    assert _parse_tool_type("pen") == ToolType.PEN
    assert _parse_tool_type("ERASER") == ToolType.ERASER
    assert _parse_tool_type("  Circle  ") == ToolType.CIRCLE


def test_parse_tool_type_invalid_falls_back_to_pen() -> None:
    assert _parse_tool_type("nonexistent") == ToolType.PEN
    assert _parse_tool_type("") == ToolType.PEN
    assert _parse_tool_type(None) == ToolType.PEN
    assert _parse_tool_type(42) == ToolType.PEN


def test_parse_tool_type_accepts_enum() -> None:
    assert _parse_tool_type(ToolType.LINE) == ToolType.LINE


def test_tool_manager_with_corrupted_last_tool(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    settings._data["last_tool"] = "strumento_inventato"
    manager = ToolManager(settings)
    assert manager.current_tool() == ToolType.PEN


def test_tool_manager_with_none_last_tool(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    settings._data["last_tool"] = None
    manager = ToolManager(settings)
    assert manager.current_tool() == ToolType.PEN


def test_set_color_ignored_for_eraser(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    original_config = manager.config_for(ToolType.ERASER)
    manager.set_color(ToolType.ERASER, "#00ff00")
    assert manager.config_for(ToolType.ERASER).color == original_config.color
    assert settings.get("eraser_color") is None


def test_set_color_updates_config_for_normal_tools(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    manager.set_color(ToolType.PEN, "#00ff00")
    assert manager.config_for(ToolType.PEN).color == "#00ff00"
    assert settings.get("pen_color") == "#00ff00"


def test_set_color_normalizes_before_canonical_update(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    manager.set_color(ToolType.PEN, "#00FF00")
    assert manager.config_for(ToolType.PEN).color == "#00ff00"


def test_invalid_color_never_enters_canonical_config(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    original = manager.config_for(ToolType.PEN)
    manager.set_color(ToolType.PEN, "not-a-color")
    assert manager.config_for(ToolType.PEN) == original
    assert settings.get("pen_color") == original.color


def test_set_size_updates_eraser_setting(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    manager.set_size(ToolType.ERASER, 55.0)
    assert manager.config_for(ToolType.ERASER).size == 55.0
    assert settings.get("eraser_size") == 55


def test_set_size_persists_for_normal_tools(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    manager.set_size(ToolType.PEN, 12.7)
    assert manager.config_for(ToolType.PEN).size == 12.0
    assert settings.get("pen_size") == 12


def test_invalid_size_never_enters_canonical_config(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    original = manager.config_for(ToolType.PEN)
    manager.set_size(ToolType.PEN, 0.0)
    assert manager.config_for(ToolType.PEN) == original
    assert settings.get("pen_size") == original.size


def test_set_tool_noop_when_same(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    assert manager.current_tool() == ToolType.PEN
    manager.set_tool(ToolType.PEN)
    assert manager.current_tool() == ToolType.PEN


def test_set_tool_persists_canonical_selection(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    manager.set_tool(ToolType.CIRCLE)
    assert manager.current_tool() == ToolType.CIRCLE
    assert settings.get("last_tool") == "circle"


def test_all_tools_returns_all_enum_values(tmp_path) -> None:
    settings = _make_settings(tmp_path)
    manager = ToolManager(settings)
    assert set(manager.all_tools()) == set(ToolType)
