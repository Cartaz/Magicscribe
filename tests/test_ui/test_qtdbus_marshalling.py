"""Verifica dei tipi D-Bus richiesti dal GlobalShortcuts portal."""

from PySide6.QtDBus import QDBusMessage, QDBusObjectPath, QDBusVariant


def test_global_shortcuts_bind_signature_is_exact() -> None:
    message = QDBusMessage.createMethodCall(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.GlobalShortcuts",
        "BindShortcuts",
    )
    shortcuts = [
        (
            "toggle_draw",
            {
                "description": QDBusVariant("Attiva o disattiva il disegno"),
                "preferred_trigger": QDBusVariant("F9"),
            },
        ),
        (
            "visibility",
            {
                "description": QDBusVariant("Mostra o nascondi le annotazioni"),
                "preferred_trigger": QDBusVariant("CTRL+SHIFT+F9"),
            },
        ),
    ]
    options = {"handle_token": QDBusVariant("magicscribe_bind_test")}

    message.setArguments([
        QDBusObjectPath("/org/freedesktop/portal/desktop/session/test/session"),
        shortcuts,
        "",
        options,
    ])

    assert message.signature() == "oa(sa{sv})sa{sv}"
