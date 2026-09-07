"""Moduli dell'interfaccia utente di MagicScribe.

I sottomoduli (MainWindow, OverlayWindow, ecc.) devono essere
importati direttamente, ad esempio:

    from ui.main_window import MainWindow

Non viene fatto import eager qui per evitare di caricare PySide6
quando si importa un sottomodulo non-Qt come ui.geometry_utils.
"""

__all__ = [
    "main_window",
    "overlay_window",
    "drawing_engine",
    "tray_icon",
    "event_bridge",
    "geometry_utils",
]
