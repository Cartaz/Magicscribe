"""Regression guard for runtime Wayland input-region changes."""

from PySide6.QtCore import Qt

from ui.quick.overlay_surface import OverlaySurface


class _FakeWindow:
    def __init__(self, *, visible: bool) -> None:
        self._visible = visible
        self.flags: list[tuple[Qt.WindowType, bool]] = []
        self.show_calls = 0
        self.update_requests = 0

    def isVisible(self) -> bool:
        return self._visible

    def setFlag(self, flag: Qt.WindowType, enabled: bool) -> None:
        self.flags.append((flag, enabled))

    def show(self) -> None:
        self._visible = True
        self.show_calls += 1

    def requestUpdate(self) -> None:
        self.update_requests += 1


def test_visible_overlay_schedules_surface_commit_after_input_region_change() -> None:
    window = _FakeWindow(visible=True)

    OverlaySurface._set_qt_input_transparency(window, True)  # type: ignore[arg-type]

    assert window.flags == [(Qt.WindowType.WindowTransparentForInput, True)]
    assert window.update_requests == 1


def test_unmapped_overlay_does_not_schedule_redundant_update() -> None:
    window = _FakeWindow(visible=False)

    OverlaySurface._set_qt_input_transparency(window, True)  # type: ignore[arg-type]

    assert window.flags == [(Qt.WindowType.WindowTransparentForInput, True)]
    assert window.update_requests == 0
