"""Tema Breeze Dark completo per MagicScribe.

Genera il foglio di stile QSS completo interpolando i token
di colore da config.theme.ThemeColors. Nessun colore e'
hardcoded (§5.1.5).
"""

from __future__ import annotations

from config.theme import ThemeColors as C


def build_stylesheet() -> str:
    """Genera il foglio di stile QSS completo per Breeze Dark.

    Returns:
        Stringa QSS con tutti gli stili dell'applicazione.
    """
    return f"""
    /* ── Widget base ──────────────────────────────────────────────────── */
    QWidget {{
        background-color: {C.BG_MAIN};
        color: {C.TEXT_PRIMARY};
        font-family: "Noto Sans", "Segoe UI", sans-serif;
        font-size: 10pt;
    }}

    /* ── Card ─────────────────────────────────────────────────────────── */
    QFrame#card {{
        background-color: {C.BG_CARD};
        border: 1px solid {C.BORDER};
        border-radius: 6px;
    }}

    /* ── Pulsanti generici ────────────────────────────────────────────── */
    QPushButton {{
        background-color: {C.BG_SURFACE};
        color: {C.TEXT_PRIMARY};
        border: 1px solid {C.BORDER};
        border-radius: 4px;
        padding: 7px 14px;
        text-align: center;
    }}
    QPushButton:hover {{
        background-color: {C.BG_SURFACE_HOVER};
        border-color: {C.BORDER_ACTIVE};
    }}
    QPushButton:pressed {{
        background-color: {C.PRIMARY_DARK};
        border-color: {C.PRIMARY};
    }}
    QPushButton:disabled {{
        color: {C.TEXT_DISABLED};
        background-color: {C.BG_CARD};
        border-color: {C.BORDER};
    }}

    /* ── Pulsante primario ────────────────────────────────────────────── */
    QPushButton#btn_primary {{
        background-color: {C.PRIMARY_DARK};
        border-color: {C.PRIMARY};
        color: {C.TEXT_PRIMARY};
        font-weight: bold;
    }}
    QPushButton#btn_primary:hover {{
        background-color: {C.PRIMARY};
    }}
    QPushButton#btn_primary:pressed {{
        background-color: {C.PRIMARY_PRESSED};
    }}

    /* ── Pulsante pericolo ────────────────────────────────────────────── */
    QPushButton#btn_danger {{
        background-color: {C.DANGER_DARK};
        border-color: {C.DANGER};
        color: {C.TEXT_PRIMARY};
    }}
    QPushButton#btn_danger:hover {{
        background-color: {C.DANGER};
    }}
    QPushButton#btn_danger:pressed {{
        background-color: {C.DANGER_PRESSED};
    }}

    /* ── Pulsante attivo ──────────────────────────────────────────────── */
    QPushButton#btn_active {{
        background-color: {C.PRIMARY};
        border-color: {C.PRIMARY_HOVER};
        color: {C.SELECTION_TEXT};
        font-weight: bold;
    }}
    QPushButton#btn_active:hover {{
        background-color: {C.PRIMARY_HOVER};
    }}

    /* ── Pulsante strumento ───────────────────────────────────────────── */
    QPushButton#btn_tool {{
        background-color: {C.BG_SURFACE};
        border: 2px solid {C.BORDER};
        border-radius: 4px;
        padding: 6px 8px;
        text-align: center;
        min-width: 48px;
    }}
    QPushButton#btn_tool:hover {{
        border-color: {C.PRIMARY};
        background-color: {C.BG_SURFACE_HOVER};
    }}
    QPushButton#btn_tool[selected="true"] {{
        border-color: {C.PRIMARY};
        background-color: {C.PRIMARY_DARK};
        color: {C.TEXT_PRIMARY};
    }}

    /* ── Etichette ────────────────────────────────────────────────────── */
    QLabel#title {{
        font-size: 13pt;
        font-weight: bold;
        color: {C.TEXT_PRIMARY};
    }}
    QLabel#subtitle {{
        font-size: 8pt;
        color: {C.TEXT_DIM};
    }}
    QLabel#section {{
        font-size: 8pt;
        font-weight: bold;
        color: {C.TEXT_SECONDARY};
        letter-spacing: 1px;
    }}
    QLabel#status_label {{
        font-size: 9pt;
        color: {C.TEXT_DIM};
    }}
    QLabel#shortcut {{
        font-size: 8pt;
        color: {C.TEXT_DIM};
        font-family: "Sarasa Mono SC", monospace;
        qproperty-alignment: AlignCenter;
    }}

    /* ── Separatore ──────────────────────────────────────────────────── */
    QFrame#separator {{
        background-color: {C.BORDER};
        max-height: 1px;
    }}

    /* ── ScrollArea ───────────────────────────────────────────────────── */
    QScrollArea {{
        border: none;
        background-color: {C.BG_MAIN};
    }}

    /* ── Slider ───────────────────────────────────────────────────────── */
    QSlider::groove:horizontal {{
        height: 4px;
        background: {C.BORDER};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {C.PRIMARY};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::sub-page:horizontal {{
        background: {C.PRIMARY};
        border-radius: 2px;
    }}

    /* ── SpinBox ──────────────────────────────────────────────────────── */
    QSpinBox {{
        background-color: {C.BG_SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 3px;
        padding: 3px 6px;
        color: {C.TEXT_PRIMARY};
    }}
    QSpinBox:focus {{
        border-color: {C.PRIMARY};
    }}
    """
