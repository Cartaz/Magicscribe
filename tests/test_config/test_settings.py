import json
from config.settings import Settings


def test_set_and_persist(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings(path=path)
    assert settings.set("pen_size", 10) is True
    reloaded = Settings(path=path)
    reloaded.load()
    assert reloaded.get("pen_size") == 10


def test_background_persistence_flushes_on_close(tmp_path):
    path = tmp_path / "background.json"
    settings = Settings(path=path, background_persistence=True)
    assert settings.set("pen_size", 17) is True
    settings.close()
    reloaded = Settings(path=path)
    reloaded.load()
    assert reloaded.get("pen_size") == 17


def test_closed_settings_reject_mutation(tmp_path):
    settings = Settings(path=tmp_path / "closed.json", background_persistence=True)
    settings.close()
    assert settings.set("pen_size", 22) is False
    assert settings.get("pen_size") == 5


def test_obsolete_hotkeys_are_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"hotkey_toggle": "F10"}), encoding="utf-8")
    settings = Settings(path=path)
    settings.load()
    assert settings.get("hotkey_toggle") is None
    assert "hotkey_toggle" not in settings.all()


def test_non_object_json_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("[]", encoding="utf-8")
    settings = Settings(path=path)
    settings.load()
    assert settings.get("pen_size") == 5


def test_invalid_values_are_ignored_on_load(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"pen_size": "x", "last_tool": "laser", "pen_color": "bad"}), encoding="utf-8")
    settings = Settings(path=path)
    settings.load()
    assert settings.get("pen_size") == 5
    assert settings.get("last_tool") == "pen"
    assert settings.get("pen_color") == "#ff0000"


def test_validation_has_no_side_effects(tmp_path):
    settings = Settings(path=tmp_path / "settings.json")
    assert settings.is_valid("pen_color", "#00ff00") is True
    assert settings.is_valid("pen_color", "invalid") is False
    assert settings.is_valid("pen_size", 12.5) is True
    assert settings.is_valid("pen_size", 0) is False
    assert settings.get("pen_color") == "#ff0000"


def test_renderer_color_formats_are_preserved(tmp_path):
    settings = Settings(path=tmp_path / "settings.json")
    settings.set("pen_color", "#AABBCCDD")
    assert settings.get("pen_color") == "#aabbccdd"
    settings.set("pen_color", "rgba(12, 34, 56, 0.5)")
    assert settings.get("pen_color") == "rgba(12,34,56,0.5)"


def test_reset_and_callback(tmp_path):
    changes = []
    settings = Settings(path=tmp_path / "settings.json", on_change=lambda k, v: changes.append((k, v)))
    settings.set("pen_size", 20)
    assert changes == [("pen_size", 20)]
    settings.reset()
    assert settings.get("pen_size") == 5
