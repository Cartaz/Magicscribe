"""Static guardrails for the local KDE native-Wayland parity harness."""

from pathlib import Path

from config.constants import HotkeyDefaults


def test_local_desktop_gate_captures_required_evidence() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "scripts" / "local_desktop_gate.sh").read_text(encoding="utf-8")

    assert "/proc/${APP_PID}/smaps_rollup" in source
    assert "Pss_Anon" in source
    assert "Global shortcuts registrate tramite XDG Desktop Portal" in source
    assert "Global shortcuts non attive:" in source
    assert "wait_portal_result" in source
    assert "Piattaforma Qt effettiva: wayland" in source
    assert "Backend Wayland nativo attivo" in source
    assert "KDE layer-shell-qt abilitato" in source
    assert (
        "Overlay avviato: backend=wayland, ruolo=layer-shell/top, "
        "superfici=${EXPECTED_SCREENS}"
    ) in source
    assert "MagicScribe Overlay NON compare più" in source
    assert "kscreen-doctor -o" in source
    assert "QT_QPA_PLATFORM=wayland" in source
    assert "env -u QT_QPA_PLATFORM" in source
    assert HotkeyDefaults.QUIT_APP in source
    assert "after_20_additional_strokes" in source
    assert "issue #24" in source
    assert "PR #25" in source


def test_local_desktop_gate_uses_run_scoped_logs() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "scripts" / "local_desktop_gate.sh").read_text(encoding="utf-8")

    assert "CURRENT_RUN_LOG" in source
    assert "RUN_LOG_OFFSET" in source
    assert "app-run-${RUN_INDEX}.log" in source
