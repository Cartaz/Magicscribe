"""Static guardrails for the local KDE desktop parity harness."""

from pathlib import Path


def test_local_desktop_gate_captures_required_evidence() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "scripts" / "local_desktop_gate.sh").read_text(encoding="utf-8")

    assert "/proc/${APP_PID}/smaps_rollup" in source
    assert "Pss_Anon" in source
    assert "Global shortcuts registrate tramite XDG Desktop Portal" in source
    assert "Global shortcuts non attive:" in source
    assert "Piattaforma Qt: xcb" in source
    assert "xrandr --listmonitors" in source
    assert "Ctrl+Shift+Q" in source
    assert "after_20_additional_strokes" in source


def test_local_desktop_gate_uses_run_scoped_logs() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "scripts" / "local_desktop_gate.sh").read_text(encoding="utf-8")

    assert "CURRENT_RUN_LOG" in source
    assert "RUN_LOG_OFFSET" in source
    assert "app-run-${RUN_INDEX}.log" in source
