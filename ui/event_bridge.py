"""Bridge thread-safe tra event bus e thread Qt.

Quando un evento viene emesso da un thread worker, il callback
viene schedulato sul thread Qt principale tramite QTimer.singleShot(0, ...).

Il modulo core/event_bus.py non importa Qt; questo bridge resta nel livello UI
finche' gli adapter QObject della migrazione QML non lo sostituiranno.
"""

from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QTimer

from core.event_bus import EventBus, event_bus

logger = logging.getLogger(__name__)


class EventBridge:
    """Iscrive handler Qt-safe agli eventi del bus."""

    @staticmethod
    def subscribe(event_name: str, callback: Callable) -> None:
        """Iscrive un callback da eseguire sul thread Qt principale."""
        def _wrapper(**kwargs) -> None:
            QTimer.singleShot(0, lambda: callback(**kwargs))

        event_bus.subscribe(event_name, _wrapper)
        logger.debug(
            "EventBridge: iscritto callback Qt-safe per '%s'", event_name,
        )

    @staticmethod
    def subscribe_on(
        bus: EventBus, event_name: str, callback: Callable,
    ) -> None:
        """Iscrive un callback Qt-safe a un bus specifico."""
        def _wrapper(**kwargs) -> None:
            QTimer.singleShot(0, lambda: callback(**kwargs))

        bus.subscribe(event_name, _wrapper)
