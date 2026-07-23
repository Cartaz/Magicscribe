"""Selettore strumenti di disegno.

Griglia di pulsanti per selezionare lo strumento
corrente (Pen, Eraser, Line, Rect, Circle, Smooth).
Usa QGridLayout adattiva con max 3 colonne (§5.1.8).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QPushButton, QSizePolicy,
)

from core.models import ToolType
from config.theme import ThemeColors as C

# Etichette e simboli per ogni strumento (no emoji, §3.6)
_TOOL_INFO = {
    ToolType.PEN:    ("Penna",    "P"),
    ToolType.ERASER: ("Gomma",    "G"),
    ToolType.LINE:   ("Linea",    "/"),
    ToolType.RECT:   ("Rett.",    "[ ]"),
    ToolType.CIRCLE: ("Cerchio",  "O"),
    ToolType.SMOOTH: ("Smuss.",   "~"),
}


class ToolSelector(QWidget):
    """Griglia di pulsanti per la selezione dello strumento.

    Emette il segnale tool_selected quando l'utente clicca
    un pulsante strumento. Il pulsante selezionato e'
    evidenziato visivamente.

    Layout: 3 colonne x 2 righe conforme a §3.4 e §5.1.8.

    Signals:
        tool_selected: emesso con il ToolType selezionato.
    """

    tool_selected = pyqtSignal(ToolType)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[ToolType, QPushButton] = {}
        self._current: ToolType = ToolType.PEN
        self._build_ui()

    def _build_ui(self) -> None:
        """Costruisce la griglia di pulsanti strumento."""
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        tools = list(ToolType)
        cols = 3
        for idx, tool in enumerate(tools):
            row, col = divmod(idx, cols)
            label, icon = _TOOL_INFO[tool]
            btn = QPushButton(f"{icon} {label}")
            btn.setObjectName("btn_tool")
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
            )
            btn.setFixedHeight(28)
            btn.clicked.connect(
                lambda checked, t=tool: self._on_tool_clicked(t),
            )
            layout.addWidget(btn, row, col)
            self._buttons[tool] = btn

        # Distribuzione uniforme delle colonne (§3.4)
        for col in range(cols):
            layout.setColumnStretch(col, 1)

        self._update_selection()

    def _on_tool_clicked(self, tool: ToolType) -> None:
        """Gestisce il click su un pulsante strumento.

        Args:
            tool: strumento selezionato.
        """
        self._current = tool
        self._update_selection()
        self.tool_selected.emit(tool)

    def _update_selection(self) -> None:
        """Aggiorna l'evidenziazione visiva del pulsante selezionato."""
        for tool, btn in self._buttons.items():
            btn.setProperty("selected", tool == self._current)
            btn.setStyle(btn.style())

    def set_current_tool(self, tool: ToolType) -> None:
        """Imposta lo strumento corrente dall'esterno.

        Args:
            tool: il ToolType da selezionare.
        """
        self._current = tool
        self._update_selection()
