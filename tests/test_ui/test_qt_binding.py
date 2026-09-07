"""Smoke test del binding Qt usato dalla UI."""

from pathlib import Path

from PySide6.QtCore import qVersion


def test_qt_version_is_611_or_newer() -> None:
    version = tuple(int(part) for part in qVersion().split(".")[:3])
    assert version >= (6, 11, 0)


def test_no_pyqt6_references_remain_in_runtime_sources() -> None:
    root = Path(__file__).resolve().parents[2]
    candidates = [root / "main.py", *sorted((root / "ui").rglob("*.py"))]
    offenders = [
        path.relative_to(root).as_posix()
        for path in candidates
        if "PyQt6" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_widget_modules_import_with_pyside6() -> None:
    import ui.drawing_engine  # noqa: F401
    import ui.event_bridge  # noqa: F401
    import ui.main_window  # noqa: F401
    import ui.overlay_window  # noqa: F401
    import ui.tray_icon  # noqa: F401
