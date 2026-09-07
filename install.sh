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
echo "[2/7] Installazione dipendenze..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip --quiet
"${VENV_DIR}/bin/python" -m pip install -r "${SCRIPT_DIR}/requirements.txt" --quiet
echo "     Dipendenze installate."

# 3. Verifica runtime Qt/PySide6
echo "[3/7] Verifica runtime PySide6/Qt..."
"${VENV_DIR}/bin/python" - <<'PY'
from PySide6.QtCore import qVersion
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

version = tuple(int(part) for part in qVersion().split(".")[:3])
if version < (6, 11, 0):
    raise SystemExit(f"Qt 6.11+ richiesto, trovato {qVersion()}")

assert QQmlApplicationEngine is not None
assert QApplication is not None
print(f"     PySide6/Qt {qVersion()} OK")
PY

# 4. Verifica modulo QML
echo "[4/7] Verifica sorgenti QML..."
if [ ! -x "${VENV_DIR}/bin/pyside6-qmllint" ]; then
    echo "ERRORE: pyside6-qmllint non disponibile nell'ambiente virtuale." >&2
    exit 1
fi
"${VENV_DIR}/bin/pyside6-qmllint" \
    -I "${SCRIPT_DIR}/ui/qml" \
    "${SCRIPT_DIR}"/ui/qml/MagicScribe/*.qml
echo "     Modulo QML valido."

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

cat > "${DESKTOP_FILE}" << EOF
[Desktop Entry]
Type=Application
Version=1.5
Name=MagicScribe
Name[it]=MagicScribe
Comment=On-screen annotation tool
Comment[it]=Strumento di annotazione sullo schermo
Icon=magicscribe
Exec=${VENV_DIR}/bin/python ${SCRIPT_DIR}/main.py
Terminal=false
Categories=Graphics;Utility;
Keywords=annotation;drawing;screenshot;presentation;
StartupWMClass=MagicScribe
EOF

echo "     File .desktop creato in ${DESKTOP_FILE}"
update-desktop-database "$(dirname "${DESKTOP_FILE}")" 2>/dev/null || true

echo ""
echo "=== Installazione completata ==="
echo "Per avviare MagicScribe:"
echo "  ${VENV_DIR}/bin/python ${SCRIPT_DIR}/main.py"
