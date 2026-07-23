"""Test per config.settings.Settings."""

import json
import tempfile
from pathlib import Path

from config.settings import Settings


def _make_settings(tmp_path: Path) -> Settings:
    """Crea un'istanza Settings con percorso temporaneo."""
    s = Settings()
    s._path = tmp_path / "test_settings.json"
    return s


def test_defaults_on_fresh_load(tmp_path: Path) -> None:
    """Le impostazioni appena caricate devono corrispondere ai default."""
    s = _make_settings(tmp_path)
    s.load()
    assert s.get("pen_size") == 5
    assert s.get("last_tool") == "pen"


def test_set_and_persist(tmp_path: Path) -> None:
    """set() deve persistere il valore su disco."""
    s = _make_settings(tmp_path)
    s.load()
    s.set("pen_size", 10)
    # Ricarica dal disco
    s2 = _make_settings(tmp_path)
    s2.load()
    assert s2.get("pen_size") == 10


def test_unknown_key_ignored(tmp_path: Path) -> None:
    """Chiavi sconosciute vengono ignorate senza errori."""
    s = _make_settings(tmp_path)
    s.load()
    s.set("nonexistent_key", 42)
    assert s.get("nonexistent_key") is None


def test_reset(tmp_path: Path) -> None:
    """reset() deve ripristinare tutti i valori ai default."""
    s = _make_settings(tmp_path)
    s.load()
    s.set("pen_size", 99)
    s.reset()
    assert s.get("pen_size") == 5


def test_on_change_callback(tmp_path: Path) -> None:
    """Il callback on_change deve essere invocato quando un valore cambia."""
    changes = []
    s = Settings(on_change=lambda k, v: changes.append((k, v)))
    s._path = tmp_path / "cb_settings.json"
    s.load()
    s.set("pen_size", 20)
    assert changes == [("pen_size", 20)]
