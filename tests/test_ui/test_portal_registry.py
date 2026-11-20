"""Regression tests for XDG host-app portal attribution."""

from __future__ import annotations

from jeepney import HeaderFields, MessageType

from ui.native.portal_registry import APP_ID, dbus_error_message, register_message


def test_registry_message_serializes_magicscribe_app_id() -> None:
    message = register_message()
    assert APP_ID == "magicscribe"
    assert message.header.fields[HeaderFields.signature] == "sa{sv}"
    assert message.body == ("magicscribe", {})
    assert message.serialise(serial=1)


def test_dbus_error_message_formats_only_error_replies() -> None:
    class _Header:
        def __init__(self, message_type, fields) -> None:
            self.message_type = message_type
            self.fields = fields

    class _Reply:
        def __init__(self, message_type, fields, body) -> None:
            self.header = _Header(message_type, fields)
            self.body = body

    error = _Reply(
        MessageType.error,
        {HeaderFields.error_name: "org.freedesktop.DBus.Error.AccessDenied"},
        ("denied",),
    )
    assert dbus_error_message(error) == "org.freedesktop.DBus.Error.AccessDenied: denied"
    assert dbus_error_message(_Reply(MessageType.error, {}, ())) == "D-Bus error"
    assert dbus_error_message(_Reply(MessageType.method_return, {}, ("ok",))) is None
