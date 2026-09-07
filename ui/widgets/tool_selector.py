"""Selettore strumenti di disegno."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QSizePolicy

from core.models import ToolType

_TOOL_INFO = {
    ToolType.PEN:    ("Penna",    "P"),
    ToolType.ERASER: ("Gomma",    "G"),
    ToolType.LINE:   ("Linea",    "/"),
    ToolType.RECT:   ("Rett.",    "[ ]"),
    ToolType.CIRCLE: ("Cerchio",  "O"),
    ToolType.SMOOTH: ("Smuss.",   "~"),
}


class ToolSelector(QWidget):
    """Griglia di pulsanti per la selezione dello strumento."""

    tool_selected = Signal(ToolType)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[ToolType, QPushButton] = {}
        self._current: ToolType = ToolType.PEN
        self._build_ui()

    def _build_ui(self) -> None:
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

        for col in range(cols):
            layout.setColumnStretch(col, 1)

        self._update_selection()

    def _on_tool_clicked(self, tool: ToolType) -> None:
        self._current = tool
        self._update_selection()
        self.tool_selected.emit(tool)

    def _update_selection(self) -> None:
        for tool, btn in self._buttons.items():
            btn.setProperty("selected", tool == self._current)
            btn.setStyle(btn.style())

    def set_current_tool(self, tool: ToolType) -> None:
        self._current = tool
        self._update_selection()
