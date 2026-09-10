#!/usr/bin/env bash
# Permanent native-Wayland regression gate for MagicScribe on KDE/KWin.
# CI covers portable logic; this script covers compositor, input, Portal and lifecycle.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
APP_STATE_DIR="${STATE_HOME}/magicscribe"
STAMP="$(date +%Y%m%d-%H%M%S)"
REPORT_DIR="${APP_STATE_DIR}/wayland-gate-${STAMP}"
REPORT_FILE="${REPORT_DIR}/report.txt"
APP_LOG="${APP_STATE_DIR}/magicscribe.log"
PYTHON="${ROOT_DIR}/.venv/bin/python"

APP_PID=""
RUN_INDEX=0
RUN_LOG_OFFSET=0
CURRENT_RUN_LOG=""
CURRENT_CONSOLE_LOG=""
EXPECTED_SCREENS=0

mkdir -p "${REPORT_DIR}"
: > "${REPORT_FILE}"

log() { printf '%s\n' "$*" | tee -a "${REPORT_FILE}"; }
section() { log ""; log "=== $* ==="; }

cleanup() {
    if [[ -n "${APP_PID}" ]] && kill -0 "${APP_PID}" 2>/dev/null; then
        kill "${APP_PID}" 2>/dev/null || true
        sleep 0.3
        kill -KILL "${APP_PID}" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

ask() {
    local id="$1" prompt="$2" answer
    while true; do
        printf '\n[%s] %s\nRisultato [y=PASS / n=FAIL / k=SKIP]: ' "${id}" "${prompt}"
        IFS= read -r answer
        case "${answer,,}" in
            y|yes|s|si|sì) log "${id}: PASS"; return 0 ;;
            n|no) log "${id}: FAIL"; return 1 ;;
            k|skip) log "${id}: SKIP"; return 0 ;;
            *) printf 'Risposta non valida.\n' ;;
        esac
    done
}

snapshot_run_log() {
    if [[ -f "${APP_LOG}" ]]; then
        tail -c "+$((RUN_LOG_OFFSET + 1))" "${APP_LOG}" > "${CURRENT_RUN_LOG}" 2>/dev/null || true
    else
        : > "${CURRENT_RUN_LOG}"
    fi
}

show_current_run_log() {
    snapshot_run_log
    log "Estratto log run ${RUN_INDEX}:"
    tail -n 100 "${CURRENT_RUN_LOG}" | tee -a "${REPORT_FILE}" || true
}

start_app() {
    local mode="${1:-normal}"
    RUN_INDEX=$((RUN_INDEX + 1))
    CURRENT_RUN_LOG="${REPORT_DIR}/app-run-${RUN_INDEX}.log"
    CURRENT_CONSOLE_LOG="${REPORT_DIR}/app-console-run-${RUN_INDEX}.log"
    RUN_LOG_OFFSET=0
    [[ -f "${APP_LOG}" ]] && RUN_LOG_OFFSET="$(wc -c < "${APP_LOG}")"
    : > "${CURRENT_CONSOLE_LOG}"

    if [[ "${mode}" == "noportal" ]]; then
        env -u QT_QPA_PLATFORM \
            DBUS_SESSION_BUS_ADDRESS="unix:path=${REPORT_DIR}/missing-session-bus" \
            "${PYTHON}" "${ROOT_DIR}/main.py" >"${CURRENT_CONSOLE_LOG}" 2>&1 &
    else
        env -u QT_QPA_PLATFORM \
            "${PYTHON}" "${ROOT_DIR}/main.py" >"${CURRENT_CONSOLE_LOG}" 2>&1 &
    fi
    APP_PID=$!
    log "MagicScribe avviato: pid=${APP_PID}, mode=${mode}, run=${RUN_INDEX}"

    for _ in {1..120}; do
        if ! kill -0 "${APP_PID}" 2>/dev/null; then
            log "STARTUP: FAIL — processo terminato durante l'avvio"
            cat "${CURRENT_CONSOLE_LOG}" | tee -a "${REPORT_FILE}" || true
            return 1
        fi
        snapshot_run_log
        if grep -q "Applicazione avviata con shell e overlay Qt Quick" "${CURRENT_RUN_LOG}"; then
            log "STARTUP: PASS"
            return 0
        fi
        sleep 0.1
    done
    log "STARTUP: FAIL — timeout"
    show_current_run_log
    return 1
}

wait_portal_result() {
    local id="$1"
    for _ in {1..150}; do
        snapshot_run_log
        if grep -q "Global shortcuts registrate tramite XDG Desktop Portal" "${CURRENT_RUN_LOG}"; then
            log "${id}: PASS"
            return 0
        fi
        if grep -q "Global shortcuts non attive:" "${CURRENT_RUN_LOG}"; then
            log "${id}: FAIL"
            return 1
        fi
        sleep 0.1
    done
    log "${id}: FAIL — nessun esito Portal entro 15 secondi"
    return 1
}

capture_pss() {
    local label="$1"
    if [[ -z "${APP_PID}" || ! -r "/proc/${APP_PID}/smaps_rollup" ]]; then
        log "PSS_${label}: FAIL — smaps_rollup non disponibile"
        return 1
    fi
    log "PSS ${label} (pid=${APP_PID}):"
    grep -E '^(Pss|Pss_Anon):' "/proc/${APP_PID}/smaps_rollup" | tee -a "${REPORT_FILE}" || true
}

graceful_quit_check() {
    local id="$1"
    printf '\nPorta il focus sulla toolbar, premi Ctrl+Q, poi torna qui e premi Invio...'
    IFS= read -r _
    for _ in {1..50}; do
        if ! kill -0 "${APP_PID}" 2>/dev/null; then
            log "${id}: PASS"
            APP_PID=""
            return 0
        fi
        sleep 0.1
    done
    log "${id}: FAIL — processo ancora vivo dopo 5 secondi"
    cleanup
    APP_PID=""
    return 1
}

section "Repository / session"
cd "${ROOT_DIR}"
log "root: ${ROOT_DIR}"
if command -v git >/dev/null 2>&1; then
    log "branch: $(git branch --show-current 2>/dev/null || true)"
    log "commit: $(git rev-parse HEAD 2>/dev/null || true)"
    if [[ -n "$(git status --porcelain 2>/dev/null || true)" ]]; then
        log "WORKTREE: FAIL — working tree non pulito"
    else
        log "WORKTREE: PASS"
    fi
fi

log "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-<unset>}"
log "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<unset>}"
if [[ "${XDG_SESSION_TYPE:-}" != "wayland" || -z "${WAYLAND_DISPLAY:-}" ]]; then
    log "SESSION_WAYLAND: FAIL — eseguire da KDE Plasma Wayland"
    exit 2
fi
log "SESSION_WAYLAND: PASS"
command -v kscreen-doctor >/dev/null 2>&1 && kscreen-doctor -o 2>&1 | tee -a "${REPORT_FILE}" || true

section "Install / layer-shell preflight"
bash "${ROOT_DIR}/install.sh" | tee -a "${REPORT_FILE}"
"${PYTHON}" -m pip check | tee -a "${REPORT_FILE}"
EXPECTED_SCREENS="$(QT_QPA_PLATFORM=wayland "${PYTHON}" - <<'PY'
from PySide6.QtGui import QGuiApplication
app = QGuiApplication([])
print(len(app.screens()))
PY
)"
if [[ "${EXPECTED_SCREENS}" =~ ^[1-9][0-9]*$ ]]; then
    log "SCREEN_PROBE: PASS — QScreen=${EXPECTED_SCREENS}"
else
    log "SCREEN_PROBE: FAIL — valore=${EXPECTED_SCREENS}"
    exit 2
fi

section "Run 1 — layer-shell + XDG GlobalShortcuts"
log "Se KDE mostra il dialog GlobalShortcuts, accetta le cinque scorciatoie."
start_app normal
printf '\nGestisci l\047eventuale dialog KDE, poi premi Invio...'
IFS= read -r _
sleep 0.3
show_current_run_log

grep -q "Piattaforma Qt effettiva: wayland" "${CURRENT_RUN_LOG}" \
    && log "ENV_QPA: PASS" || log "ENV_QPA: FAIL"
grep -q "Backend Wayland nativo attivo" "${CURRENT_RUN_LOG}" \
    && log "WAYLAND_RUNTIME: PASS" || log "WAYLAND_RUNTIME: FAIL"
grep -q "KDE layer-shell-qt abilitato" "${CURRENT_RUN_LOG}" \
    && log "LAYER_SHELL_RUNTIME: PASS" || log "LAYER_SHELL_RUNTIME: FAIL"
grep -q "Overlay avviato: backend=wayland, ruolo=layer-shell/top, superfici=${EXPECTED_SCREENS}" \
    "${CURRENT_RUN_LOG}" && log "OVERLAY_SURFACES: PASS" || log "OVERLAY_SURFACES: FAIL"

PORTAL_OK=false
if wait_portal_result "PORTAL_GLOBAL"; then PORTAL_OK=true; fi
capture_pss "idle" || true

section "Layer roles / focus"
ask "LS1" "La toolbar resta visibile SOPRA le normali finestre anche cambiando app?" || true
ask "LS2" "La toolbar si trascina liberamente dal logo senza salto o perdita di interazione?" || true
ask "LS3" "La floating palette resta sopra le normali finestre?" || true
ask "LS4" "MagicScribe Overlay NON compare più nell'elenco Alt+Tab/task switcher?" || true

section "Toolbar / floating 1:1"
ask "FP1" "Riducendo la toolbar, la floating icon compare ESATTAMENTE sullo stesso centro del logo?" || true
ask "FP2" "La floating palette si trascina liberamente e il logo della toolbar ricompare ESATTAMENTE sul centro dell'icona al restore?" || true

section "Overlay input region"
ask "OV1" "Con disegno OFF, click e scroll raggiungono subito desktop/app sottostante?" || true
ask "OV2" "Con disegno ON, l'overlay cattura correttamente il puntatore?" || true
ask "OV3" "Tornando OFF, il desktop è interattivo IMMEDIATAMENTE senza cambio focus?" || true
ask "OV4" "Dopo almeno 10 toggle ON/OFF, cattura e click-through restano stabili?" || true

section "Global shortcuts fuori focus"
if [[ "${PORTAL_OK}" == true ]]; then
    ask "GS1" "F9 funziona con MagicScribe NON focalizzato?" || true
    ask "GS2" "Ctrl+Shift+F9 funziona con MagicScribe NON focalizzato?" || true
    ask "GS3" "F8 e Shift+F8 eseguono undo/redo fuori focus?" || true
    ask "GS4" "Shift+F9 cancella le annotazioni fuori focus?" || true
else
    log "GS1: SKIP — Portal non registrato"
    log "GS2: SKIP — Portal non registrato"
    log "GS3: SKIP — Portal non registrato"
    log "GS4: SKIP — Portal non registrato"
fi

section "Drawing parity"
ask "DR1" "Penna e Smooth disegnano correttamente e restano visivamente distinti?" || true
ask "DR2" "Linea, rettangolo e cerchio hanno preview e commit corretti?" || true
ask "DR3" "La gomma cancella correttamente e il cursore cambia in modo coerente?" || true
ask "DR4" "Undo, redo, clear e visibility restano coerenti dopo più tratti?" || true

section "Multi-monitor"
if [[ "${EXPECTED_SCREENS}" -gt 1 ]]; then
    ask "MM1" "Ogni monitor è coperto e click-through quando il disegno è OFF?" || true
    ask "MM2" "Il disegno mantiene coordinate corrette passando tra monitor?" || true
    ask "MM3" "Undo/redo/visibility non spostano o duplicano tratti fra monitor?" || true
else
    log "MM1: N/A — un solo QScreen"
    log "MM2: N/A — un solo QScreen"
    log "MM3: N/A — un solo QScreen"
fi

section "Memory / lifecycle"
printf '\nDisegna ESATTAMENTE 20 tratti aggiuntivi, poi premi Invio...'
IFS= read -r _
capture_pss "after_20_additional_strokes" || true
graceful_quit_check "LC1" || true

section "Run 2 — Portal forzatamente non disponibile"
start_app noportal
sleep 0.5
show_current_run_log
grep -q "Piattaforma Qt effettiva: wayland" "${CURRENT_RUN_LOG}" \
    && log "ENV_QPA_RUN2: PASS" || log "ENV_QPA_RUN2: FAIL"
if grep -q "Global shortcuts non attive:" "${CURRENT_RUN_LOG}"; then
    log "FORCED_FALLBACK_PATH: PASS"
    ask "FB1" "Con toolbar focalizzata, F9 funziona come WindowShortcut locale?" || true
    ask "FB2" "Con toolbar focalizzata, visibility/clear/undo/redo locali funzionano?" || true
else
    log "FORCED_FALLBACK_PATH: FAIL"
fi
graceful_quit_check "LC2" || true

section "Final evidence"
[[ -f "${APP_LOG}" ]] && cp -f "${APP_LOG}" "${REPORT_DIR}/magicscribe-full.log"
pass_count="$(grep -c ': PASS' "${REPORT_FILE}" || true)"
fail_count="$(grep -c ': FAIL' "${REPORT_FILE}" || true)"
skip_count="$(grep -c ': SKIP' "${REPORT_FILE}" || true)"
na_count="$(grep -c ': N/A' "${REPORT_FILE}" || true)"
log "Risultati: PASS=${pass_count} FAIL=${fail_count} SKIP=${skip_count} N/A=${na_count}"
log "Report completo: ${REPORT_FILE}"

if [[ "${fail_count}" -gt 0 ]]; then
    log "GATE: FAIL — regressione desktop rilevata."
    exit 2
fi
if [[ "${skip_count}" -gt 0 ]]; then
    log "GATE: INCOMPLETO — restano verifiche SKIP."
    exit 3
fi
log "GATE: PASS — nessun FAIL/SKIP."
