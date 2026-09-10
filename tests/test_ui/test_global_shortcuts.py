"""Tests for the XDG Desktop Portal shortcut boundary."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from jeepney import HeaderFields

from config.settings import Settings
from core.app_controller import AppController
from ui.adapters.shell_adapter import ShellAdapter
from ui.native.global_shortcuts import (
    GlobalShortcutService,
    ShortcutSpec,
    _bind_shortcuts_message,
    _bound_shortcut_ids,
    _create_session_message,
    _create_session_options,
    _qt_to_xdg_trigger,
    _request_options,
    _request_path,
    _shortcut_payload,
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


class _FakeCoordinator:
    def control_logo_center(self):
        from PySide6.QtCore import QPointF

        return QPointF()

    def set_control_input_region(self, *_args) -> None:
        pass

    def set_floating_input_region(self, *_args) -> None:
        pass

    def minimize_to_floating(self) -> None:
        pass

    def restore_control_panel(self) -> None:
        pass

    def quit_application(self) -> None:
        pass


def _controller(tmp_path) -> AppController:
    return AppController(Settings(path=tmp_path / "shortcuts.json"))


def test_qt_shortcuts_convert_to_xdg_trigger_format() -> None:
    assert _qt_to_xdg_trigger("F9") == "F9"
    assert _qt_to_xdg_trigger("Ctrl+Shift+F9") == "CTRL+SHIFT+F9"
    assert _qt_to_xdg_trigger("Meta+Alt+P") == "LOGO+ALT+P"


def test_request_path_uses_xdg_sender_convention() -> None:
    assert _request_path(":1.234", "magicscribe_test") == (
        "/org/freedesktop/portal/desktop/request/1_234/magicscribe_test"
    )


def test_portal_payloads_use_explicit_dbus_signatures() -> None:
    shortcuts = (ShortcutSpec("toggle_draw", "Toggle drawing", "F9"),)
    assert _create_session_options("create", "session") == {
        "handle_token": ("s", "create"),
        "session_handle_token": ("s", "session"),
    }
    assert _request_options("bind") == {"handle_token": ("s", "bind")}
    assert _shortcut_payload(shortcuts)[0][0] == "toggle_draw"

    create = _create_session_message("create", "session")
    bind = _bind_shortcuts_message("/session/path", shortcuts, "", "bind")
    assert create.header.fields[HeaderFields.signature] == "a{sv}"
    assert bind.header.fields[HeaderFields.signature] == "oa(sa{sv})sa{sv}"
    assert create.serialise(serial=1)
    assert bind.serialise(serial=2)


def test_bound_shortcuts_fail_closed_on_partial_result() -> None:
    results = {
        "shortcuts": (
            "a(sa{sv})",
            [("toggle_draw", {"trigger_description": ("s", "F9")})],
        )
    }
    assert _bound_shortcut_ids(results) == {"toggle_draw"}
    assert _bound_shortcut_ids({}) == set()


def test_service_requests_and_dispatches_exact_actions(tmp_path) -> None:
    controller = _controller(tmp_path)
    backend = _FakeBackend()
    service = GlobalShortcutService(controller, backend=backend)
    service.start("")
    service.start("")
    assert len(backend.starts) == 1
    shortcuts, parent = backend.starts[0]
    assert parent == ""
    assert [item.shortcut_id for item in shortcuts] == [
        "toggle_draw",
        "toggle_visibility",
        "clear_screen",
        "undo",
        "redo",
    ]

    backend.activated.emit("toggle_draw")
    assert controller.is_drawing_active() is True
    before = controller.is_drawing_active()
    backend.activated.emit("unknown")
    assert controller.is_drawing_active() is before


def test_service_state_drives_shell_fallback_property(tmp_path) -> None:
    controller = _controller(tmp_path)
    backend = _FakeBackend()
    service = GlobalShortcutService(controller, backend=backend)
    adapter = ShellAdapter(_FakeCoordinator(), service)  # type: ignore[arg-type]
    assert adapter.globalDrawingShortcutsActive is False
    backend.registrationFinished.emit(True, "")
    assert adapter.globalDrawingShortcutsActive is True
    service.shutdown()
    assert backend.shutdown_calls == 1
    assert adapter.globalDrawingShortcutsActive is False


def test_portal_backend_keeps_blocking_dbus_off_gui_thread() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "ui" / "native" / "global_shortcuts.py"
    ).read_text(encoding="utf-8")
    assert "PySide6.QtDBus" not in source
    assert "threading.Thread(" in source
    assert "waitForFinished(" not in source
