"""Test per core.tool_manager.ToolManager."""

from core.tool_manager import ToolManager, _parse_tool_type
from core.models import ToolType
from config.settings import Settings


def _make_settings(tmp_path) -> Settings:
    """Crea un Settings con percorso temporaneo."""
    s = Settings()
    s._path = tmp_path / "tm_settings.json"
    s.load()
    return s


def test_parse_tool_type_valid_string() -> None:
    """_parse_tool_type deve convertire stringhe valide."""
    assert _parse_tool_type("pen") == ToolType.PEN
    assert _parse_tool_type("ERASER") == ToolType.ERASER
    assert _parse_tool_type("  Circle  ") == ToolType.CIRCLE


def test_parse_tool_type_invalid_falls_back_to_pen() -> None:
    """Stringhe non valide devono ricadere su PEN senza eccezioni."""
    assert _parse_tool_type("nonexistent") == ToolType.PEN
    assert _parse_tool_type("") == ToolType.PEN
    assert _parse_tool_type(None) == ToolType.PEN
    assert _parse_tool_type(42) == ToolType.PEN


def test_parse_tool_type_accepts_enum() -> None:
    """Passare gia' un ToolType deve restituirlo invariato."""
    assert _parse_tool_type(ToolType.LINE) == ToolType.LINE


def test_tool_manager_with_corrupted_last_tool(tmp_path) -> None:
    """ToolManager non deve crashare se last_tool e' corrotto nel file."""
    s = _make_settings(tmp_path)
    s.set("last_tool", "strumento_inventato")
    # Deve istanziarsi senza sollevare KeyError
    tm = ToolManager(s)
    assert tm.current_tool() == ToolType.PEN


def test_tool_manager_with_none_last_tool(tmp_path) -> None:
    """ToolManager deve gestire last_tool = None (file corrotto)."""
    s = _make_settings(tmp_path)
    s._data["last_tool"] = None
    tm = ToolManager(s)
    assert tm.current_tool() == ToolType.PEN


def test_set_color_ignored_for_eraser(tmp_path) -> None:
    """set_color su ERASER deve essere un no-op (non scrive setting inesistente)."""
    s = _make_settings(tmp_path)
    tm = ToolManager(s)
    original_config = tm.config_for(ToolType.ERASER)
    tm.set_color(ToolType.ERASER, "#00ff00")
    # La configurazione non deve cambiare
    assert tm.config_for(ToolType.ERASER).color == original_config.color
    # Nessuna chiave eraser_color deve essere stata creata
    assert s.get("eraser_color") is None


def test_set_color_updates_config_for_normal_tools(tmp_path) -> None:
    """set_color su PEN deve aggiornare config e persistere."""
    s = _make_settings(tmp_path)
    tm = ToolManager(s)
    tm.set_color(ToolType.PEN, "#00ff00")
    assert tm.config_for(ToolType.PEN).color == "#00ff00"
    assert s.get("pen_color") == "#00ff00"


def test_set_size_updates_eraser_setting(tmp_path) -> None:
    """set_size su ERASER deve scrivere eraser_size (chiave corretta)."""
    s = _make_settings(tmp_path)
    tm = ToolManager(s)
    tm.set_size(ToolType.ERASER, 55.0)
    assert tm.config_for(ToolType.ERASER).size == 55.0
    assert s.get("eraser_size") == 55


def test_set_size_persists_for_normal_tools(tmp_path) -> None:
    """set_size su PEN deve scrivere pen_size come int."""
    s = _make_settings(tmp_path)
    tm = ToolManager(s)
    tm.set_size(ToolType.PEN, 12.7)
    assert s.get("pen_size") == 12


def test_set_tool_noop_when_same(tmp_path) -> None:
    """set_tool con lo stesso strumento non deve emettere eventi."""
    s = _make_settings(tmp_path)
    tm = ToolManager(s)
    assert tm.current_tool() == ToolType.PEN
    # Chiamata noop
    tm.set_tool(ToolType.PEN)
    assert tm.current_tool() == ToolType.PEN


def test_all_tools_returns_all_enum_values(tmp_path) -> None:
    """all_tools deve restituire tutti i ToolType."""
    s = _make_settings(tmp_path)
    tm = ToolManager(s)
    assert set(tm.all_tools()) == set(ToolType)
