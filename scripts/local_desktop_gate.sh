#!/usr/bin/env bash
# Local interactive desktop parity gate for MagicScribe on CachyOS/KDE/KWin.
# Collects reproducible environment/log/PSS evidence and guides the checks that
# cannot be proven in offscreen CI.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
MAGICSCRIBE_STATE_DIR="${STATE_HOME}/magicscribe"
STAMP="$(date +%Y%m%d-%H%M%S)"
REPORT_DIR="${MAGICSCRIBE_STATE_DIR}/desktop-gate-${STAMP}"
REPORT_FILE="${REPORT_DIR}/report.txt"
APP_STDERR="${REPORT_DIR}/app-console.log"
APP_LOG="${MAGICSCRIBE_STATE_DIR}/magicscribe.log"
PYTHON="${ROOT_DIR}/.venv/bin/python"
APP_PID=""

mkdir -p "${REPORT_DIR}"
: > "${REPORT_FILE}"

log() {
    printf '%s\n' "$*" | tee -a "${REPORT_FILE}"
}

section() {
    log ""
    log "=== $* ==="
}

cleanup() {
    if [[ -n "${APP_PID}" ]] && kill -0 "${APP_PID}" 2>/dev/null; then
        kill "${APP_PID}" 2>/dev/null || true
        for _ in {1..30}; do
            kill -0 "${APP_PID}" 2>/dev/null || break
            sleep 0.1
        done
        kill -KILL "${APP_PID}" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

ask() {
    local id="$1"
    local prompt="$2"
    local answer
    while true; do
        printf '\n[%s] %s\n' "${id}" "${prompt}"
        printf 'Risultato [y=PASS / n=FAIL / s=SKIP]: '
        IFS= read -r answer
        case "${answer,,}" in
            y|yes|si|sì)
                log "${id}: PASS"
                return 0
                ;;
            n|no)
                log "${id}: FAIL"
                return 1
                ;;
            s|skip)
                log "${id}: SKIP"
                return 0
                ;;
            *)
                printf 'Risposta non valida.\n'
                ;;
        esac
    done
}

capture_pss() {
    local label="$1"
    if [[ -z "${APP_PID}" || ! -r "/proc/${APP_PID}/smaps_rollup" ]]; then
        log "PSS ${label}: NON DISPONIBILE (pid=${APP_PID:-none})"
        return 1
    fi
    log "PSS ${label} (pid ${APP_PID}):"
    grep -E '^(Pss|Pss_Anon):' "/proc/${APP_PID}/smaps_rollup" | tee -a "${REPORT_FILE}" || true
}

start_app() {
    local log_offset
    log_offset=0
    if [[ -f "${APP_LOG}" ]]; then
        log_offset="$(wc -c < "${APP_LOG}")"
    fi

    : > "${APP_STDERR}"
    "${PYTHON}" "${ROOT_DIR}/main.py" >"${APP_STDERR}" 2>&1 &
    APP_PID=$!
    log "MagicScribe avviato: pid=${APP_PID}"

    for _ in {1..50}; do
        if ! kill -0 "${APP_PID}" 2>/dev/null; then
            log "ERRORE: MagicScribe è terminato durante l'avvio."
            cat "${APP_STDERR}" | tee -a "${REPORT_FILE}"
            return 1
        fi
        if [[ -f "${APP_LOG}" ]] && tail -c "+$((log_offset + 1))" "${APP_LOG}" 2>/dev/null | grep -q "Applicazione avviata con shell e overlay Qt Quick"; then
            break
        fi
        sleep 0.1
    done

    sleep 0.4
    if [[ -f "${APP_LOG}" ]]; then
        log "Estratto log dell'avvio corrente:"
        tail -c "+$((log_offset + 1))" "${APP_LOG}" 2>/dev/null | tail -n 80 | tee -a "${REPORT_FILE}"
    fi
}

stop_app() {
    if [[ -n "${APP_PID}" ]] && kill -0 "${APP_PID}" 2>/dev/null; then
        kill "${APP_PID}" 2>/dev/null || true
        for _ in {1..50}; do
            kill -0 "${APP_PID}" 2>/dev/null || break
            sleep 0.1
        done
    fi
    APP_PID=""
}

section "Repository"
cd "${ROOT_DIR}"
if command -v git >/dev/null 2>&1; then
    log "root: ${ROOT_DIR}"
    log "branch: $(git branch --show-current 2>/dev/null || true)"
    log "commit: $(git rev-parse HEAD 2>/dev/null || true)"
    if [[ -n "$(git status --porcelain 2>/dev/null || true)" ]]; then
        log "ATTENZIONE: working tree non pulito"
        git status --short | tee -a "${REPORT_FILE}"
    else
        log "working tree: clean"
    fi
fi

section "Desktop/session environment"
log "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-<unset>}"
log "QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-<unset>}"
log "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<unset>}"
log "DISPLAY=${DISPLAY:-<unset>}"
log "XDG_CURRENT_DESKTOP=${XDG_CURRENT_DESKTOP:-<unset>}"
log "KDE_FULL_SESSION=${KDE_FULL_SESSION:-<unset>}"
log "KDE_SESSION_VERSION=${KDE_SESSION_VERSION:-<unset>}"

if command -v systemctl >/dev/null 2>&1; then
    for service in xdg-desktop-portal.service xdg-desktop-portal-kde.service; do
        state="$(systemctl --user is-active "${service}" 2>/dev/null || true)"
        log "${service}: ${state:-unknown}"
    done
fi
if command -v pgrep >/dev/null 2>&1; then
    log "portal processes:"
    pgrep -af 'xdg-desktop-portal($|-)|xdg-desktop-portal-kde' | tee -a "${REPORT_FILE}" || log "  nessun processo portal trovato"
fi
if command -v busctl >/dev/null 2>&1; then
    if busctl --user list 2>/dev/null | grep -q 'org.freedesktop.portal.Desktop'; then
        log "D-Bus org.freedesktop.portal.Desktop: presente"
    else
        log "D-Bus org.freedesktop.portal.Desktop: NON presente"
    fi
fi

section "Runtime prerequisite"
if [[ ! -x "${PYTHON}" ]]; then
    log "Ambiente virtuale assente: eseguo install.sh"
    "${ROOT_DIR}/install.sh" | tee -a "${REPORT_FILE}"
fi
"${PYTHON}" - <<'PY' | tee -a "${REPORT_FILE}"
from PySide6.QtCore import qVersion
from PySide6 import __version__ as pyside_version
print(f"Python/PySide6/Qt runtime: PySide6 {pyside_version}, Qt {qVersion()}")
PY

section "Start application / portal"
log "Se KDE mostra la finestra del GlobalShortcuts portal, ACCETTA le cinque scorciatoie per questa prima fase."
start_app

if grep -q "Global shortcuts registrate tramite XDG Desktop Portal" "${APP_LOG}" 2>/dev/null; then
    log "Portal registration: PASS (messaggio di successo presente nel log)"
else
    log "Portal registration: NON CONFERMATA. Controlla l'estratto log sopra."
fi

capture_pss "idle"

section "Global shortcuts — app non focalizzata"
log "Porta il focus su un'altra applicazione prima di ogni prova."
ask "GS1" "F9 attiva/disattiva il disegno mentre MagicScribe NON è focalizzato?" || true
ask "GS2" "Ctrl+Shift+F9 mostra/nasconde le annotazioni mentre MagicScribe NON è focalizzato?" || true
ask "GS3" "Shift+F9 cancella le annotazioni mentre MagicScribe NON è focalizzato?" || true
ask "GS4" "F8 esegue undo mentre MagicScribe NON è focalizzato?" || true
ask "GS5" "Shift+F8 esegue redo mentre MagicScribe NON è focalizzato?" || true

section "No double activation"
log "Riporta il focus sul pannello di controllo."
ask "GS6" "Con il pannello focalizzato, F9 produce una sola commutazione e non un doppio trigger?" || true
ask "GS7" "Con il pannello focalizzato, undo/redo/visibility/clear producono ciascuno una sola azione?" || true

section "Qt Quick overlay / floating palette"
ask "OV1" "Overlay visivamente trasparente salvo le annotazioni?" || true
ask "OV2" "Con disegno disattivato, click e interazioni passano al desktop/app sottostante?" || true
ask "OV3" "Con disegno attivo, il puntatore viene catturato correttamente dall'overlay?" || true
ask "OV4" "Penna e Smooth hanno comportamento e resa corretti?" || true
ask "OV5" "Linea, rettangolo e cerchio mostrano preview corretta e commit corretto?" || true
ask "OV6" "Gomma cancella correttamente e il cursore passa correttamente gomma↔normale?" || true
ask "OV7" "Undo, redo, clear e visibility restano coerenti dopo più tratti?" || true
ask "FL1" "La floating palette ripristina il pannello e non riceve tratti di disegno?" || true
ask "FL2" "Il drag della floating palette funziona correttamente sotto KWin/XWayland?" || true
ask "ZW1" "Dopo più toggle del disegno, overlay resta sotto pannello/floating e non li copre?" || true

if command -v xrandr >/dev/null 2>&1; then
    log "Configurazione monitor riportata da xrandr:"
    xrandr --listmonitors 2>&1 | tee -a "${REPORT_FILE}" || true
fi
ask "MM1" "Se usi più monitor, l'overlay copre correttamente l'intero desktop virtuale (anche coordinate negative)? Altrimenti SKIP." || true

section "PSS after controlled drawing load"
printf '\nDisegna ora ESATTAMENTE 20 tratti complessivi aggiuntivi, distribuendoli tra gli strumenti.\n'
printf 'Quando hai finito premi Invio per acquisire il secondo snapshot PSS...'
IFS= read -r _
capture_pss "after_20_additional_strokes"

section "Accessibility/focus observation"
ask "A11Y1" "La floating palette non ruba il focus all'app annotata e resta comunque utilizzabile correttamente col mouse?" || true
ask "A11Y2" "Tab/focus visibile nel pannello di controllo è coerente e non ci sono controlli irraggiungibili?" || true

section "Portal rejection/fallback pass"
log "Chiudo la prima istanza. La seconda serve a verificare il fallback locale."
stop_app
log "Riapriamo MagicScribe. Se KDE ripropone la richiesta GlobalShortcuts, questa volta ANNULLALA/RIFIUTALA."
start_app
sleep 0.5

if grep -q "Global shortcuts non attive:" "${APP_LOG}" 2>/dev/null; then
    log "Fallback registration path: osservato nel log"
else
    log "Fallback registration path: non osservato automaticamente (il portal può aver riusato una decisione precedente)"
fi

log "Con il pannello MagicScribe focalizzato, prova le cinque scorciatoie locali."
ask "FB1" "F9 funziona localmente con il pannello focalizzato?" || true
ask "FB2" "Ctrl+Shift+F9 funziona localmente con il pannello focalizzato?" || true
ask "FB3" "Shift+F9 funziona localmente con il pannello focalizzato?" || true
ask "FB4" "F8 funziona localmente con il pannello focalizzato?" || true
ask "FB5" "Shift+F8 funziona localmente con il pannello focalizzato?" || true

section "Final evidence"
if [[ -f "${APP_LOG}" ]]; then
    cp -f "${APP_LOG}" "${REPORT_DIR}/magicscribe.log"
    log "Log applicazione copiato in ${REPORT_DIR}/magicscribe.log"
fi
cp -f "${APP_STDERR}" "${REPORT_DIR}/app-console-last-run.log" 2>/dev/null || true

pass_count="$(grep -c ': PASS$' "${REPORT_FILE}" || true)"
fail_count="$(grep -c ': FAIL$' "${REPORT_FILE}" || true)"
skip_count="$(grep -c ': SKIP$' "${REPORT_FILE}" || true)"
log "Risultati interattivi: PASS=${pass_count} FAIL=${fail_count} SKIP=${skip_count}"
log "Report completo: ${REPORT_FILE}"

if [[ "${fail_count}" -gt 0 ]]; then
    log "GATE: FAIL — non rimuovere il fallback legacy."
    exit 2
fi

log "GATE interattivo senza FAIL espliciti. Controllare comunque eventuali SKIP e il requisito portal rejection prima di chiudere issue #6."
