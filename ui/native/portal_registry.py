"""XDG host-app registration for portal attribution.

The registry is best-effort: xdg-desktop-portal documents this host interface
as transitional, so absence or rejection must not prevent portal fallback.
"""

from __future__ import annotations

import logging
from typing import Any

from jeepney import DBusAddress, HeaderFields, MessageType, new_method_call

from config.constants import AppMeta

logger = logging.getLogger(__name__)

PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
_REGISTRY_IFACE = "org.freedesktop.host.portal.Registry"
APP_ID = AppMeta.ORG_NAME  # deve coincidere con il nome del file .desktop

_REGISTRY_ADDRESS = DBusAddress(
    PORTAL_PATH,
    bus_name=PORTAL_SERVICE,
    interface=_REGISTRY_IFACE,
)


def register_message(app_id: str = APP_ID):
    """Build ``Registry.Register(s, a{sv})`` for the current D-Bus peer."""
    return new_method_call(
        _REGISTRY_ADDRESS,
        "Register",
        "sa{sv}",
        (app_id, {}),
    )


def dbus_error_message(reply: Any) -> str | None:
    """Descrive una reply D-Bus di errore, oppure None se non e' un errore."""
    if reply.header.message_type != MessageType.error:
        return None
    error_name = reply.header.fields.get(HeaderFields.error_name, "D-Bus error")
    details = ": ".join(str(part) for part in reply.body if part)
    return f"{error_name}: {details}" if details else str(error_name)


def register_host_app(connection: Any, *, timeout: float) -> bool:
    """Associate this peer with ``magicscribe.desktop`` before portal calls.

    Failure is intentionally non-fatal because the host Registry interface is
    documented as transitional and may disappear in a future portal release.
    """
    try:
        reply = connection.send_and_get_reply(
            register_message(),
            timeout=timeout,
        )
    except Exception as exc:
        logger.debug("XDG host Registry non disponibile: %s", exc)
        return False

    error = dbus_error_message(reply)
    if error is not None:
        logger.debug("XDG host Registry non applicata: %s", error)
        return False

    logger.info("Peer portal registrato con app-id %s", APP_ID)
    return True
