#!/usr/bin/env bash
# Interactive native-Wayland parity gate for MagicScribe on CachyOS/KDE/KWin.
# Collects reproducible environment/log/PSS evidence for behavior that cannot
# be proven by the offscreen GitHub Actions suite.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
MAGICSCRIBE_STATE_DIR="${STATE_HOME}/magicscribe"
STAMP="$(date +%Y%m%d-%H%M%S)"
REPORT_DIR="${MAGICSCRIBE_STATE_DIR}/wayland-gate-${STAMP}"
REPORT_FILE="${REPORT_DIR}/report.txt"
APP_LOG="${MAGICSCRIBE_STATE_DIR}/magicscribe.log"
PYTHON="${ROOT_DIR}/.venv/bin/python"
APP_PID=""
RUN_INDEX=0
RUN_LOG_OFFSET=0
CURRENT_RUN_LOG=""
CURRENT_CONSOLE_LOG=""
EXPECTED_SCREENS=0

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
        printf 'Risultato [y=PASS / n=FAIL / k=SKIP]: '
        IFS= read -r answer
        case "${answer,,}" in
            y|yes|s|si|sì)
                log "${id}: PASS"
                return 0
                ;;
            n|no)
                log "${id}: FAIL"
                return 1
                ;;
            k|skip)
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
    grep -E '^(Pss|Pss_Anon):' "/proc/${APP_PID}/smaps_rollup" \
        | tee -a "${REPORT_FILE}" || true
}

snapshot_run_log() {
    if [[ -f "${APP_LOG}" ]]; then
        tail -c "+$((RUN_LOG_OFFSET + 1))" "${APP_LOG}" 2>/dev/null \
            > "${CURRENT_RUN_LOG}" || true
    else
        : > "${CURRENT_RUN_LOG}"
    fi
}

start_app() {
    local mode="${1:-normal}"
    RUN_INDEX=$((RUN_INDEX + 1))
    CURRENT_RUN_LOG="${REPORT_DIR}/app-run-${RUN_INDEX}.log"
    CURRENT_CONSOLE_LOG="${REPORT_DIR}/app-console-run-${RUN_INDEX}.log"
    RUN_LOG_OFFSET=0
    if [[ -f "${APP_LOG}" ]]; then
        RUN_LOG_OFFSET="$(wc -c < "${APP_LOG}")"
    fi

    : > "${CURRENT_CONSOLE_LOG}"
    if [[ "${mode}" == "noportal" ]]; then
        env -u QT_QPA_PLATFORM \
            DBUS_SESSION_BUS_ADDRESS="unix:path=${REPORT_DIR}/missing-session-bus" \
            "${PYTHON}" "${ROOT_DIR}/main.py" \
            >"${CURRENT_CONSOLE_LOG}" 2>&1 &
    else
        # Deliberatamente rimuoviamo l'override: il gate deve provare che
        # main.py sceglie autonomamente il QPA Wayland in una sessione Wayland.
        env -u QT_QPA_PLATFORM \
            "${PYTHON}" "${ROOT_DIR}/main.py" \
            >"${CURRENT_CONSOLE_LOG}" 2>&1 &
    fi
    APP_PID=$!
    log "MagicScribe avviato: pid=${APP_PID}, mode=${mode}, run=${RUN_INDEX}"

    for _ in {1..100}; do
        if ! kill -0 "${APP_PID}" 2>/dev/null; then
            log "ERRORE: MagicScribe è terminato durante l'avvio."
            cat "${CURRENT_CONSOLE_LOG}" | tee -a "${REPORT_FILE}"
            return 1
        fi
        snapshot_run_log
        if grep -q "Applicazione avviata con shell e overlay Qt Quick" \
            "${CURRENT_RUN_LOG}" 2>/dev/null; then
            return 0
        fi
        sleep 0.1
    done

    snapshot_run_log
    log "ERRORE: timeout attendendo il completamento dell'avvio."
    tail -n 100 "${CURRENT_RUN_LOG}" | tee -a "${REPORT_FILE}" || true
    tail -n 100 "${CURRENT_CONSOLE_LOG}" | tee -a "${REPORT_FILE}" || true
    return 1
}

stop_app_forcefully() {
    if [[ -n "${APP_PID}" ]] && kill -0 "${APP_PID}" 2>/dev/null; then
        kill "${APP_PID}" 2>/dev/null || true
        for _ in {1..50}; do
            kill -0 "${APP_PID}" 2>/dev/null || break
            sleep 0.1
        done
        kill -KILL "${APP_PID}" 2>/dev/null || true
    fi
    APP_PID=""
}

graceful_quit_check() {
    local id="$1"
    printf '\nPorta il focus sul pannello MagicScribe e premi Ctrl+Q.\n'
    printf 'Dopo averlo premuto, torna qui e premi Invio...'
    IFS= read -r _

    for _ in {1..50}; do
        if ! kill -0 "${APP_PID}" 2>/dev/null; then
            log "${id}: PASS"
            APP_PID=""
            return 0
        fi
        sleep 0.1
    done

    log "${id}: FAIL"
    log "L'app non è terminata entro 5 secondi; la chiudo per continuare il gate."
    stop_app_forcefully
    return 1
}

show_current_run_log() {
    snapshot_run_log
    log "Estratto log run ${RUN_INDEX}:"
    tail -n 120 "${CURRENT_RUN_LOG}" | tee -a "${REPORT_FILE}" || true
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

if [[ "${XDG_SESSION_TYPE:-}" != "wayland" || -z "${WAYLAND_DISPLAY:-}" ]]; then
    log "SESSION_WAYLAND: FAIL — esegui il gate da una sessione KDE Plasma Wayland reale"
    log "Report completo: ${REPORT_FILE}"
    exit 2
fi
log "SESSION_WAYLAND: PASS"

if command -v systemctl >/dev/null 2>&1; then
    for service in xdg-desktop-portal.service xdg-desktop-portal-kde.service; do
        state="$(systemctl --user is-active "${service}" 2>/dev/null || true)"
        log "${service}: ${state:-unknown}"
    done
fi
if command -v pgrep >/dev/null 2>&1; then
    log "portal processes:"
    pgrep -af 'xdg-desktop-portal($|-)|xdg-desktop-portal-kde' \
        | tee -a "${REPORT_FILE}" || log "  nessun processo portal trovato"
fi
if command -v busctl >/dev/null 2>&1; then
    if busctl --user list 2>/dev/null | grep -q 'org.freedesktop.portal.Desktop'; then
        log "D-Bus org.freedesktop.portal.Desktop: presente"
    else
        log "D-Bus org.freedesktop.portal.Desktop: NON presente"
    fi
fi

if command -v kscreen-doctor >/dev/null 2>&1; then
    log "Configurazione output KScreen:"
    kscreen-doctor -o 2>&1 | tee -a "${REPORT_FILE}" || true
else
    log "kscreen-doctor: non disponibile"
fi

section "Runtime prerequisite"
if [[ ! -x "${PYTHON}" ]]; then
    log "Ambiente virtuale assente: eseguo install.sh"
    bash "${ROOT_DIR}/install.sh" | tee -a "${REPORT_FILE}"
fi

"${PYTHON}" "${ROOT_DIR}/scripts/verify_release_constraints.py" \
    | tee -a "${REPORT_FILE}"

EXPECTED_SCREENS="$(
    QT_QPA_PLATFORM=wayland "${PYTHON}" - <<'PY'
from PySide6.QtGui import QGuiApplication
app = QGuiApplication([])
print(len(app.screens()))
PY
)"
if [[ ! "${EXPECTED_SCREENS}" =~ ^[1-9][0-9]*$ ]]; then
    log "SCREEN_PROBE: FAIL — conteggio QScreen non valido: ${EXPECTED_SCREENS}"
    exit 2
fi
log "SCREEN_PROBE: PASS — QScreen Wayland=${EXPECTED_SCREENS}"

"${PYTHON}" - <<'PY' | tee -a "${REPORT_FILE}"
from pathlib import Path
from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QLibraryInfo, qVersion
platforms = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)) / "platforms"
plugins = sorted(path.name for path in platforms.glob("libqwayland*.so"))
print(f"Python/PySide6/Qt runtime: PySide6 {pyside_version}, Qt {qVersion()}")
print("Qt Wayland QPA plugins: " + ", ".join(plugins))
PY

section "Run 1 — native Wayland + production portal"
log "Se KDE mostra la finestra GlobalShortcuts, ACCETTA le cinque scorciatoie."
start_app normal
printf '\nGestisci ora l\047eventuale dialog GlobalShortcuts; poi premi Invio...'
IFS= read -r _
sleep 0.5
show_current_run_log

if grep -q "Piattaforma Qt effettiva: wayland" "${CURRENT_RUN_LOG}" \
    && grep -q "Backend Wayland nativo attivo" "${CURRENT_RUN_LOG}"; then
    log "ENV_QPA: PASS"
else
    log "ENV_QPA: FAIL — MagicScribe non sta usando il QPA Wayland nativo"
fi

if grep -q "Overlay avviato: backend=wayland, superfici=${EXPECTED_SCREENS}" \
    "${CURRENT_RUN_LOG}"; then
    log "OVERLAY_SURFACES: PASS"
else
    log "OVERLAY_SURFACES: FAIL — attese ${EXPECTED_SCREENS} superfici Wayland"
fi

if grep -q "Global shortcuts registrate tramite XDG Desktop Portal" \
    "${CURRENT_RUN_LOG}"; then
    log "PORTAL_GLOBAL: PASS"
else
    log "PORTAL_GLOBAL: FAIL"
fi

capture_pss "idle"

section "Global shortcuts — app non focalizzata"
log "Porta il focus su un'altra applicazione prima di ogni prova."
ask "GS1" "F9 attiva/disattiva il disegno mentre MagicScribe NON è focalizzato?" || true
printf '\nCrea almeno un tratto visibile prima delle prove visibility/clear. Premi Invio quando pronto...'
IFS= read -r _
ask "GS2" "Ctrl+Shift+F9 mostra/nasconde le annotazioni mentre MagicScribe NON è focalizzato?" || true
ask "GS3" "Shift+F9 cancella le annotazioni mentre MagicScribe NON è focalizzato?" || true
printf '\nCrea un nuovo tratto, poi riporta il focus fuori da MagicScribe. Premi Invio quando pronto...'
IFS= read -r _
ask "GS4" "F8 esegue undo del nuovo tratto mentre MagicScribe NON è focalizzato?" || true
ask "GS5" "Shift+F8 esegue redo dello stesso tratto mentre MagicScribe NON è focalizzato?" || true

section "No double activation"
log "Riporta il focus sul pannello di controllo."
ask "GS6" "Con il pannello focalizzato, F9 produce una sola commutazione e non un doppio trigger?" || true
ask "GS7" "Con il pannello focalizzato, undo/redo/visibility/clear producono ciascuno una sola azione?" || true

section "Compact vertical toolbar — XDG Shell"
ask "TB1" "La toolbar è frameless, compatta, verticale e interamente visibile? La posizione iniziale può essere scelta da KWin." || true
ask "TB2" "Un click sull'icona MagicScribe riduce la toolbar lasciando soltanto la floating palette?" || true
ask "TB3" "Un click sulla floating palette ripristina una toolbar interamente visibile e utilizzabile?" || true
ask "TB4" "Trascinando dall'icona MagicScribe, startSystemMove sposta correttamente la toolbar sotto KWin/Wayland?" || true
ask "TB5" "Cambiando strumento resta selezionato un solo pulsante, con stato inset/arancione coerente?" || true
ask "TB6" "Slider dello spessore e swatch colore sono visibili, raggiungibili e aggiornano lo strumento?" || true

section "Qt Quick overlay — native Wayland"
ask "OV1" "L'overlay è visivamente trasparente salvo le annotazioni, senza fondo nero/opaco?" || true
ask "OV2" "Con disegno disattivato, click, scroll e interazioni passano all'app sottostante?" || true
ask "OV3" "Con disegno attivo, il puntatore viene catturato dall'overlay e non aziona l'app sottostante?" || true
ask "OV4" "Ripetendo almeno 10 volte F9, il passaggio click-through↔capture resta stabile senza finestre che spariscono?" || true
ask "OV5" "Penna e Smooth hanno comportamento e resa corretti?" || true
ask "OV6" "Linea, rettangolo e cerchio mostrano preview e commit corretti?" || true
ask "OV7" "Gomma cancella correttamente e il cursore passa gomma↔normale?" || true
ask "OV8" "Undo, redo, clear e visibility restano coerenti dopo più tratti?" || true

section "Floating palette / stacking / focus"
ask "FL1" "La floating palette ripristina il pannello e non riceve tratti di disegno?" || true
ask "FL2" "Il drag della floating palette funziona tramite startSystemMove sotto KWin/Wayland?" || true
ask "ZW1" "Dopo più toggle, pannello e floating palette restano sopra l'overlay e non vengono coperti?" || true
ask "A11Y1" "La floating palette non ruba il focus all'app annotata e resta utilizzabile col mouse?" || true
ask "A11Y2" "Tab/focus visibile nel pannello è coerente e non ci sono controlli irraggiungibili?" || true

section "Multi-monitor / global coordinates"
if [[ "${EXPECTED_SCREENS}" -gt 1 ]]; then
    ask "MM1" "Ogni monitor è coperto dall'overlay trasparente e resta utilizzabile quando il disegno è disattivato?" || true
    ask "MM2" "Puoi creare tratti separatamente su ciascun monitor e ogni tratto resta nella posizione corretta dopo undo/redo/visibility?" || true
    ask "MM3" "Monitor disposti con coordinate negative/non allineate non spostano o duplicano le annotazioni?" || true
else
    log "MM1: N/A — un solo QScreen rilevato"
    log "MM2: N/A — un solo QScreen rilevato"
    log "MM3: N/A — un solo QScreen rilevato"
fi

section "PSS after controlled drawing load"
printf '\nDisegna ora ESATTAMENTE 20 tratti aggiuntivi, distribuendoli tra gli strumenti.\n'
printf 'Quando hai finito premi Invio per acquisire il secondo snapshot PSS...'
IFS= read -r _
capture_pss "after_20_additional_strokes"

section "Lifecycle"
graceful_quit_check "LC1" || true

section "Run 2 — portal rejection / local WindowShortcut fallback"
log "Riapro MagicScribe. Se KDE ripropone GlobalShortcuts, questa volta ANNULLA/RIFIUTA."
start_app normal
printf '\nGestisci ora l\047eventuale dialog; poi premi Invio...'
IFS= read -r _
sleep 0.5
show_current_run_log

if grep -q "Piattaforma Qt effettiva: wayland" "${CURRENT_RUN_LOG}"; then
    log "ENV_QPA_RUN2: PASS"
else
    log "ENV_QPA_RUN2: FAIL"
fi

fallback_observed=false
if grep -q "Global shortcuts non attive:" "${CURRENT_RUN_LOG}"; then
    log "PORTAL_REJECTION: PASS — fallback locale osservato"
    fallback_observed=true
elif grep -q "Global shortcuts registrate tramite XDG Desktop Portal" \
    "${CURRENT_RUN_LOG}"; then
    log "PORTAL_REJECTION: N/A — KDE ha riutilizzato la sessione portal"
else
    log "PORTAL_REJECTION: FAIL — nessun esito portal conclusivo"
fi

if [[ "${fallback_observed}" == true ]]; then
    log "Con il pannello focalizzato, verifica le cinque WindowShortcut locali."
    ask "FB1" "F9 funziona localmente con il pannello focalizzato?" || true
    ask "FB2" "Ctrl+Shift+F9 funziona localmente con il pannello focalizzato?" || true
    ask "FB3" "Shift+F9 funziona localmente con il pannello focalizzato?" || true
    ask "FB4" "F8 funziona localmente con il pannello focalizzato?" || true
    ask "FB5" "Shift+F8 funziona localmente con il pannello focalizzato?" || true
    graceful_quit_check "LC2" || true
else
    log "FB1: N/A"
    log "FB2: N/A"
    log "FB3: N/A"
    log "FB4: N/A"
    log "FB5: N/A"
    stop_app_forcefully
fi

section "Forced portal-unavailable fallback"
log "Eseguo una terza istanza Wayland con session bus volutamente irraggiungibile per provare il fallback locale deterministico."
start_app noportal
sleep 0.5
show_current_run_log
if grep -q "Piattaforma Qt effettiva: wayland" "${CURRENT_RUN_LOG}"; then
    log "ENV_QPA_RUN3: PASS"
else
    log "ENV_QPA_RUN3: FAIL"
fi
if grep -q "Global shortcuts non attive:" "${CURRENT_RUN_LOG}"; then
    log "FORCED_FALLBACK_PATH: PASS"
    log "Porta il focus sul pannello e prova le cinque scorciatoie."
    ask "FF1" "F9 funziona nel fallback locale forzato?" || true
    ask "FF2" "Ctrl+Shift+F9 funziona nel fallback locale forzato?" || true
    ask "FF3" "Shift+F9 funziona nel fallback locale forzato?" || true
    ask "FF4" "F8 funziona nel fallback locale forzato?" || true
    ask "FF5" "Shift+F8 funziona nel fallback locale forzato?" || true
else
    log "FORCED_FALLBACK_PATH: FAIL"
fi
graceful_quit_check "LC3" || true

section "Final evidence"
if [[ -f "${APP_LOG}" ]]; then
    cp -f "${APP_LOG}" "${REPORT_DIR}/magicscribe-full.log"
    log "Log applicazione completo copiato in ${REPORT_DIR}/magicscribe-full.log"
fi

pass_count="$(grep -c ': PASS' "${REPORT_FILE}" || true)"
fail_count="$(grep -c ': FAIL' "${REPORT_FILE}" || true)"
skip_count="$(grep -c ': SKIP' "${REPORT_FILE}" || true)"
na_count="$(grep -c ': N/A' "${REPORT_FILE}" || true)"
log "Risultati: PASS=${pass_count} FAIL=${fail_count} SKIP=${skip_count} N/A=${na_count}"
log "Report completo: ${REPORT_FILE}"

if [[ "${fail_count}" -gt 0 ]]; then
    log "GATE: FAIL — non chiudere issue #24 e non rimuovere il rollback xcb/X11."
    exit 2
fi
if [[ "${skip_count}" -gt 0 ]]; then
    log "GATE: INCOMPLETO — nessun FAIL, ma restano verifiche manuali SKIP."
    exit 3
fi

log "GATE: PASS — nessun FAIL/SKIP. Revisionare il report prima di chiudere issue #24 e rimuovere il rollback xcb/X11."
