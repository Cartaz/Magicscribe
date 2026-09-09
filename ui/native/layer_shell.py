"""Discovery del modulo KDE layer-shell-qt per il runtime Wayland nativo.

Il pacchetto e' fornito dal sistema Plasma, mentre PySide6 porta il proprio Qt.
Questo modulo individua soltanto la root QML di sistema e la aggiunge all'engine;
non contiene policy di dominio o fallback silenziosi.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import subprocess

from PySide6.QtCore import QLibraryInfo, qVersion
from PySide6.QtQml import QQmlEngine

logger = logging.getLogger(__name__)

_LAYER_SHELL_RELATIVE = Path("org/kde/layershell/qmldir")


def _candidate_qml_roots() -> list[Path]:
    candidates: list[Path] = []

    for variable in ("QML2_IMPORT_PATH", "QML_IMPORT_PATH"):
        raw = os.environ.get(variable, "")
        for entry in raw.split(os.pathsep):
            if entry:
                candidates.append(Path(entry))

    candidates.append(
        Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.QmlImportsPath))
    )

    qtpaths = shutil.which("qtpaths6")
    if qtpaths:
        try:
            qml_root = subprocess.run(
                [qtpaths, "--query", "QT_INSTALL_QML"],
                check=True,
                capture_output=True,
                text=True,
                timeout=2,
            ).stdout.strip()
            if qml_root:
                candidates.append(Path(qml_root))
        except (OSError, subprocess.SubprocessError):
            logger.debug("qtpaths6 non disponibile per la discovery layer-shell", exc_info=True)

    candidates.extend((
        Path("/usr/lib/qt6/qml"),
        Path("/usr/lib64/qt6/qml"),
    ))

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def find_layer_shell_qml_root() -> Path | None:
    """Restituisce la root QML contenente ``org.kde.layershell``."""
    for root in _candidate_qml_roots():
        if (root / _LAYER_SHELL_RELATIVE).is_file():
            return root
    return None


def configure_layer_shell(engine: QQmlEngine) -> Path:
    """Rende disponibile layer-shell-qt all'engine o fallisce chiaramente."""
    qml_root = find_layer_shell_qml_root()
    if qml_root is None:
        raise RuntimeError(
            "Modulo QML org.kde.layershell non trovato. "
            "Su CachyOS/Arch installare il pacchetto 'layer-shell-qt'."
        )

    engine.addImportPath(str(qml_root))
    logger.info(
        "KDE layer-shell-qt abilitato da %s (Qt runtime %s)",
        qml_root,
        qVersion(),
    )
    return qml_root
