"""Test del servizio GlobalShortcuts e dei guardrail di fallback."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from jeepney import HeaderFields

from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import event_bus
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
    def minimize_to_floating(self) -> None:
        pass

    def restore_control_panel(self) -> None:
        pass

    def quit_application(self) -> None:
        pass


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


def test_portal_vardicts_use_explicit_variant_signatures() -> None:
    create = _create_session_options("create_token", "session_token")
    bind = _request_options("bind_token")
    shortcuts = _shortcut_payload((
        ShortcutSpec("toggle_draw", "Toggle drawing", "F9"),
    ))

    assert create == {
        "handle_token": ("s", "create_token"),
        "session_handle_token": ("s", "session_token"),
    }
    assert bind == {"handle_token": ("s", "bind_token")}
    assert shortcuts == [
        (
            "toggle_draw",
            {
                "description": ("s", "Toggle drawing"),
                "preferred_trigger": ("s", "F9"),
            },
        )
    ]


def test_portal_messages_serialize_exact_compound_signatures() -> None:
    shortcuts = (
        ShortcutSpec("toggle_draw", "Toggle drawing", "F9"),
        ShortcutSpec("undo", "Undo", "F8"),
    )
    create = _create_session_message("create_token", "session_token")
    bind = _bind_shortcuts_message(
        "/org/freedesktop/portal/desktop/session/1_2/session_token",
        shortcuts,
        "x11:abc",
        "bind_token",
    )

    assert create.header.fields[HeaderFields.signature] == "a{sv}"
    assert bind.header.fields[HeaderFields.signature] == "oa(sa{sv})sa{sv}"

    # La serializzazione e' il guardrail che mancava al precedente backend
    # PySide6: tuple/dict non devono degradare a un PyObjectWrapper runtime.
    assert create.serialise(serial=1)
    assert bind.serialise(serial=2)


def test_bound_shortcut_ids_fail_closed_on_partial_result() -> None:
    results = {
        "shortcuts": (
            "a(sa{sv})",
            [
                (
                    "toggle_draw",
                    {"trigger_description": ("s", "F9")},
                )
            ],
        )
    }
    assert _bound_shortcut_ids(results) == {"toggle_draw"}
    assert _bound_shortcut_ids({}) == set()


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


def test_shell_adapter_exposes_global_fallback_state(tmp_path) -> None:
    controller = _controller(tmp_path)
    backend = _FakeBackend()
    service = GlobalShortcutService(controller, backend=backend)
    adapter = ShellAdapter(_FakeCoordinator(), service)
    changes: list[bool] = []
    adapter.globalDrawingShortcutsActiveChanged.connect(
        lambda: changes.append(adapter.globalDrawingShortcutsActive)
    )

    assert adapter.globalDrawingShortcutsActive is False
    backend.registrationFinished.emit(True, "")
    assert adapter.globalDrawingShortcutsActive is True
    assert changes == [True]
    event_bus.clear()


def test_portal_backend_isolated_from_qtdbus_and_gui_blocking() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "ui"
        / "native"
        / "global_shortcuts.py"
    ).read_text(encoding="utf-8")
    assert "PySide6.QtDBus" not in source
    assert "waitForFinished(" not in source
    assert "BlockWithGui" not in source
    assert "threading.Thread(" in source


def test_qml_disables_exactly_five_local_drawing_shortcuts() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "ui"
        / "qml"
        / "MagicScribe"
        / "ControlPanel.qml"
    ).read_text(encoding="utf-8")
    guard = "enabled: !root.shellAdapter.globalDrawingShortcutsActive"
    assert source.count(guard) == 5
    assert "sequence: root.shellAdapter.minimizeShortcut\n        context: Qt.WindowShortcut\n        onActivated:" in source
    assert "sequence: root.shellAdapter.quitShortcut\n        context: Qt.WindowShortcut\n        onActivated:" in source


def test_main_wires_global_shortcuts_without_dbus_policy() -> None:
    source = (Path(__file__).resolve().parents[2] / "main.py").read_text(
        encoding="utf-8"
    )
    assert "GlobalShortcutService(controller)" in source
    assert "global_shortcuts.start(_portal_parent_window(control_window))" in source
    assert "global_shortcuts.shutdown()" in source
    assert "QDBus" not in source
