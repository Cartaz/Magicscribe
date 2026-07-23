"""Test per core.event_bus.EventBus."""

from core.event_bus import EventBus


def test_subscribe_and_emit() -> None:
    """Un handler iscritto deve ricevere l'evento emesso."""
    bus = EventBus()
    received = []
    bus.subscribe("test_event", lambda **kw: received.append(kw))
    bus.emit("test_event", value=42)
    assert received == [{"value": 42}]


def test_multiple_handlers() -> None:
    """Più handler iscritti devono ricevere tutti l'evento."""
    bus = EventBus()
    results = []
    bus.subscribe("evt", lambda **kw: results.append("a"))
    bus.subscribe("evt", lambda **kw: results.append("b"))
    bus.emit("evt")
    assert results == ["a", "b"]


def test_unsubscribe() -> None:
    """Un handler deregistrato non deve ricevere eventi."""
    bus = EventBus()
    received = []
    handler = lambda **kw: received.append(True)
    bus.subscribe("evt", handler)
    bus.unsubscribe("evt", handler)
    bus.emit("evt")
    assert received == []


def test_no_handlers_no_error() -> None:
    """Emit su un evento senza handler non deve sollevare errori."""
    bus = EventBus()
    bus.emit("nonexistent")


def test_handler_exception_logged() -> None:
    """Un'eccezione in un handler non deve bloccare gli altri."""
    bus = EventBus()
    results = []

    def bad_handler(**kw):
        raise RuntimeError("test error")

    bus.subscribe("evt", bad_handler)
    bus.subscribe("evt", lambda **kw: results.append("ok"))
    bus.emit("evt")
    assert results == ["ok"]


def test_clear() -> None:
    """clear() deve rimuovere tutti gli handler."""
    bus = EventBus()
    bus.subscribe("evt", lambda **kw: None)
    bus.clear()
    assert len(bus._handlers) == 0
