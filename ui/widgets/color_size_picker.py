"""Selettore colore e dimensione per lo strumento corrente."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSlider, QSpinBox,
)

from core.models import ToolType
from config.theme import ThemeColors as C

_PRESET_COLORS = [
    "#ff0000", "#ff8800", "#ffcc00", "#27ae60",
    "#00bfa5", "#e040fb", "#ffffff", "#6b7076",
]


class ColorSizePicker(QWidget):
    """Selettore colore e dimensione per lo strumento corrente."""

    color_changed = Signal(str)
    size_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_color: str = "#ff0000"
        self._current_size: int = 5
        self._tool_type: ToolType = ToolType.PEN
        self._color_label: QLabel | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._color_label = QLabel("Colore")
        self._color_label.setObjectName("section")
        layout.addWidget(self._color_label)

        color_row = QHBoxLayout()
        color_row.setSpacing(2)

        self._color_buttons: list[QPushButton] = []
        for hex_color in _PRESET_COLORS:
            btn = QPushButton()
            btn.setFixedSize(18, 18)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border: 2px solid {C.BORDER};
                    border-radius: 2px;
                }}
                QPushButton:hover {{
                    border-color: {C.PRIMARY};
                }}
            """)
            btn.clicked.connect(
                lambda checked, c=hex_color: self._set_color(c),
            )
            color_row.addWidget(btn)
            self._color_buttons.append(btn)

        color_row.addStretch()
        layout.addLayout(color_row)

        size_label = QLabel("Dimensione")
        size_label.setObjectName("section")
        layout.addWidget(size_label)

        size_row = QHBoxLayout()
        size_row.setSpacing(6)

        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(1, 100)
        self._size_slider.setValue(self._current_size)
        self._size_slider.valueChanged.connect(self._on_size_changed)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(1, 100)
        self._size_spin.setValue(self._current_size)
        self._size_spin.setFixedWidth(50)
        self._size_spin.valueChanged.connect(self._size_slider.setValue)

        size_row.addWidget(self._size_slider)
        size_row.addWidget(self._size_spin)
        layout.addLayout(size_row)

    def _set_color(self, color: str) -> None:
        self._current_color = color
        self.color_changed.emit(color)

    def _on_size_changed(self, value: int) -> None:
        self._current_size = value
        self._size_spin.setValue(value)
        self.size_changed.emit(float(value))

    def set_tool(
        self, tool_type: ToolType, color: str, size: float,
    ) -> None:
        self._tool_type = tool_type
        self._current_color = color
        self._current_size = int(size)
        self._size_slider.blockSignals(True)
        self._size_slider.setValue(self._current_size)
        self._size_slider.blockSignals(False)
        self._size_spin.blockSignals(True)
        self._size_spin.setValue(self._current_size)
        self._size_spin.blockSignals(False)

        color_visible = tool_type != ToolType.ERASER
        for btn in self._color_buttons:
            btn.setVisible(color_visible)
        if self._color_label:
            self._color_label.setVisible(color_visible)
