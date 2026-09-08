"""Regression tests for XDG host-app portal attribution."""

from __future__ import annotations

from pathlib import Path

from jeepney import HeaderFields

from ui.native.portal_registry import APP_ID, register_message


def test_registry_message_serializes_magicscribe_app_id() -> None:
    message = register_message()
    assert APP_ID == "magicscribe"
    assert message.header.fields[HeaderFields.signature] == "sa{sv}"
    assert message.body == ("magicscribe", {})
    assert message.serialise(serial=1)


def test_registry_runs_before_global_shortcuts_portal_calls() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "ui"
        / "native"
        / "global_shortcuts.py"
    ).read_text(encoding="utf-8")
    registry_call = source.index(
        "register_host_app(connection, timeout=_METHOD_REPLY_TIMEOUT)"
    )
    create_call = source.index("self._create_and_bind_session(connection, responses)")
    assert registry_call < create_call
