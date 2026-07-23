"""Componenti della finestra principale di MagicScribe.

Contiene la logica di costruzione dell'header e del footer,
separata da main_window.py per rispettare il limite di 300
righe per file (§5.1.3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton,
)

from config.constants import UIDefaults
from ui.widgets.status_indicator import StatusIndicator


def _load_app_icon(size: int = 36) -> QPixmap:
    """Carica l'icona dell'applicazione come QPixmap alla dimensione data.

    Cerca prima le icone PNG pre-renderizzate (che evitano il problema
    "buffer size too big" dell'SVG), poi fallback all'SVG.

    Args:
        size: dimensione in pixel dell'icona.

    Returns:
        QPixmap dell'icona, o pixmap vuoto se non trovata.
    """
    # Percorso relativo a questo file → assets/icons/
    _app_dir = Path(__file__).resolve().parent.parent
    _png_dir = _app_dir / "assets" / "icons" / "png"
    _svg_path = _app_dir / "assets" / "icons" / "magicscribe.svg"

    # Trova la PNG piu' vicina alla dimensione richiesta
    if _png_dir.exists():
        available = []
        for p in _png_dir.glob("magicscribe_*.png"):
            try:
                available.append(int(p.stem.split("_")[1]))
            except (IndexError, ValueError):
                # Salta file con naming non standard
                continue
        if available:
            available.sort()
            best = min(available, key=lambda s: abs(s - size))
            png_path = _png_dir / f"magicscribe_{best}.png"
            icon = QIcon(str(png_path))
            pix = icon.pixmap(size, size)
            if not pix.isNull():
                return pix

    # Fallback: SVG
    if _svg_path.exists():
        icon = QIcon(str(_svg_path))
        pix = icon.pixmap(size, size)
        if not pix.isNull():
            return pix

    # Ultimo fallback: pixmap vuoto
    return QPixmap(size, size)


def build_header(
    status_indicator: StatusIndicator,
) -> QHBoxLayout:
    """Costruisce l'header con logo, titolo e indicatore stato.

    Args:
        status_indicator: indicatore di stato animato.

    Returns:
        Layout orizzontale dell'header.
    """
    header = QHBoxLayout()
    header.setSpacing(8)

    icon_label = QLabel()
    icon_pixmap = _load_app_icon(36)
    icon_label.setPixmap(icon_pixmap)
    icon_label.setFixedSize(36, 36)

    title_col = QVBoxLayout()
    title_col.setSpacing(1)
    t = QLabel("MagicScribe")
    t.setObjectName("title")
    s = QLabel("Annotazioni sullo schermo")
    s.setObjectName("subtitle")
    title_col.addWidget(t)
    title_col.addWidget(s)

    header.addWidget(icon_label)
    header.addLayout(title_col)
    header.addStretch()
    header.addWidget(status_indicator)

    return header


def build_separator() -> QFrame:
    """Crea un separatore orizzontale standard.

    Returns:
        QFrame con linea orizzontale.
    """
    sep = QFrame()
    sep.setObjectName("separator")
    sep.setFrameShape(QFrame.Shape.HLine)
    return sep


def build_footer(
    on_minimize: Callable[[], None],
    shortcut_text: str = "Ctrl+M",
) -> QHBoxLayout:
    """Costruisce il footer con pulsante minimizza.

    Args:
        on_minimize: callback per la minimizzazione.
        shortcut_text: testo scorciatoia da mostrare.

    Returns:
        Layout orizzontale del footer.
    """
    footer_row = QHBoxLayout()
    footer_row.setSpacing(8)

    footer_label = QLabel("Riduci a icona volante per massimizzare l'area")
    footer_label.setObjectName("subtitle")
    footer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

    btn_minimize = QPushButton("Riduci")
    btn_minimize.setObjectName("btn_primary")
    btn_minimize.setFixedHeight(28)
    btn_minimize.setFixedWidth(80)
    btn_minimize.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_minimize.setToolTip(f"Minimizza ({shortcut_text})")
    btn_minimize.clicked.connect(on_minimize)

    footer_row.addWidget(footer_label, 1)
    footer_row.addWidget(btn_minimize)

    return footer_row
