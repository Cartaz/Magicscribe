"""Runtime binding smoke tests."""

from __future__ import annotations

from PySide6.QtCore import qVersion


def test_qt_version_is_611_or_newer() -> None:
    version = tuple(int(part) for part in qVersion().split(".")[:3])
    assert version >= (6, 11, 0)


def test_production_ui_modules_import() -> None:
    import ui.drawing_engine  # noqa: F401
    import ui.quick.drawing_canvas  # noqa: F401
    import ui.quick.overlay_surface  # noqa: F401
    import ui.tray_icon  # noqa: F401
