"""Indicatore di stato animato (punto colorato)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QPropertyAnimation, QSize, Property, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPaintEvent
from PySide6.QtWidgets import QWidget

from config.theme import ThemeColors as C


class StatusIndicator(QWidget):
    """Indicatore di stato visivo con animazione pulsante."""

    STATE_COLORS = {
        "running": C.SUCCESS,
        "error": C.DANGER,
        "stopped": C.TEXT_DISABLED,
        "paused": C.PRIMARY,
    }

    def __init__(
        self, parent: QWidget | None = None, size: int = 10,
    ) -> None:
        super().__init__(parent)
        self._size: int = size
        self._color: QColor = QColor(C.TEXT_DISABLED)
        self._opacity: float = 1.0
        self._anim: QPropertyAnimation | None = None
        self.setFixedSize(QSize(size + 4, size + 4))

    def set_state(self, state: str) -> None:
        color_hex = self.STATE_COLORS.get(state, C.TEXT_DISABLED)
        self._color = QColor(color_hex)

        if self._anim is not None:
            self._anim.stop()

        if state == "running":
            self._start_pulse_animation()
        else:
            self._opacity = 1.0

        self.update()

    def _start_pulse_animation(self) -> None:
        self._anim = QPropertyAnimation(self, b"pulse_opacity")
        self._anim.setDuration(1500)
        self._anim.setStartValue(0.5)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)
        self._anim.start()

    @Property(float)
    def pulse_opacity(self) -> float:
        """Opacita' corrente per l'animazione pulsante."""
        return self._opacity

    @pulse_opacity.setter
    def pulse_opacity(self, value: float) -> None:
        self._opacity = value
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._color)
        color.setAlphaF(self._opacity)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        margin = 2
        painter.drawEllipse(margin, margin, self._size, self._size)
        painter.end()
