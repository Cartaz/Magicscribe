"""Behavioral tests for the XDG portal D-Bus worker, using a scripted bus."""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
import time
from typing import Any, Callable

from jeepney import HeaderFields, MessageType
from PySide6.QtWidgets import QApplication

import ui.native.global_shortcuts as global_shortcuts
from ui.native.global_shortcuts import PortalGlobalShortcutBackend, ShortcutSpec

_APP = QApplication.instance() or QApplication([])
_SESSION = "/org/freedesktop/portal/desktop/session/1_42/magicscribe"
_SHORTCUTS = (
    ShortcutSpec("toggle_draw", "Toggle drawing", "F9"),
    ShortcutSpec("undo", "Undo", "F8"),
)


@dataclass
class _Header:
    message_type: MessageType
    fields: dict[HeaderFields, Any] = field(default_factory=dict)


@dataclass
class _Message:
    header: _Header
    body: tuple[Any, ...] = ()


def _reply(*body: Any) -> _Message:
    return _Message(_Header(MessageType.method_return), body)


def _signal(path: str, *body: Any) -> _Message:
    return _Message(_Header(MessageType.signal, {HeaderFields.path: path}), body)


class _ScriptedBus:
    """Minimal jeepney blocking connection driven by per-method responses."""

    unique_name = ":1.42"

    def __init__(self, create_response: int = 0, bind_ids: tuple[str, ...] | None = None):
        self.calls: list[str] = []
        self.sent: list[tuple[str, str]] = []
        self.closed = False
        self._create_response = create_response
        self._bind_ids = bind_ids if bind_ids is not None else tuple(
            spec.shortcut_id for spec in _SHORTCUTS
        )
        self._queues: list[deque] = []
        self._pending: deque[Callable[[], None]] = deque()

    @contextmanager
    def filter(self, _rule, bufsize: int):
        queue: deque = deque(maxlen=bufsize)
        self._queues.append(queue)
        yield queue

    @property
    def _responses(self) -> deque:
        return self._queues[0]

    @property
    def _activations(self) -> deque:
        return self._queues[1]

    def send_and_get_reply(self, message, timeout: float) -> _Message:
        member = message.header.fields[HeaderFields.member]
        self.calls.append(member)
        if member == "CreateSession":
            path = "/org/freedesktop/portal/desktop/request/1_42/create"
            results = {"session_handle": ("o", _SESSION)}
            self._pending.append(
                lambda: self._responses.append(_signal(path, self._create_response, results))
            )
            return _reply(path)
        if member == "BindShortcuts":
            path = "/org/freedesktop/portal/desktop/request/1_42/bind"
            bound = [(shortcut_id, {}) for shortcut_id in self._bind_ids]
            results = {"shortcuts": ("a(sa{sv})", bound)}
            self._pending.append(lambda: self._responses.append(_signal(path, 0, results)))
            self._pending.append(
                lambda: self._activations.append(
                    _signal(global_shortcuts._PORTAL_PATH, _SESSION, "toggle_draw", 0, {})
                )
            )
            return _reply(path)
        return _reply()

    def recv_messages(self, timeout: float) -> None:
        if self._pending:
            self._pending.popleft()()
            return
        time.sleep(min(timeout, 0.01))
        raise TimeoutError

    def send(self, message) -> None:
        self.sent.append(
            (message.header.fields[HeaderFields.member], message.header.fields[HeaderFields.path])
        )

    def close(self) -> None:
        self.closed = True


def _run_backend(monkeypatch, bus: _ScriptedBus, until: Callable[[list, list], bool]):
    monkeypatch.setattr(global_shortcuts, "open_dbus_connection", lambda **_kwargs: bus)
    backend = PortalGlobalShortcutBackend()
    finished: list[tuple[bool, str]] = []
    activated: list[str] = []
    backend.registrationFinished.connect(lambda ok, message: finished.append((ok, message)))
    backend.activated.connect(activated.append)
    backend.start(_SHORTCUTS)
    deadline = time.monotonic() + 5.0
    try:
        while not until(finished, activated) and time.monotonic() < deadline:
            _APP.processEvents()
            time.sleep(0.01)
    finally:
        backend.shutdown()
        _APP.processEvents()
    return finished, activated


def test_worker_registers_binds_dispatches_and_closes_session(monkeypatch) -> None:
    bus = _ScriptedBus()
    finished, activated = _run_backend(
        monkeypatch, bus, lambda finished, activated: bool(finished and activated)
    )

    assert finished == [(True, "")]
    assert activated == ["toggle_draw"]
    # The host Registry must run on the same peer before any portal method.
    assert bus.calls == ["Register", "AddMatch", "AddMatch", "CreateSession", "BindShortcuts"]
    assert bus.sent == [("Close", _SESSION)]
    assert bus.closed is True


def test_worker_reports_user_cancellation(monkeypatch) -> None:
    bus = _ScriptedBus(create_response=1)
    finished, activated = _run_backend(monkeypatch, bus, lambda finished, _: bool(finished))

    assert len(finished) == 1
    ok, message = finished[0]
    assert ok is False
    assert "annullata" in message
    assert activated == []
    assert "BindShortcuts" not in bus.calls
    assert bus.closed is True


def test_worker_fails_closed_when_portal_binds_a_subset(monkeypatch) -> None:
    bus = _ScriptedBus(bind_ids=("toggle_draw",))
    finished, activated = _run_backend(monkeypatch, bus, lambda finished, _: bool(finished))

    assert finished and finished[0][0] is False
    assert activated == []
    assert bus.sent == [("Close", _SESSION)]
