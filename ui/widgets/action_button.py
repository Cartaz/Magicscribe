"""Pulsante azione con badge scorciatoia.

Combina un QPushButton con un ShortcutBadge in un widget composto.
La registrazione delle scorciatoie appartiene alla finestra/shell; questo
componente e' esclusivamente presentazionale.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSizePolicy

from ui.widgets.shortcut_badge import ShortcutBadge


class ActionButton(QWidget):
    """Riga con pulsante azione e badge scorciatoia tastiera."""

    def __init__(
        self,
        label: str,
        shortcut: str = "",
        slot: Optional[Callable[[], None]] = None,
        obj_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn = QPushButton(label)
        if obj_name:
            self.btn.setObjectName(obj_name)
        self.btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
        )
        self.btn.setFixedHeight(30)
        if slot:
            self.btn.clicked.connect(slot)

        self.badge = ShortcutBadge(shortcut)
        layout.addWidget(self.btn)
        layout.addWidget(self.badge)

    def set_text(self, text: str) -> None:
        """Imposta il testo del pulsante."""
        self.btn.setText(text)

    def set_object_name(self, name: str) -> None:
        """Imposta l'objectName del pulsante e aggiorna lo stile."""
        self.btn.setObjectName(name)
        self.btn.setStyle(self.btn.style())

    def set_enabled(self, enabled: bool) -> None:
        """Abilita/disabilita il pulsante."""
        self.btn.setEnabled(enabled)
