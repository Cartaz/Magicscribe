"""Test per config.settings.Settings."""

import json
from pathlib import Path

from config.settings import Settings


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(path=tmp_path / "test_settings.json")


def test_defaults_on_fresh_load(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    settings.load()
    assert settings.get("pen_size") == 5
    assert settings.get("last_tool") == "pen"


def test_set_and_persist(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    settings.load()
    settings.set("pen_size", 10)

    reloaded = _make_settings(tmp_path)
    reloaded.load()
    assert reloaded.get("pen_size") == 10


def test_unknown_key_ignored(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    settings.set("nonexistent_key", 42)
    assert settings.get("nonexistent_key") is None


def test_reset(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    settings.set("pen_size", 99)
    settings.reset()
    assert settings.get("pen_size") == 5


def test_on_change_callback(tmp_path: Path) -> None:
    changes = []
    settings = Settings(
        on_change=lambda key, value: changes.append((key, value)),
        path=tmp_path / "cb_settings.json",
    )
    settings.set("pen_size", 20)
    assert changes == [("pen_size", 20)]


def test_non_object_json_falls_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "test_settings.json"
    path.write_text("[]", encoding="utf-8")

    settings = Settings(path=path)
    settings.load()

    assert settings.get("pen_size") == 5
    assert settings.get("last_tool") == "pen"


def test_invalid_values_are_ignored_on_load(tmp_path: Path) -> None:
    path = tmp_path / "test_settings.json"
    path.write_text(
        json.dumps({
            "pen_size": "enorme",
            "overlay_opacity": -4,
            "show_control_on_start": 1,
            "last_tool": "laser",
            "pen_color": "not-a-color",
        }),
        encoding="utf-8",
    )

    settings = Settings(path=path)
    settings.load()

    assert settings.get("pen_size") == 5
    assert settings.get("overlay_opacity") == 0.75
    assert settings.get("show_control_on_start") is True
    assert settings.get("last_tool") == "pen"
    assert settings.get("pen_color") == "#ff0000"


def test_invalid_set_does_not_replace_current_value(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    settings.set("pen_size", 12)
    settings.set("pen_size", 0)
    settings.set("last_tool", "laser")

    assert settings.get("pen_size") == 12
    assert settings.get("last_tool") == "pen"
