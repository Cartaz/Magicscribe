"""Bridge thread-safe tra event bus e thread Qt.

Quando un evento viene emesso da un thread worker, il callback
viene schedulato sul thread Qt principale tramite
QTimer.singleShot(0, ...). Questo e' il pattern corretto
per invocazioni thread-safe sul thread Qt (§5.1.10).

Il modulo core/event_bus.py NON importa Qt (§5.1.4b);
questo bridge risiede nel livello UI per fornire
la marshalling delle chiamate.
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QTimer
from core.event_bus import EventBus, event_bus

import logging

logger = logging.getLogger(__name__)


class EventBridge:
    """Iscrive handler Qt-safe agli eventi del bus.

    Quando un evento viene emesso da un thread worker,
    il callback viene schedulato sul thread Qt principale
    tramite QTimer.singleShot(0, ...).
    """

    @staticmethod
    def subscribe(event_name: str, callback: Callable) -> None:
        """Iscrive un callback Qt-safe a un evento del bus.

        Il callback verra' invocato sul thread Qt principale,
        indipendentemente dal thread che emette l'evento.

        Args:
            event_name: nome dell'evento.
            callback: funzione da invocare sul thread Qt.
        """
        def _wrapper(**kwargs) -> None:
            QTimer.singleShot(0, lambda: callback(**kwargs))

        event_bus.subscribe(event_name, _wrapper)
        logger.debug(
            "EventBridge: iscritto callback Qt-safe per '%s'",
            event_name,
        )

    @staticmethod
    def subscribe_on(
        bus: EventBus, event_name: str, callback: Callable,
    ) -> None:
        """Iscrive un callback Qt-safe a un evento di un bus specifico.

        Args:
            bus: istanza EventBus su cui iscriversi.
            event_name: nome dell'evento.
            callback: funzione da invocare sul thread Qt.
        """
        def _wrapper(**kwargs) -> None:
            QTimer.singleShot(0, lambda: callback(**kwargs))

        bus.subscribe(event_name, _wrapper)
