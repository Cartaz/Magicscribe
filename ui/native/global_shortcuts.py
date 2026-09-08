"""Scorciatoie globali tramite XDG Desktop Portal.

QtDBus resta confinato in questo modulo. Il core possiede le azioni; questo
servizio possiede soltanto registrazione, dispatch nativo e lifecycle delle
scorciatoie globali. Le chiamate al portal non bloccano il GUI thread.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import secrets
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot, SLOT
from PySide6.QtDBus import (
    QDBus,
    QDBusConnection,
    QDBusInterface,
    QDBusObjectPath,
    QDBusPendingCallWatcher,
    QDBusVariant,
)

from config.constants import HotkeyDefaults
from core.app_controller import AppController

logger = logging.getLogger(__name__)

_PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
_PORTAL_PATH = "/org/freedesktop/portal/desktop"
_GLOBAL_SHORTCUTS_IFACE = "org.freedesktop.portal.GlobalShortcuts"
_REQUEST_IFACE = "org.freedesktop.portal.Request"
_SESSION_IFACE = "org.freedesktop.portal.Session"

_CREATE_RESPONSE_SLOT = "_on_create_response(uint,QVariantMap)"
_BIND_RESPONSE_SLOT = "_on_bind_response(uint,QVariantMap)"
_ACTIVATED_SLOT = "_on_activated(QDBusObjectPath,QString,qulonglong,QVariantMap)"


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


def _object_path_text(value: Any) -> str:
    if isinstance(value, QDBusVariant):
        value = value.variant()
    if isinstance(value, QDBusObjectPath):
        return value.path()
    return str(value)


def _unwrap_variant(value: Any) -> Any:
    return value.variant() if isinstance(value, QDBusVariant) else value


def _new_token(prefix: str) -> str:
    # Solo caratteri validi per un elemento di object path D-Bus.
    return f"magicscribe_{prefix}_{secrets.token_hex(8)}"


def _create_session_options(handle_token: str, session_token: str) -> dict[str, str]:
    """Build the GlobalShortcuts CreateSession vardict with scalar values.

    A Python mapping passed as a QVariantMap is already marshalled by Qt as
    ``a{sv}``. Wrapping the values in QDBusVariant here would create a nested
    variant and the portal would see type ``v`` where the key contract expects
    the contained string type ``s``.
    """
    return {
        "handle_token": handle_token,
        "session_handle_token": session_token,
    }


def _shortcut_payload(
    shortcuts: tuple[ShortcutSpec, ...],
) -> list[tuple[str, dict[str, str]]]:
    """Build the ``a(sa{sv})`` shortcut payload using plain scalar values."""
    return [
        (
            spec.shortcut_id,
            {
                "description": spec.description,
                "preferred_trigger": spec.preferred_trigger,
            },
        )
        for spec in shortcuts
    ]


def _request_options(handle_token: str) -> dict[str, str]:
    return {"handle_token": handle_token}


class PortalGlobalShortcutBackend(QObject):
    """Backend QtDBus asincrono per org.freedesktop.portal.GlobalShortcuts."""

    activated = Signal(str)
    registrationFinished = Signal(bool, str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        bus: QDBusConnection | None = None,
    ) -> None:
        super().__init__(parent)
        self._bus = bus or QDBusConnection.sessionBus()
        self._portal: QDBusInterface | None = None
        self._session_handle = ""
        self._shortcuts: tuple[ShortcutSpec, ...] = ()
        self._requested_ids: set[str] = set()
        self._watchers: list[QDBusPendingCallWatcher] = []
        self._watcher_metadata: dict[int, tuple[str, str, str]] = {}
        self._response_connections: list[tuple[str, str]] = []
        self._activated_connected = False
        self._started = False
        self._finished = False
        self._parent_window = ""

    def start(
        self,
        shortcuts: tuple[ShortcutSpec, ...],
        parent_window: str = "",
    ) -> None:
        """Avvia CreateSession -> BindShortcuts senza bloccare il GUI thread."""
        if self._started:
            return
        self._started = True
        self._parent_window = parent_window
        self._shortcuts = shortcuts
        self._requested_ids = {shortcut.shortcut_id for shortcut in shortcuts}

        if not self._bus.isConnected():
            self._finish(False, "D-Bus session bus non disponibile")
            return

        self._portal = QDBusInterface(
            _PORTAL_SERVICE,
            _PORTAL_PATH,
            _GLOBAL_SHORTCUTS_IFACE,
            self._bus,
            self,
        )
        if not self._portal.isValid():
            self._finish(False, "XDG GlobalShortcuts portal non disponibile")
            return

        self._activated_connected = self._bus.connect(
            _PORTAL_SERVICE,
            _PORTAL_PATH,
            _GLOBAL_SHORTCUTS_IFACE,
            "Activated",
            self,
            SLOT(_ACTIVATED_SLOT),
        )
        if not self._activated_connected:
            self._finish(False, "Impossibile sottoscrivere GlobalShortcuts.Activated")
            return

        handle_token = _new_token("create")
        session_token = _new_token("session")
        request_path = _request_path(self._bus.baseService(), handle_token)
        if not self._connect_response(request_path, _CREATE_RESPONSE_SLOT):
            self._finish(False, "Impossibile sottoscrivere la risposta CreateSession")
            return

        options = _create_session_options(handle_token, session_token)
        pending = self._portal.asyncCallWithArgumentList("CreateSession", [options])
        self._watch_method_reply(
            pending,
            method_name="CreateSession",
            expected_path=request_path,
            response_slot=_CREATE_RESPONSE_SLOT,
        )

    def shutdown(self) -> None:
        """Chiude deterministicamente la sessione e scollega i segnali."""
        self._disconnect_all_responses()
        self._disconnect_activated()
        if self._session_handle and self._bus.isConnected():
            session = QDBusInterface(
                _PORTAL_SERVICE,
                self._session_handle,
                _SESSION_IFACE,
                self._bus,
                self,
            )
            if session.isValid():
                session.call(QDBus.CallMode.NoBlock, "Close")
        self._session_handle = ""

    def _connect_response(self, path: str, slot_signature: str) -> bool:
        connected = self._bus.connect(
            _PORTAL_SERVICE,
            path,
            _REQUEST_IFACE,
            "Response",
            self,
            SLOT(slot_signature),
        )
        if connected:
            self._response_connections.append((path, slot_signature))
        return connected

    def _disconnect_response(self, path: str, slot_signature: str) -> None:
        self._bus.disconnect(
            _PORTAL_SERVICE,
            path,
            _REQUEST_IFACE,
            "Response",
            self,
            SLOT(slot_signature),
        )
        try:
            self._response_connections.remove((path, slot_signature))
        except ValueError:
            pass

    def _disconnect_all_responses(self) -> None:
        for path, slot_signature in list(self._response_connections):
            self._disconnect_response(path, slot_signature)

    def _disconnect_activated(self) -> None:
        if not self._activated_connected:
            return
        self._bus.disconnect(
            _PORTAL_SERVICE,
            _PORTAL_PATH,
            _GLOBAL_SHORTCUTS_IFACE,
            "Activated",
            self,
            SLOT(_ACTIVATED_SLOT),
        )
        self._activated_connected = False

    def _watch_method_reply(
        self,
        pending,
        *,
        method_name: str,
        expected_path: str,
        response_slot: str,
    ) -> None:
        watcher = QDBusPendingCallWatcher(pending, self)
        self._watchers.append(watcher)
        self._watcher_metadata[id(watcher)] = (
            method_name,
            expected_path,
            response_slot,
        )
        watcher.finished.connect(self._on_method_reply_finished)

    def _on_method_reply_finished(self, watcher: QDBusPendingCallWatcher) -> None:
        method_name, expected_path, response_slot = self._watcher_metadata.pop(
            id(watcher),
            ("portal call", "", ""),
        )
        try:
            if watcher.isError():
                error = watcher.error()
                self._finish(
                    False,
                    f"{method_name} fallita: {error.name()}: {error.message()}",
                )
                return

            arguments = watcher.reply().arguments()
            if not arguments:
                self._finish(False, f"{method_name} non ha restituito un request handle")
                return

            returned_path = _object_path_text(arguments[0])
            if returned_path and returned_path != expected_path and response_slot:
                # Compatibilita' con portal precedenti alla convenzione TOKEN.
                self._disconnect_response(expected_path, response_slot)
                if not self._connect_response(returned_path, response_slot):
                    self._finish(
                        False,
                        f"Impossibile seguire il request handle di {method_name}",
                    )
        finally:
            try:
                self._watchers.remove(watcher)
            except ValueError:
                pass
            watcher.deleteLater()

    @Slot("uint", "QVariantMap")
    def _on_create_response(self, response: int, results: dict) -> None:
        self._disconnect_response_for_slot(_CREATE_RESPONSE_SLOT)
        if response != 0:
            message = (
                "Registrazione scorciatoie annullata dall'utente"
                if response == 1
                else "CreateSession terminata senza successo"
            )
            self._finish(False, message)
            return

        session_value = _unwrap_variant(results.get("session_handle", ""))
        self._session_handle = _object_path_text(session_value)
        if not self._session_handle.startswith("/"):
            self._finish(False, "CreateSession non ha restituito una sessione valida")
            return
        self._bind_shortcuts()

    def _bind_shortcuts(self) -> None:
        portal = self._portal
        if portal is None or not self._session_handle:
            self._finish(False, "Sessione GlobalShortcuts non inizializzata")
            return

        handle_token = _new_token("bind")
        request_path = _request_path(self._bus.baseService(), handle_token)
        if not self._connect_response(request_path, _BIND_RESPONSE_SLOT):
            self._finish(False, "Impossibile sottoscrivere la risposta BindShortcuts")
            return

        shortcut_payload = _shortcut_payload(self._shortcuts)
        options = _request_options(handle_token)
        pending = portal.asyncCallWithArgumentList(
            "BindShortcuts",
            [
                QDBusObjectPath(self._session_handle),
                shortcut_payload,
                self._parent_window,
                options,
            ],
        )
        self._watch_method_reply(
            pending,
            method_name="BindShortcuts",
            expected_path=request_path,
            response_slot=_BIND_RESPONSE_SLOT,
        )

    @Slot("uint", "QVariantMap")
    def _on_bind_response(self, response: int, results: dict) -> None:
        self._disconnect_response_for_slot(_BIND_RESPONSE_SLOT)
        if response != 0:
            message = (
                "Configurazione scorciatoie annullata dall'utente"
                if response == 1
                else "BindShortcuts terminata senza successo"
            )
            self._finish(False, message)
            return

        raw_shortcuts = _unwrap_variant(results.get("shortcuts", []))
        bound_ids: set[str] = set()
        try:
            for item in raw_shortcuts:
                if isinstance(item, (tuple, list)) and item:
                    bound_ids.add(str(_unwrap_variant(item[0])))
        except TypeError:
            logger.warning("Risposta BindShortcuts non iterabile: %r", raw_shortcuts)

        # O tutte le scorciatoie richieste sono globali, oppure il fallback
        # locale resta integralmente attivo. Evita doppi trigger e buchi.
        if bound_ids != self._requested_ids:
            self._finish(
                False,
                "Il portal non ha registrato tutte le scorciatoie richieste",
            )
            return
        self._finish(True, "")

    def _disconnect_response_for_slot(self, slot_signature: str) -> None:
        connection = next(
            (
                entry
                for entry in self._response_connections
                if entry[1] == slot_signature
            ),
            None,
        )
        if connection is not None:
            self._disconnect_response(*connection)

    @Slot("QDBusObjectPath", str, "qulonglong", "QVariantMap")
    def _on_activated(
        self,
        session_handle: QDBusObjectPath,
        shortcut_id: str,
        _timestamp: int,
        _options: dict,
    ) -> None:
        if _object_path_text(session_handle) != self._session_handle:
            return
        if shortcut_id in self._requested_ids:
            self.activated.emit(shortcut_id)

    def _finish(self, success: bool, message: str) -> None:
        if self._finished:
            return
        self._finished = True
        if success:
            logger.info("Global shortcuts registrate tramite XDG Desktop Portal")
        else:
            logger.warning("Global shortcuts non attive: %s", message)
            self.shutdown()
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
