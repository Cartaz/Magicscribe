"""Card con intestazione in maiuscoletto.

Contenitore visivo per raggruppare azioni correlate,
con sfondo, bordo e intestazione sezione.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

from config.theme import ThemeColors as C

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class Card(QFrame):
    """Card con intestazione sezione in maiuscoletto."""

    def __init__(
        self, section_title: str, parent: QFrame | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(4)

        header = QLabel(section_title.upper())
        header.setObjectName("section")
        font = QFont("Noto Sans", 13, QFont.Weight.Medium)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        font.setStyleStrategy(QFont.StyleStrategy.PreferMatch)
        header.setFont(font)
        header.setStyleSheet(f"color: {C.TEXT_SECONDARY};")
        self._layout.addWidget(header)

    def add_widget(self, widget: QWidget) -> None:
        """Aggiunge un widget alla card."""
        self._layout.addWidget(widget)

    def add_layout(self, layout: QVBoxLayout) -> None:
        """Aggiunge un layout alla card."""
        self._layout.addLayout(layout)

    def add_spacing(self, size: int) -> None:
        """Aggiunge spaziatura verticale."""
        self._layout.addSpacing(size)
