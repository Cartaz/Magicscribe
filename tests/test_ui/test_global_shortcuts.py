"""Test del servizio GlobalShortcuts e dei guardrail di fallback."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtDBus import QDBusConnection

from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
from ui.native.global_shortcuts import (
    GlobalShortcutService,
    PortalGlobalShortcutBackend,
    ShortcutSpec,
    _qt_to_xdg_trigger,
    _request_path,
)


class _FakeBackend(QObject):
    activated = Signal(str)
    registrationFinished = Signal(bool, str)

    def __init__(self) -> None:
        super().__init__()
        self.starts: list[tuple[tuple[ShortcutSpec, ...], str]] = []
        self.shutdown_calls = 0

    def start(self, shortcuts: tuple[ShortcutSpec, ...], parent_window: str = "") -> None:
        self.starts.append((shortcuts, parent_window))

    def shutdown(self) -> None:
        self.shutdown_calls += 1


def _controller(tmp_path) -> AppController:
    event_bus.clear()
    return AppController(Settings(path=tmp_path / "shortcut_settings.json"))


def test_qt_shortcuts_convert_to_xdg_trigger_format() -> None:
    assert _qt_to_xdg_trigger("F9") == "F9"
    assert _qt_to_xdg_trigger("Ctrl+Shift+F9") == "CTRL+SHIFT+F9"
    assert _qt_to_xdg_trigger("Meta+Alt+P") == "LOGO+ALT+P"


def test_request_path_uses_xdg_sender_convention() -> None:
    assert _request_path(":1.234", "magicscribe_test") == (
        "/org/freedesktop/portal/desktop/request/1_234/magicscribe_test"
    )


def test_service_requests_exact_drawing_shortcuts_and_is_idempotent(tmp_path) -> None:
    controller = _controller(tmp_path)
    backend = _FakeBackend()
    service = GlobalShortcutService(controller, backend=backend)

    service.start("x11:1234")
    service.start("x11:ffff")

    assert len(backend.starts) == 1
    shortcuts, parent_window = backend.starts[0]
    assert parent_window == "x11:1234"
    assert [item.shortcut_id for item in shortcuts] == [
        "toggle_draw",
        "toggle_visibility",
        "clear_screen",
        "undo",
        "redo",
    ]
    assert [item.preferred_trigger for item in shortcuts] == [
        "F9",
        "CTRL+SHIFT+F9",
        "SHIFT+F9",
        "F8",
        "SHIFT+F8",
    ]

    event_bus.clear()


def test_service_dispatches_only_registered_actions(tmp_path) -> None:
    controller = _controller(tmp_path)
    backend = _FakeBackend()
    service = GlobalShortcutService(controller, backend=backend)

    assert controller.is_drawing_active() is False
    backend.activated.emit("toggle_draw")
    assert controller.is_drawing_active() is True

    visible_before = controller.is_visible()
    backend.activated.emit("toggle_visibility")
    assert controller.is_visible() is (not visible_before)

    state_before = controller.is_drawing_active()
    backend.activated.emit("not_a_shortcut")
    assert controller.is_drawing_active() is state_before

    event_bus.clear()


def test_service_active_state_tracks_backend_and_shutdown(tmp_path) -> None:
    controller = _controller(tmp_path)
    backend = _FakeBackend()
    service = GlobalShortcutService(controller, backend=backend)
    changes: list[bool] = []
    failures: list[str] = []
    service.activeChanged.connect(lambda: changes.append(service.active))
    service.registrationFailed.connect(failures.append)

    backend.registrationFinished.emit(True, "")
    assert service.active is True
    assert changes == [True]

    service.shutdown()
    assert backend.shutdown_calls == 1
    assert service.active is False
    assert changes == [True, False]

    backend.registrationFinished.emit(False, "portal unavailable")
    assert failures == ["portal unavailable"]

    event_bus.clear()


def test_portal_backend_fails_closed_on_partial_binding() -> None:
    backend = PortalGlobalShortcutBackend(bus=QDBusConnection.sessionBus())
    backend._requested_ids = {"toggle_draw", "undo"}
    outcomes: list[tuple[bool, str]] = []
    backend.registrationFinished.connect(
        lambda success, message: outcomes.append((success, message))
    )

    backend._on_bind_response(
        0,
        {"shortcuts": [("toggle_draw", {"trigger_description": "F9"})]},
    )

    assert outcomes
    assert outcomes[-1][0] is False
    assert "tutte" in outcomes[-1][1]


def test_portal_backend_source_never_waits_synchronously() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "ui"
        / "native"
        / "global_shortcuts.py"
    ).read_text(encoding="utf-8")
    assert "waitForFinished(" not in source
    assert "BlockWithGui" not in source
