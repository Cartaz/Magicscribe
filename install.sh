#!/bin/bash
# install.sh — Script di installazione locale per MagicScribe
# Crea l'ambiente virtuale, installa le dipendenze e configura
# il file .desktop per l'integrazione con KDE Plasma.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="magicscribe"

# Rispetta XDG_CONFIG_HOME / XDG_STATE_HOME come fa il codice Python.
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
APP_CONFIG_DIR="${CONFIG_HOME}/${APP_NAME}"
APP_STATE_DIR="${STATE_HOME}/${APP_NAME}"

# Desktop file: segue XDG_DATA_HOME se definito.
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
DESKTOP_FILE="${DATA_HOME}/applications/${APP_NAME}.desktop"
ICON_THEME_DIR="${DATA_HOME}/icons/hicolor"

echo "=== MagicScribe — Installazione locale ==="

# 1. Ambiente virtuale
echo "[1/5] Creazione ambiente virtuale..."
if [ ! -d "${SCRIPT_DIR}/.venv" ]; then
    python3 -m venv "${SCRIPT_DIR}/.venv"
    echo "     Ambiente virtuale creato."
else
    echo "     Ambiente virtuale gia' esistente."
fi

# 2. Dipendenze
echo "[2/5] Installazione dipendenze..."
"${SCRIPT_DIR}/.venv/bin/python" -m pip install --upgrade pip --quiet
"${SCRIPT_DIR}/.venv/bin/python" -m pip install -r "${SCRIPT_DIR}/requirements.txt" --quiet
echo "     Dipendenze installate."

# 3. Directory di configurazione (rispetta XDG)
echo "[3/5] Creazione directory di configurazione..."
mkdir -p "${APP_CONFIG_DIR}"
mkdir -p "${APP_STATE_DIR}"
echo "     Directory create (${APP_CONFIG_DIR}, ${APP_STATE_DIR})."

# 4. Icone nel tema di sistema (PNG pre-renderizzate)
echo "[4/5] Installazione icone nel tema di sistema..."
# Installa le icone PNG pre-renderizzate nella gerarchia hicolor.
# KDE Plasma le trovera' automaticamente per taskbar, menu e alt+tab.
# Le PNG evitano completamente l'errore "qt.svg.draw: buffer size too big".
for size in 16 22 24 32 48 64 128 256 512; do
    src="${SCRIPT_DIR}/assets/icons/png/magicscribe_${size}.png"
    if [ -f "$src" ]; then
        dir="${ICON_THEME_DIR}/${size}x${size}/apps"
        mkdir -p "$dir"
        cp -f "$src" "${dir}/magicscribe.png"
    fi
done
# Copia anche la versione SVG scalabile (se presente) come fallback
# per temi che la preferiscono.
SVG_SRC="${SCRIPT_DIR}/assets/icons/magicscribe.svg"
if [ -f "${SVG_SRC}" ]; then
    mkdir -p "${ICON_THEME_DIR}/scalable/apps"
    cp -f "${SVG_SRC}" "${ICON_THEME_DIR}/scalable/apps/magicscribe.svg"
else
    echo "     (SVG non trovato, salto installazione scalable)"
fi

# Aggiorna la cache delle icone
gtk-update-icon-cache "${ICON_THEME_DIR}" 2>/dev/null || true
echo "     Icone installate nel tema hicolor."

# 5. File .desktop
echo "[5/5] Creazione file .desktop..."
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
Exec=${SCRIPT_DIR}/.venv/bin/python ${SCRIPT_DIR}/main.py
Terminal=false
Categories=Graphics;Utility;
Keywords=annotation;drawing;screenshot;presentation;
StartupWMClass=MagicScribe
EOF

echo "     File .desktop creato in ${DESKTOP_FILE}"

# Aggiorna il database desktop
update-desktop-database "$(dirname "${DESKTOP_FILE}")" 2>/dev/null || true

echo ""
echo "=== Installazione completata! ==="
echo ""
echo "Per avviare MagicScribe:"
echo "  ${SCRIPT_DIR}/.venv/bin/python ${SCRIPT_DIR}/main.py"
echo ""
echo "Oppure cercare 'MagicScribe' nel menu delle applicazioni."
echo ""
echo "Scorciatoie da tastiera:"
echo "  F9          — Attiva/Disattiva disegno"
echo "  Ctrl+Shift+F9 — Mostra/Nascondi annotazioni"
echo "  Shift+F9    — Cancella schermo"
echo "  F8          — Annulla tratto"
echo "  Shift+F8    — Ripristina tratto"
echo "  Ctrl+M      — Riduci a icona volante"
echo "  Ctrl+Q      — Esci dall'applicazione"
