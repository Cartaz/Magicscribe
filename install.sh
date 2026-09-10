#!/usr/bin/env bash
# install.sh — installazione locale repo-based di MagicScribe per KDE/Wayland.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="magicscribe"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_VERSION="26.2.1"

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_CONFIG_DIR="${CONFIG_HOME}/${APP_NAME}"
APP_STATE_DIR="${STATE_HOME}/${APP_NAME}"
DESKTOP_FILE="${DATA_HOME}/applications/${APP_NAME}.desktop"
ICON_THEME_DIR="${DATA_HOME}/icons/hicolor"
VENV_DIR="${SCRIPT_DIR}/.venv"

echo "=== MagicScribe — Installazione locale ==="

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "ERRORE: ${PYTHON_BIN} non trovato." >&2
    exit 1
fi

if ! "${PYTHON_BIN}" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
then
    echo "ERRORE: MagicScribe richiede Python 3.12 o superiore." >&2
    exit 1
fi

# 1. Ambiente virtuale
echo "[1/6] Verifica ambiente virtuale..."
if [ -d "${VENV_DIR}" ]; then
    if [ ! -x "${VENV_DIR}/bin/python" ] || ! "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
    then
        echo "     Ambiente virtuale non valido: ricreazione..."
        rm -rf "${VENV_DIR}"
    fi
fi

if [ ! -d "${VENV_DIR}" ]; then
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    echo "     Ambiente virtuale creato."
else
    echo "     Ambiente virtuale valido."
fi

# 2. Dipendenze: una sola sorgente di verità in requirements.txt
echo "[2/6] Installazione dipendenze pinned..."
"${VENV_DIR}/bin/python" -m pip install "pip==${PIP_VERSION}" --quiet
"${VENV_DIR}/bin/python" -m pip install \
    -r "${SCRIPT_DIR}/requirements.txt" \
    --quiet
"${VENV_DIR}/bin/python" -m pip check
echo "     Ambiente coerente."

# 3. Verifica runtime Qt/PySide6 + D-Bus + Wayland/layer-shell
echo "[3/6] Verifica runtime PySide6/Qt, D-Bus e KDE layer-shell..."
"${VENV_DIR}/bin/python" - <<'PY'
import ctypes.util
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, qVersion
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
import jeepney

version = tuple(int(part) for part in qVersion().split(".")[:3])
if version < (6, 11, 0):
    raise SystemExit(f"Qt 6.11+ richiesto, trovato {qVersion()}")

assert QQmlApplicationEngine is not None
assert QApplication is not None
assert jeepney is not None

plugins_root = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
platforms_dir = plugins_root / "platforms"
wayland_plugins = sorted(platforms_dir.glob("libqwayland*.so"))
if not wayland_plugins:
    raise SystemExit(f"Plugin Qt Wayland non trovato in {platforms_dir}")

missing_native = [
    name for name in ("wayland-client", "xkbcommon")
    if ctypes.util.find_library(name) is None
]
if missing_native:
    raise SystemExit(
        "Librerie native Wayland mancanti: " + ", ".join(missing_native)
    )

print(
    f"     PySide6/Qt {qVersion()} OK "
    f"(Jeepney, Wayland QPA={len(wayland_plugins)}, wayland-client, xkbcommon)"
)
PY

QT_PATHS6="$(command -v qtpaths6 || true)"
if [[ -z "${QT_PATHS6}" && -x /usr/lib/qt6/bin/qtpaths6 ]]; then
    QT_PATHS6="/usr/lib/qt6/bin/qtpaths6"
fi
if [[ -z "${QT_PATHS6}" ]]; then
    echo "ERRORE: qtpaths6 non trovato; necessario per verificare l'ABI di layer-shell-qt." >&2
    exit 1
fi

PYSIDE_QT_VERSION="$("${VENV_DIR}/bin/python" - <<'PY'
from PySide6.QtCore import qVersion
print(qVersion())
PY
)"
SYSTEM_QT_VERSION="$("${QT_PATHS6}" --qt-version)"
if [[ "${PYSIDE_QT_VERSION}" != "${SYSTEM_QT_VERSION}" ]]; then
    echo "ERRORE: Qt PySide6=${PYSIDE_QT_VERSION}, Qt sistema=${SYSTEM_QT_VERSION}." >&2
    echo "layer-shell-qt usa API private QtWayland: le versioni devono coincidere." >&2
    exit 1
fi

LAYER_SHELL_QML_ROOT="$(
    PYTHONPATH="${SCRIPT_DIR}" "${VENV_DIR}/bin/python" - <<'PY'
from ui.native.layer_shell import find_layer_shell_qml_root
root = find_layer_shell_qml_root()
if root is None:
    raise SystemExit(
        "Modulo org.kde.layershell non trovato; su CachyOS/Arch installare layer-shell-qt"
    )
print(root)
PY
)"
echo "     layer-shell-qt QML: ${LAYER_SHELL_QML_ROOT} (ABI Qt ${SYSTEM_QT_VERSION})"

# 4. Verifica QML completa contro il modulo KDE reale
echo "[4/6] Verifica sorgenti QML..."
if [ ! -x "${VENV_DIR}/bin/pyside6-qmllint" ]; then
    echo "ERRORE: pyside6-qmllint non disponibile nell'ambiente virtuale." >&2
    exit 1
fi
"${VENV_DIR}/bin/pyside6-qmllint" \
    --max-warnings 0 \
    -I "${SCRIPT_DIR}/ui/qml" \
    -I "${LAYER_SHELL_QML_ROOT}" \
    "${SCRIPT_DIR}"/ui/qml/MagicScribe/*.qml
echo "     Modulo QML + layer-shell valido e senza warning."

# 5. Directory e icone
echo "[5/6] Installazione integrazione desktop..."
mkdir -p "${APP_CONFIG_DIR}" "${APP_STATE_DIR}"
for size in 16 22 24 32 48 64 128 256 512; do
    src="${SCRIPT_DIR}/assets/icons/png/magicscribe_${size}.png"
    if [ -f "${src}" ]; then
        dir="${ICON_THEME_DIR}/${size}x${size}/apps"
        mkdir -p "${dir}"
        cp -f "${src}" "${dir}/magicscribe.png"
    fi
done

SVG_SRC="${SCRIPT_DIR}/assets/icons/magicscribe.svg"
if [ -f "${SVG_SRC}" ]; then
    mkdir -p "${ICON_THEME_DIR}/scalable/apps"
    cp -f "${SVG_SRC}" "${ICON_THEME_DIR}/scalable/apps/magicscribe.svg"
fi
gtk-update-icon-cache "${ICON_THEME_DIR}" 2>/dev/null || true

desktop_exec_quote() {
    "${VENV_DIR}/bin/python" - "$1" <<'PY'
import sys

value = sys.argv[1]
if any(ord(char) < 32 or ord(char) == 127 for char in value):
    raise SystemExit("Percorso con caratteri di controllo non supportato nel file .desktop")
if "=" in value:
    raise SystemExit("Percorso contenente '=' non supportato dall'Exec del file .desktop")

encoded = []
for char in value:
    if char == "\\":
        encoded.append("\\\\\\\\")
    elif char in {'"', "`", "$"}:
        encoded.append("\\\\" + char)
    elif char == "%":
        encoded.append("%%")
    else:
        encoded.append(char)

sys.stdout.write('"' + "".join(encoded) + '"')
PY
}

EXEC_PYTHON="$(desktop_exec_quote "${VENV_DIR}/bin/python")"
EXEC_MAIN="$(desktop_exec_quote "${SCRIPT_DIR}/main.py")"
mkdir -p "$(dirname "${DESKTOP_FILE}")"
cat > "${DESKTOP_FILE}" << EOF
[Desktop Entry]
Type=Application
Version=1.5
Name=MagicScribe
Name[it]=MagicScribe
Comment=On-screen annotation tool
Comment[it]=Strumento di annotazione sullo schermo
Icon=magicscribe
Exec=${EXEC_PYTHON} ${EXEC_MAIN}
Terminal=false
Categories=Graphics;Utility;
Keywords=annotation;drawing;screenshot;presentation;
EOF

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "${DESKTOP_FILE}"
fi
update-desktop-database "$(dirname "${DESKTOP_FILE}")" 2>/dev/null || true

# 6. Riepilogo
echo "[6/6] Installazione completata."
echo "MagicScribe è un'app repo-based: il file .desktop punta a questa checkout."
echo "Avvio: ${VENV_DIR}/bin/python ${SCRIPT_DIR}/main.py"
