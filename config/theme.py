"""Definizione centralizzata dei token di colore Breeze Dark.

Tutti i componenti UI devono referenziare i colori tramite ThemeColors,
mai usare valori hex hardcoded. Il tema e' esclusivamente Breeze Dark.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _ThemeColors:
    """Token di colore semantici per il tema Breeze Dark KDE Plasma.

    I nomi dei token esprimono il ruolo semantico, non il valore cromatico.
    """

    # ── Accento primario (Teal) ──────────────────────────────────────────
    PRIMARY: str = "#00bfa5"
    PRIMARY_DARK: str = "#00695c"
    PRIMARY_PRESSED: str = "#004d40"
    PRIMARY_HOVER: str = "#00d6b8"

    # ── Azioni distruttive (Arancione) ───────────────────────────────────
    DANGER: str = "#db4105"
    DANGER_DARK: str = "#7a2400"
    DANGER_PRESSED: str = "#5c1a00"

    # ── Successo / Stato attivo ──────────────────────────────────────────
    SUCCESS: str = "#27ae60"

    # ── Sfondi ───────────────────────────────────────────────────────────
    BG_MAIN: str = "#1b1e20"
    BG_CARD: str = "#232629"
    BG_SURFACE: str = "#2a2e32"
    BG_SURFACE_HOVER: str = "#31363b"
    BG_TOOLTIP: str = "#2a2e32"

    # ── Bordi ────────────────────────────────────────────────────────────
    BORDER: str = "#3f4347"
    BORDER_ACTIVE: str = "#00bfa5"

    # ── Testo ────────────────────────────────────────────────────────────
    TEXT_PRIMARY: str = "#eff0f1"
    TEXT_SECONDARY: str = "#a0a4a8"
    TEXT_DIM: str = "#7f8c8d"
    TEXT_DISABLED: str = "#6b7076"

    # ── Badge scorciatoia ────────────────────────────────────────────────
    SHORTCUT_BG: str = "rgba(255, 255, 255, 0.08)"
    SHORTCUT_BORDER: str = "#3f4347"

    # ── Overlay ──────────────────────────────────────────────────────────
    OVERLAY_GRID: str = "rgba(255, 255, 255, 0.05)"

    # ── Selezione ────────────────────────────────────────────────────────
    SELECTION_BG: str = "#00695c"
    SELECTION_TEXT: str = "#ffffff"


# Istanza singleton immutabile
ThemeColors = _ThemeColors()
