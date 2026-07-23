"""Indicatore di stato animato (punto colorato).

Mostra lo stato di un processo con un punto colorato
e animazione pulsante quando attivo.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPropertyAnimation, QSize, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPaintEvent
from PyQt6.QtWidgets import QWidget

from config.theme import ThemeColors as C


class StatusIndicator(QWidget):
    """Indicatore di stato visivo con punto colorato e animazione.

    Supporta quattro stati: running (verde), error (arancione),
    stopped (grigio), paused (teal). Quando attivo, il punto
    pulsa con animazione di opacita'.

    Attributes:
        _color: colore corrente dell'indicatore.
        _opacity: opacita' corrente per l'animazione.
    """

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
        """Imposta lo stato dell'indicatore.

        Args:
            state: uno tra 'running', 'error', 'stopped', 'paused'.
        """
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
        """Avvia l'animazione pulsante (opacita' 0.5-1.0).

        Usa easing curve come specificato in §3.5
        (ease-in-out per transizioni di stato).
        """
        self._anim = QPropertyAnimation(self, b"pulse_opacity")
        self._anim.setDuration(1500)
        self._anim.setStartValue(0.5)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)  # infinito
        self._anim.start()

    @pyqtProperty(float)
    def pulse_opacity(self) -> float:
        """Opacita' corrente per l'animazione pulsante."""
        return self._opacity

    @pulse_opacity.setter
    def pulse_opacity(self, value: float) -> None:
        """Imposta l'opacita' per l'animazione e ridisegna."""
        self._opacity = value
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """Disegna il punto colorato dell'indicatore."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._color)
        color.setAlphaF(self._opacity)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        margin = 2
        painter.drawEllipse(margin, margin, self._size, self._size)
        painter.end()
