"""Tests for the validated persistent settings store."""

import json
from pathlib import Path
from threading import get_ident

from config.settings import Settings
from core.models import TOOL_SPECS


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(path=tmp_path / "settings.json")


def test_defaults_follow_canonical_tool_specs(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    for spec in TOOL_SPECS:
        assert settings.get(spec.size_key) == spec.default_size
        if spec.color_key is not None:
            assert settings.get(spec.color_key) == spec.default_color
    assert settings.get("last_tool") == "pen"


def test_set_persists_and_reloads(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(path=path)
    assert settings.set("pen_size", 10)
    reloaded = Settings(path=path)
    reloaded.load()
    assert reloaded.get("pen_size") == 10


def test_unknown_and_invalid_values_are_rejected(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    assert settings.set("nonexistent_key", 42) is False
    assert settings.set("pen_size", 0) is False
    assert settings.set("last_tool", "laser") is False
    assert settings.set("pen_color", "not-a-color") is False


def test_invalid_file_values_fall_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "pen_size": "enorme",
                "show_control_on_start": 1,
                "last_tool": "laser",
                "pen_color": "not-a-color",
                "obsolete": 123,
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(path=path)
    settings.load()
    assert settings.get("pen_size") == 5
    assert settings.get("show_control_on_start") is True
    assert settings.get("last_tool") == "pen"
    assert settings.get("pen_color") == "#ff0000"
    assert settings.get("obsolete") is None


def test_non_object_json_falls_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("[]", encoding="utf-8")
    settings = Settings(path=path)
    settings.load()
    assert settings.get("pen_size") == 5


def test_colors_are_normalized_rrggbb_only(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    assert settings.set("pen_color", " #AABBCC ")
    assert settings.get("pen_color") == "#aabbcc"
    # The UI has no alpha: new values are only accepted as #rrggbb.
    assert settings.set("pen_color", "#AABBCCDD") is False
    assert settings.set("pen_color", "rgba(12, 34, 56, 0.5)") is False
    assert settings.get("pen_color") == "#aabbcc"


def test_legacy_colors_saved_by_older_versions_are_migrated(tmp_path: Path) -> None:
    keys = [spec.color_key for spec in TOOL_SPECS if spec.color_key is not None]
    assert len(keys) >= 2
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({keys[0]: "rgba(12, 34, 56, 0.5)", keys[1]: "#80AABBCC"}),
        encoding="utf-8",
    )
    settings = Settings(path=path)
    settings.load()
    assert settings.get(keys[0]) == "#0c2238"
    # Older versions followed QColor: 9-digit hex is #AARRGGBB.
    assert settings.get(keys[1]) == "#aabbcc"
    # The migration is written back once, so it does not repeat at every start.
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved[keys[0]] == "#0c2238" and saved[keys[1]] == "#aabbcc"


def test_malformed_legacy_colors_fall_back_to_defaults(tmp_path: Path) -> None:
    spec = next(spec for spec in TOOL_SPECS if spec.color_key is not None)
    for legacy in ("rgba(300, 0, 0, 1)", "rgba(1, 2, 3)", "rgba(1, 2, 3, 2)", "#80aabbcz"):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({spec.color_key: legacy}), encoding="utf-8")
        settings = Settings(path=path)
        settings.load()
        assert settings.get(spec.color_key) == spec.default_color, legacy


def test_last_tool_is_normalized_to_its_key(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    assert settings.set("last_tool", " Circle ")
    assert settings.get("last_tool") == "circle"


def test_background_persistence_flushes_on_close(tmp_path: Path) -> None:
    path = tmp_path / "background.json"
    settings = Settings(path=path, background_persistence=True)
    assert settings.set("pen_size", 17)
    settings.close()
    reloaded = Settings(path=path)
    reloaded.load()
    assert reloaded.get("pen_size") == 17


def test_background_writer_runs_off_calling_thread(tmp_path: Path) -> None:
    settings = Settings(path=tmp_path / "background.json", background_persistence=True)
    caller = get_ident()
    writer_threads: list[int] = []
    original = settings._write_snapshot

    def recording_write(snapshot: dict) -> None:
        writer_threads.append(get_ident())
        original(snapshot)

    settings._write_snapshot = recording_write
    settings.set("pen_size", 18)
    settings.close()
    assert writer_threads
    assert all(thread != caller for thread in writer_threads)


def test_closed_settings_reject_mutation(tmp_path: Path) -> None:
    settings = Settings(path=tmp_path / "closed.json", background_persistence=True)
    settings.close()
    assert settings.set("pen_size", 22) is False
