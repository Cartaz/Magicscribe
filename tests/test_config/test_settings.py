"""Test per config.settings.Settings."""

import json
from pathlib import Path
from threading import get_ident

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
    assert settings.set("pen_size", 10) is True

    reloaded = _make_settings(tmp_path)
    reloaded.load()
    assert reloaded.get("pen_size") == 10


def test_unknown_key_ignored(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    assert settings.set("nonexistent_key", 42) is False
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
    assert settings.set("pen_size", 0) is False
    assert settings.set("last_tool", "laser") is False

    assert settings.get("pen_size") == 12
    assert settings.get("last_tool") == "pen"


def test_color_formats_supported_by_renderer_are_preserved(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)

    settings.set("pen_color", "#AABBCCDD")
    assert settings.get("pen_color") == "#aabbccdd"

    settings.set("pen_color", "rgba(12, 34, 56, 0.5)")
    assert settings.get("pen_color") == "rgba(12,34,56,0.5)"


def test_invalid_rgba_is_rejected(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    original = settings.get("pen_color")

    assert settings.set("pen_color", "rgba(300,0,0,1)") is False
    assert settings.set("pen_color", "rgba(0,0,0,2)") is False
    assert settings.get("pen_color") == original


def test_validation_has_no_side_effects(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    assert settings.is_valid("pen_color", "#00ff00") is True
    assert settings.is_valid("pen_color", "invalid") is False
    assert settings.is_valid("pen_size", 12.5) is True
    assert settings.is_valid("pen_size", 0) is False
    assert settings.get("pen_color") == "#ff0000"
    assert settings.get("pen_size") == 5


def test_obsolete_hotkey_keys_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "test_settings.json"
    path.write_text(
        json.dumps({
            "hotkey_toggle": "F10",
            "hotkey_visibility": "Ctrl+F10",
            "pen_size": 11,
        }),
        encoding="utf-8",
    )
    settings = Settings(path=path)
    settings.load()

    assert settings.get("pen_size") == 11
    assert settings.get("hotkey_toggle") is None
    assert settings.get("hotkey_visibility") is None
    assert "hotkey_toggle" not in settings.all()


def test_background_persistence_flushes_on_close(tmp_path: Path) -> None:
    path = tmp_path / "background.json"
    settings = Settings(path=path, background_persistence=True)
    assert settings.set("pen_size", 17) is True
    settings.close()

    reloaded = Settings(path=path)
    reloaded.load()
    assert reloaded.get("pen_size") == 17


def test_background_writer_runs_off_calling_thread(tmp_path: Path) -> None:
    settings = Settings(
        path=tmp_path / "background_thread.json",
        background_persistence=True,
    )
    caller_thread = get_ident()
    writer_threads: list[int] = []
    original_write = settings._write_snapshot

    def recording_write(snapshot: dict) -> None:
        writer_threads.append(get_ident())
        original_write(snapshot)

    settings._write_snapshot = recording_write
    settings.set("pen_size", 18)
    settings.close()

    assert writer_threads
    assert all(thread_id != caller_thread for thread_id in writer_threads)


def test_closed_settings_reject_mutation(tmp_path: Path) -> None:
    settings = Settings(
        path=tmp_path / "closed.json",
        background_persistence=True,
    )
    settings.close()
    assert settings.set("pen_size", 22) is False
    assert settings.get("pen_size") == 5
