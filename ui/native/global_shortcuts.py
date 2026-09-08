"""Scorciatoie globali tramite XDG Desktop Portal.

Il core possiede le azioni. Questo modulo possiede soltanto registrazione,
dispatch nativo e lifecycle delle scorciatoie globali. Il protocollo D-Bus
viene eseguito in un worker dedicato, quindi il GUI thread non viene bloccato.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import logging
import secrets
import threading
from typing import Any

from PySide6.QtCore import QObject, Signal
from jeepney import (
    DBusAddress,
    HeaderFields,
    MatchRule,
    MessageType,
    message_bus,
    new_method_call,
)
from jeepney.io.blocking import open_dbus_connection

from config.constants import HotkeyDefaults
from core.app_controller import AppController
from ui.native.portal_registry import register_host_app

logger = logging.getLogger(__name__)

_PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
_PORTAL_PATH = "/org/freedesktop/portal/desktop"
_GLOBAL_SHORTCUTS_IFACE = "org.freedesktop.portal.GlobalShortcuts"
_REQUEST_IFACE = "org.freedesktop.portal.Request"
_SESSION_IFACE = "org.freedesktop.portal.Session"
_METHOD_REPLY_TIMEOUT = 5.0
_RECEIVE_POLL_SECONDS = 0.2

_PORTAL_ADDRESS = DBusAddress(
    _PORTAL_PATH,
    bus_name=_PORTAL_SERVICE,
    interface=_GLOBAL_SHORTCUTS_IFACE,
)


@dataclass(frozen=True, slots=True)
class ShortcutSpec:
    """Descrizione stabile di una scorciatoia richiesta al portal."""

    shortcut_id: str
    description: str
    preferred_trigger: str


def _qt_to_xdg_trigger(sequence: str) -> str:
    """Converte le sequenze Qt del progetto nel formato XDG shortcuts."""
    aliases = {
        "ctrl": "CTRL",
        "control": "CTRL",
        "alt": "ALT",
        "shift": "SHIFT",
        "meta": "LOGO",
        "super": "LOGO",
    }
    parts = [part.strip() for part in sequence.split("+") if part.strip()]
    return "+".join(aliases.get(part.lower(), part) for part in parts)


def _sender_segment(base_service: str) -> str:
    """Normalizza il unique bus name secondo la convenzione XDG Request."""
    return base_service.removeprefix(":").replace(".", "_")


def _request_path(base_service: str, token: str) -> str:
    return (
        "/org/freedesktop/portal/desktop/request/"
        f"{_sender_segment(base_service)}/{token}"
    )


def _new_token(prefix: str) -> str:
    # Solo caratteri validi per un elemento di object path D-Bus.
    return f"magicscribe_{prefix}_{secrets.token_hex(8)}"


def _create_session_options(
    handle_token: str,
    session_token: str,
) -> dict[str, tuple[str, str]]:
    """Vardict D-Bus esplicito per CreateSession."""
    return {
        "handle_token": ("s", handle_token),
        "session_handle_token": ("s", session_token),
    }


def _shortcut_payload(
    shortcuts: tuple[ShortcutSpec, ...],
) -> list[tuple[str, dict[str, tuple[str, str]]]]:
    """Payload ``a(sa{sv})`` senza conversioni implicite Python/Qt."""
    return [
        (
            spec.shortcut_id,
            {
                "description": ("s", spec.description),
                "preferred_trigger": ("s", spec.preferred_trigger),
            },
        )
        for spec in shortcuts
    ]


def _request_options(handle_token: str) -> dict[str, tuple[str, str]]:
    return {"handle_token": ("s", handle_token)}


def _create_session_message(handle_token: str, session_token: str):
    return new_method_call(
        _PORTAL_ADDRESS,
        "CreateSession",
        "a{sv}",
        (_create_session_options(handle_token, session_token),),
    )


def _bind_shortcuts_message(
    session_handle: str,
    shortcuts: tuple[ShortcutSpec, ...],
    parent_window: str,
    handle_token: str,
):
    return new_method_call(
        _PORTAL_ADDRESS,
        "BindShortcuts",
        "oa(sa{sv})sa{sv}",
        (
            session_handle,
            _shortcut_payload(shortcuts),
            parent_window,
            _request_options(handle_token),
        ),
    )


def _message_path(message) -> str:
    return str(message.header.fields.get(HeaderFields.path, ""))


def _reply_body(reply, method_name: str) -> tuple[Any, ...]:
    if reply.header.message_type == MessageType.error:
        error_name = reply.header.fields.get(HeaderFields.error_name, "D-Bus error")
        details = ": ".join(str(part) for part in reply.body if part)
        suffix = f": {details}" if details else ""
        raise RuntimeError(f"{method_name} fallita: {error_name}{suffix}")
    return reply.body


def _variant_value(value: Any) -> Any:
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        return value[1]
    return value


def _bound_shortcut_ids(results: dict[str, Any]) -> set[str]:
    raw_shortcuts = _variant_value(results.get("shortcuts", ("a(sa{sv})", [])))
    bound: set[str] = set()
    if not isinstance(raw_shortcuts, list):
        return bound
    for item in raw_shortcuts:
        if isinstance(item, tuple) and item:
            bound.add(str(item[0]))
    return bound


class PortalGlobalShortcutBackend(QObject):
    """Backend XDG Portal con D-Bus esplicito in un worker dedicato."""

    activated = Signal(str)
    registrationFinished = Signal(bool, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._shortcuts: tuple[ShortcutSpec, ...] = ()
        self._requested_ids: set[str] = set()
        self._parent_window = ""
        self._session_handle = ""
        self._started = False
        self._finished = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(
        self,
        shortcuts: tuple[ShortcutSpec, ...],
        parent_window: str = "",
    ) -> None:
        """Avvia CreateSession -> BindShortcuts senza bloccare il GUI thread."""
        if self._started:
            return
        self._started = True
        self._shortcuts = shortcuts
        self._requested_ids = {shortcut.shortcut_id for shortcut in shortcuts}
        self._parent_window = parent_window
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="magicscribe-global-shortcuts",
            daemon=False,
        )
        self._thread.start()

    def shutdown(self) -> None:
        """Richiede stop e attende il worker dopo la chiusura dell'event loop Qt."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=_METHOD_REPLY_TIMEOUT + 1.0)
            if thread.is_alive():
                logger.warning("Worker GlobalShortcuts non terminato entro il timeout")
        self._thread = None
        self._session_handle = ""

    def _run(self) -> None:
        response_rule = MatchRule(
            type="signal",
            interface=_REQUEST_IFACE,
            member="Response",
            path_namespace="/org/freedesktop/portal/desktop/request",
        )
        activated_rule = MatchRule(
            type="signal",
            interface=_GLOBAL_SHORTCUTS_IFACE,
            member="Activated",
            path=_PORTAL_PATH,
        )

        connection = None
        try:
            connection = open_dbus_connection(bus="SESSION")
            # Host apps launched from a terminal can otherwise inherit the
            # terminal's app-id (observed as org.kde.konsole on KDE). The XDG
            # Registry must be called on this same peer before portal methods.
            register_host_app(connection, timeout=_METHOD_REPLY_TIMEOUT)
            with (
                connection.filter(response_rule, bufsize=16) as responses,
                connection.filter(activated_rule, bufsize=32) as activations,
            ):
                _reply_body(
                    connection.send_and_get_reply(
                        message_bus.AddMatch(response_rule),
                        timeout=_METHOD_REPLY_TIMEOUT,
                    ),
                    "AddMatch(Request.Response)",
                )
                _reply_body(
                    connection.send_and_get_reply(
                        message_bus.AddMatch(activated_rule),
                        timeout=_METHOD_REPLY_TIMEOUT,
                    ),
                    "AddMatch(GlobalShortcuts.Activated)",
                )

                self._create_and_bind_session(connection, responses)
                if self._finished:
                    return
                self._finish(True, "")
                self._activation_loop(connection, activations)
        except Exception as exc:
            if not self._stop_event.is_set():
                self._finish(False, str(exc))
        finally:
            if connection is not None:
                self._close_session(connection)
                connection.close()

    def _create_and_bind_session(self, connection, responses: deque) -> None:
        create_token = _new_token("create")
        session_token = _new_token("session")
        expected_create_path = _request_path(connection.unique_name, create_token)
        create_reply = _reply_body(
            connection.send_and_get_reply(
                _create_session_message(create_token, session_token),
                timeout=_METHOD_REPLY_TIMEOUT,
            ),
            "CreateSession",
        )
        if not create_reply:
            raise RuntimeError("CreateSession non ha restituito un request handle")
        create_path = str(create_reply[0]) or expected_create_path
        response, results = self._wait_for_response(connection, responses, create_path)
        if response != 0:
            if response == 1:
                raise RuntimeError("Registrazione scorciatoie annullata dall'utente")
            raise RuntimeError("CreateSession terminata senza successo")

        self._session_handle = str(_variant_value(results.get("session_handle", "")))
        if not self._session_handle.startswith("/"):
            raise RuntimeError("CreateSession non ha restituito una sessione valida")

        bind_token = _new_token("bind")
        expected_bind_path = _request_path(connection.unique_name, bind_token)
        bind_reply = _reply_body(
            connection.send_and_get_reply(
                _bind_shortcuts_message(
                    self._session_handle,
                    self._shortcuts,
                    self._parent_window,
                    bind_token,
                ),
                timeout=_METHOD_REPLY_TIMEOUT,
            ),
            "BindShortcuts",
        )
        if not bind_reply:
            raise RuntimeError("BindShortcuts non ha restituito un request handle")
        bind_path = str(bind_reply[0]) or expected_bind_path
        response, results = self._wait_for_response(connection, responses, bind_path)
        if response != 0:
            if response == 1:
                raise RuntimeError("Configurazione scorciatoie annullata dall'utente")
            raise RuntimeError("BindShortcuts terminata senza successo")

        if _bound_shortcut_ids(results) != self._requested_ids:
            raise RuntimeError("Il portal non ha registrato tutte le scorciatoie richieste")

    def _wait_for_response(
        self,
        connection,
        responses: deque,
        request_path: str,
    ) -> tuple[int, dict[str, Any]]:
        while not self._stop_event.is_set():
            while responses:
                message = responses.popleft()
                if _message_path(message) != request_path:
                    continue
                if len(message.body) < 2:
                    raise RuntimeError("Risposta portal incompleta")
                return int(message.body[0]), dict(message.body[1])
            try:
                connection.recv_messages(timeout=_RECEIVE_POLL_SECONDS)
            except TimeoutError:
                continue
        raise RuntimeError("Registrazione GlobalShortcuts interrotta")

    def _activation_loop(self, connection, activations: deque) -> None:
        while not self._stop_event.is_set():
            while activations:
                message = activations.popleft()
                if len(message.body) < 2:
                    continue
                session_handle = str(message.body[0])
                shortcut_id = str(message.body[1])
                if (
                    session_handle == self._session_handle
                    and shortcut_id in self._requested_ids
                ):
                    self.activated.emit(shortcut_id)
            try:
                connection.recv_messages(timeout=_RECEIVE_POLL_SECONDS)
            except TimeoutError:
                continue

    def _close_session(self, connection) -> None:
        session_handle = self._session_handle
        if not session_handle:
            return
        try:
            address = DBusAddress(
                session_handle,
                bus_name=_PORTAL_SERVICE,
                interface=_SESSION_IFACE,
            )
            connection.send(new_method_call(address, "Close"))
        except Exception as exc:
            logger.debug("Chiusura sessione GlobalShortcuts fallita: %s", exc)
        finally:
            self._session_handle = ""

    def _finish(self, success: bool, message: str) -> None:
        if self._finished:
            return
        self._finished = True
        if success:
            logger.info("Global shortcuts registrate tramite XDG Desktop Portal")
        else:
            logger.warning("Global shortcuts non attive: %s", message)
        self.registrationFinished.emit(success, message)


class GlobalShortcutService(QObject):
    """Coordina il backend nativo e le azioni canoniche dell'AppController."""

    activeChanged = Signal()
    registrationFailed = Signal(str)

    def __init__(
        self,
        controller: AppController,
        parent: QObject | None = None,
        *,
        backend: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._active = False
        self._started = False
        self._backend = backend or PortalGlobalShortcutBackend(self)
        self._actions = {
            "toggle_draw": controller.toggle_drawing,
            "toggle_visibility": controller.toggle_visibility,
            "clear_screen": controller.clear_screen,
            "undo": controller.undo,
            "redo": controller.redo,
        }
        self._shortcuts = (
            ShortcutSpec(
                "toggle_draw",
                "Attiva o disattiva il disegno",
                _qt_to_xdg_trigger(HotkeyDefaults.TOGGLE_DRAW),
            ),
            ShortcutSpec(
                "toggle_visibility",
                "Mostra o nascondi le annotazioni",
                _qt_to_xdg_trigger(HotkeyDefaults.TOGGLE_VISIBILITY),
            ),
            ShortcutSpec(
                "clear_screen",
                "Cancella tutte le annotazioni",
                _qt_to_xdg_trigger(HotkeyDefaults.CLEAR),
            ),
            ShortcutSpec(
                "undo",
                "Annulla l'ultimo tratto",
                _qt_to_xdg_trigger(HotkeyDefaults.UNDO),
            ),
            ShortcutSpec(
                "redo",
                "Ripristina l'ultimo tratto annullato",
                _qt_to_xdg_trigger(HotkeyDefaults.REDO),
            ),
        )
        self._backend.activated.connect(self._on_activated)
        self._backend.registrationFinished.connect(self._on_registration_finished)

    @property
    def active(self) -> bool:
        return self._active

    @property
    def shortcuts(self) -> tuple[ShortcutSpec, ...]:
        return self._shortcuts

    def start(self, parent_window: str = "") -> None:
        if self._started:
            return
        self._started = True
        self._backend.start(self._shortcuts, parent_window)

    def shutdown(self) -> None:
        self._backend.shutdown()
        if self._active:
            self._active = False
            self.activeChanged.emit()

    def _on_registration_finished(self, success: bool, message: str) -> None:
        if self._active != success:
            self._active = success
            self.activeChanged.emit()
        if not success and message:
            self.registrationFailed.emit(message)

    def _on_activated(self, shortcut_id: str) -> None:
        action = self._actions.get(shortcut_id)
        if action is None:
            logger.warning("Shortcut globale sconosciuta: %s", shortcut_id)
            return
        action()
