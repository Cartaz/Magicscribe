"""XDG host-app registration for portal attribution.

The registry is best-effort: xdg-desktop-portal documents this host interface
as transitional, so absence or rejection must not prevent portal fallback.
"""

from __future__ import annotations

import logging
from typing import Any

from jeepney import DBusAddress, HeaderFields, MessageType, new_method_call

logger = logging.getLogger(__name__)

_PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
_PORTAL_PATH = "/org/freedesktop/portal/desktop"
_REGISTRY_IFACE = "org.freedesktop.host.portal.Registry"
APP_ID = "magicscribe"

_REGISTRY_ADDRESS = DBusAddress(
    _PORTAL_PATH,
    bus_name=_PORTAL_SERVICE,
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


def _error_name(reply: Any) -> str:
    return str(reply.header.fields.get(HeaderFields.error_name, ""))


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

    if reply.header.message_type == MessageType.error:
        details = ": ".join(str(part) for part in reply.body if part)
        suffix = f": {details}" if details else ""
        logger.debug(
            "XDG host Registry non applicata: %s%s",
            _error_name(reply) or "D-Bus error",
            suffix,
        )
        return False

    logger.info("Peer portal registrato con app-id %s", APP_ID)
    return True
