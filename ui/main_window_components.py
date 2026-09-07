"""Componenti della finestra principale di MagicScribe."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton

from ui.widgets.status_indicator import StatusIndicator


def _load_app_icon(size: int = 36) -> QPixmap:
    """Carica l'icona dell'applicazione alla dimensione richiesta."""
    app_dir = Path(__file__).resolve().parent.parent
    png_dir = app_dir / "assets" / "icons" / "png"
    svg_path = app_dir / "assets" / "icons" / "magicscribe.svg"

    if png_dir.exists():
        available = []
        for path in png_dir.glob("magicscribe_*.png"):
            try:
                available.append(int(path.stem.split("_")[1]))
            except (IndexError, ValueError):
                continue
        if available:
            best = min(sorted(available), key=lambda candidate: abs(candidate - size))
            png_path = png_dir / f"magicscribe_{best}.png"
            pixmap = QIcon(str(png_path)).pixmap(size, size)
            if not pixmap.isNull():
                return pixmap

    if svg_path.exists():
        pixmap = QIcon(str(svg_path)).pixmap(size, size)
        if not pixmap.isNull():
            return pixmap

    return QPixmap(size, size)


def build_header(status_indicator: StatusIndicator) -> QHBoxLayout:
    """Costruisce l'header con logo, titolo e indicatore stato."""
    header = QHBoxLayout()
    header.setSpacing(8)

    icon_label = QLabel()
    icon_label.setPixmap(_load_app_icon(36))
    icon_label.setFixedSize(36, 36)

    title_col = QVBoxLayout()
    title_col.setSpacing(1)
    title = QLabel("MagicScribe")
    title.setObjectName("title")
    subtitle = QLabel("Annotazioni sullo schermo")
    subtitle.setObjectName("subtitle")
    title_col.addWidget(title)
    title_col.addWidget(subtitle)

    header.addWidget(icon_label)
    header.addLayout(title_col)
    header.addStretch()
    header.addWidget(status_indicator)
    return header


def build_separator() -> QFrame:
    """Crea un separatore orizzontale standard."""
    separator = QFrame()
    separator.setObjectName("separator")
    separator.setFrameShape(QFrame.Shape.HLine)
    return separator


def build_footer(
    on_minimize: Callable[[], None],
    shortcut_text: str = "Ctrl+M",
) -> QHBoxLayout:
    """Costruisce il footer con pulsante minimizza."""
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
