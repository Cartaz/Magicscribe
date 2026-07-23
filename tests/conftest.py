"""Fixture condivise per i test di MagicScribe."""

import pytest

from core.event_bus import EventBus


@pytest.fixture
def fresh_event_bus() -> EventBus:
    """Crea un nuovo event bus pulito per ogni test."""
    return EventBus()
