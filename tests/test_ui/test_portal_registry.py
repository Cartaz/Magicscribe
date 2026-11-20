"""Regression tests for XDG host-app portal attribution."""

from __future__ import annotations

from jeepney import HeaderFields

from ui.native.portal_registry import APP_ID, register_message


def test_registry_message_serializes_magicscribe_app_id() -> None:
    message = register_message()
    assert APP_ID == "magicscribe"
    assert message.header.fields[HeaderFields.signature] == "sa{sv}"
    assert message.body == ("magicscribe", {})
    assert message.serialise(serial=1)
