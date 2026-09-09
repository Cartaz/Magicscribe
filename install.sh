#!/usr/bin/env bash
# install.sh — Script di installazione locale per MagicScribe
# Crea/ripara l'ambiente virtuale, installa le dipendenze e configura
# il file .desktop per l'integrazione con KDE Plasma.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="magicscribe"
PYTHON_BIN="${PYTHON_BIN:-python3}"

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
APP_CONFIG_DIR="${CONFIG_HOME}/${APP_NAME}"
APP_STATE_DIR="${STATE_HOME}/${APP_NAME}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
DESKTOP_FILE="${DATA_HOME}/applications/${APP_NAME}.desktop"
ICON_THEME_DIR="${DATA_HOME}/icons/hicolor"
VENV_DIR="${SCRIPT_DIR}/.venv"
LAYER_SHELL_QML_ROOT=""

echo "=== MagicScribe — Installazione locale ==="

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "ERRORE: ${PYTHON_BIN} non trovato." >&2
    exit 1
fi

if ! "${PYTHON_BIN}" - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12+ richiesto, trovato {sys.version.split()[0]}")
PY
then
    echo "ERRORE: MagicScribe richiede Python 3.12 o superiore." >&2
    exit 1
fi

# 1. Ambiente virtuale
echo "[1/7] Verifica ambiente virtuale..."
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

# 2. Dipendenze
echo "[2/7] Installazione dipendenze riproducibili..."
"${VENV_DIR}/bin/python" "${SCRIPT_DIR}/scripts/verify_release_constraints.py"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip --quiet
"${VENV_DIR}/bin/python" -m pip install \
    -r "${SCRIPT_DIR}/requirements.txt" \
    -c "${SCRIPT_DIR}/constraints-release.txt" \
    --quiet
echo "     Dipendenze release installate dai pin verificati."

# 3. Verifica runtime Qt/PySide6 + D-Bus + Wayland/layer-shell
echo "[3/7] Verifica runtime PySide6/Qt, D-Bus e KDE layer-shell..."
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
    raise SystemExit(
        "Plugin Qt Wayland non trovato in "
        f"{platforms_dir}; il porting nativo richiede il QPA Wayland"
    )

missing_native = [
    name for name in ("wayland-client", "xkbcommon")
    if ctypes.util.find_library(name) is None
]
if missing_native:
    raise SystemExit(
        "Librerie native richieste dal runtime Wayland mancanti: "
        + ", ".join(missing_native)
    )

print(
    f"     PySide6/Qt {qVersion()} OK "
    f"(Jeepney, Wayland QPA={len(wayland_plugins)}, wayland-client, xkbcommon)"
)
PY

if ! command -v qtpaths6 >/dev/null 2>&1; then
    echo "ERRORE: qtpaths6 non trovato; necessario per verificare l'ABI di layer-shell-qt." >&2
    exit 1
fi

PYSIDE_QT_VERSION="$("${VENV_DIR}/bin/python" - <<'PY'
from PySide6.QtCore import qVersion
print(qVersion())
PY
)"
SYSTEM_QT_VERSION="$(qtpaths6 --qt-version)"
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

# xcb/X11 resta soltanto un rollback diagnostico durante il gate di migrazione.
if "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1
import ctypes.util
from pathlib import Path
from PySide6.QtCore import QLibraryInfo
plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)) / "platforms"
raise SystemExit(0 if (
    (plugins / "libqxcb.so").is_file()
    and ctypes.util.find_library("X11") is not None
    and ctypes.util.find_library("Xext") is not None
) else 1)
PY
then
    echo "     Rollback xcb/X11: disponibile"
else
    echo "     Rollback xcb/X11: non disponibile"
fi

# 4. Verifica modulo QML, incluso il boundary KDE di sistema
echo "[4/7] Verifica sorgenti QML..."
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

# 5. Directory di configurazione
echo "[5/7] Creazione directory di configurazione..."
mkdir -p "${APP_CONFIG_DIR}" "${APP_STATE_DIR}"
echo "     Directory create (${APP_CONFIG_DIR}, ${APP_STATE_DIR})."

# 6. Icone nel tema di sistema
echo "[6/7] Installazione icone nel tema di sistema..."
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
else
    echo "     (SVG non trovato, salto installazione scalable)"
fi

gtk-update-icon-cache "${ICON_THEME_DIR}" 2>/dev/null || true
echo "     Icone installate nel tema hicolor."

# 7. File .desktop
echo "[7/7] Creazione file .desktop..."
mkdir -p "$(dirname "${DESKTOP_FILE}")"

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
StartupWMClass=MagicScribe
EOF

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "${DESKTOP_FILE}"
fi

echo "     File .desktop creato in ${DESKTOP_FILE}"
update-desktop-database "$(dirname "${DESKTOP_FILE}")" 2>/dev/null || true

echo ""
echo "=== Installazione completata ==="
echo "Per avviare MagicScribe:"
echo "  ${VENV_DIR}/bin/python ${SCRIPT_DIR}/main.py"
