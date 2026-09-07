from config.settings import Settings
from core.models import ToolType
from core.tool_manager import ToolManager, _parse_tool_type


def _make(tmp_path):
    return Settings(path=tmp_path / "tm.json")


def test_parse_tool_type():
    assert _parse_tool_type("circle") == ToolType.CIRCLE
    assert _parse_tool_type("bad") == ToolType.PEN
    assert _parse_tool_type(None) == ToolType.PEN


def test_invalid_values_never_enter_canonical_config(tmp_path):
    settings = _make(tmp_path)
    manager = ToolManager(settings)
    original_color = manager.config_for(ToolType.PEN).color
    original_size = manager.config_for(ToolType.PEN).size
    manager.set_color(ToolType.PEN, "bad")
    manager.set_size(ToolType.PEN, 0)
    assert manager.config_for(ToolType.PEN).color == original_color
    assert manager.config_for(ToolType.PEN).size == original_size


def test_valid_values_are_normalized_and_persisted(tmp_path):
    settings = _make(tmp_path)
    manager = ToolManager(settings)
    manager.set_color(ToolType.PEN, "#00FF00")
    manager.set_size(ToolType.PEN, 12.7)
    assert manager.config_for(ToolType.PEN).color == "#00ff00"
    assert manager.config_for(ToolType.PEN).size == 12.0
    assert settings.get("pen_size") == 12


def test_eraser_has_no_color_setting(tmp_path):
    settings = _make(tmp_path)
    manager = ToolManager(settings)
    original = manager.config_for(ToolType.ERASER).color
    manager.set_color(ToolType.ERASER, "#00ff00")
    assert manager.config_for(ToolType.ERASER).color == original
    assert settings.get("eraser_color") is None


def test_tool_selection_and_all_tools(tmp_path):
    manager = ToolManager(_make(tmp_path))
    manager.set_tool(ToolType.CIRCLE)
    assert manager.current_tool() == ToolType.CIRCLE
    assert set(manager.all_tools()) == set(ToolType)
