"""Gerarchia delle eccezioni personalizzate di MagicScribe.

Fornisce eccezioni specifiche per i diversi livelli di errore
dell'applicazione, consentendo una gestione granulare.
"""

from __future__ import annotations


class MagicScribeError(Exception):
    """Eccezione base per tutti gli errori di MagicScribe."""


class ConfigError(MagicScribeError):
    """Errore nella configurazione o nelle impostazioni."""


class DrawingError(MagicScribeError):
    """Errore durante un'operazione di disegno."""


class StrokeError(DrawingError):
    """Errore nella gestione dei tratti (undo/redo/clear)."""


class ToolError(DrawingError):
    """Errore nella configurazione o selezione di uno strumento."""
