"""Event bus centrale per la comunicazione tra moduli.

Implementa il pattern Observer con eventi tipizzati.
I moduli si iscrivono a eventi per nome e ricevono callback
quando l'evento viene emesso.

Nota: questo modulo NON importa mai Qt (§5.1.4b). Per la
comunicazione thread-safe verso il livello UI, usare
ui/event_bridge.py che marshalla le chiamate sul thread Qt.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Tipo handler: funzione che riceve kwargs arbitrari
EventHandler = Callable[..., None]


class EventBus:
    """Canale di comunicazione asincrona tra moduli.

    Gli handler vengono eseguiti sincronamente nel thread
    dell'emittente. Operazioni lunghe devono essere delegate
    a worker thread.

    Attributes:
        _handlers: mappa nome_evento -> lista di handler.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event: str, handler: EventHandler) -> None:
        """Registra un handler per un tipo di evento.

        Args:
            event: nome dell'evento (es. 'drawing_toggled').
            handler: callback invocato quando l'evento viene emesso.
        """
        if handler not in self._handlers[event]:
            self._handlers[event].append(handler)
            logger.debug(
                "Iscritto handler %s all'evento '%s'",
                handler.__name__, event,
            )

    def unsubscribe(self, event: str, handler: EventHandler) -> None:
        """Deregistra un handler da un tipo di evento.

        Args:
            event: nome dell'evento.
            handler: handler da rimuovere.
        """
        if handler in self._handlers.get(event, []):
            self._handlers[event].remove(handler)
            logger.debug(
                "Rimosso handler %s dall'evento '%s'",
                handler.__name__, event,
            )

    def emit(self, event: str, **kwargs: Any) -> None:
        """Emette un evento, invocando tutti gli handler iscritti.

        Args:
            event: nome dell'evento.
            **kwargs: dati associati all'evento.
        """
        handlers = self._handlers.get(event, [])
        if not handlers:
            logger.debug("Evento '%s' emesso senza handler iscritti", event)
            return
        for handler in handlers:
            try:
                handler(**kwargs)
            except Exception:
                logger.exception(
                    "Errore nell'handler %s per l'evento '%s'",
                    handler.__name__, event,
                )

    def clear(self) -> None:
        """Rimuove tutti gli handler da tutti gli eventi."""
        self._handlers.clear()


# Istanza singleton globale
event_bus = EventBus()
