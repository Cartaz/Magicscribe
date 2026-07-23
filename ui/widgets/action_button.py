"""Pulsante azione con badge scorciatoia.

Combina un QPushButton con un ShortcutBadge in un
widget composto, usato nelle card delle azioni.
Ogni pulsante d'azione ha un badge scorciatoia visibile
accanto ad esso (§5.2.1).
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSizePolicy,
)

from ui.widgets.shortcut_badge import ShortcutBadge


class ActionButton(QWidget):
    """Riga con pulsante azione e badge scorciatoia tastiera.

    Il pulsante occupa lo spazio disponibile, il badge e'
    fisso a destra. La scorciatoia e' registrata nel sistema
    globale tramite QShortcut (non solo visiva, §5.2.1).

    Attributes:
        btn: il QPushButton interno.
        badge: il ShortcutBadge interno.
    """

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

        # Registra la scorciatoia nel sistema globale (§5.2.1)
        if shortcut and slot:
            self._shortcut = QShortcut(QKeySequence(shortcut), self)
            self._shortcut.activated.connect(slot)

    # ── API pubblica ─────────────────────────────────────────────────────

    def set_text(self, text: str) -> None:
        """Imposta il testo del pulsante.

        Args:
            text: nuovo testo.
        """
        self.btn.setText(text)

    def set_object_name(self, name: str) -> None:
        """Imposta l'objectName del pulsante (per styling QSS) e aggiorna lo stile.

        Args:
            name: nome oggetto QSS.
        """
        self.btn.setObjectName(name)
        # Forza il refresh del foglio di stile applicato
        self.btn.setStyle(self.btn.style())

    def set_enabled(self, enabled: bool) -> None:
        """Abilita/disabilita il pulsante.

        Args:
            enabled: True per abilitare, False per disabilitare.
        """
        self.btn.setEnabled(enabled)
