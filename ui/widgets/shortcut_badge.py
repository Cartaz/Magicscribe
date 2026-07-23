"""Badge scorciatoia tastiera.

Visualizza la combinazione di tasti come badge con
sfondo semi-trasparente e testo centrato.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from config.theme import ThemeColors as C


class ShortcutBadge(QLabel):
    """Badge che mostra una scorciatoia da tastiera.

    Il badge ha sfondo semi-trasparente, bordo sottile,
    testo centrato in font monospace.

    Attributes:
        _key_text: testo della scorciatoia (es. 'F9', 'Ctrl+F9').
    """

    def __init__(self, key_text: str, parent: QLabel | None = None) -> None:
        super().__init__(key_text, parent)
        self._key_text: str = key_text
        self.setObjectName("shortcut_badge")
        self.setFixedWidth(64)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            QLabel#shortcut_badge {{
                background-color: {C.SHORTCUT_BG};
                border: 1px solid {C.SHORTCUT_BORDER};
                border-radius: 3px;
                padding: 1px 4px;
                font-size: 10px;
                font-family: "Sarasa Mono SC", monospace;
                color: {C.TEXT_SECONDARY};
            }}
        """)
