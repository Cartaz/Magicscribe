"""Layer UI e integrazione Qt di MagicScribe.

La shell di produzione vive in `ui.qml`, gli adapter in `ui.adapters`, le
integrazioni desktop in `ui.native` e l'overlay Qt Quick in `ui.quick`.
I moduli QWidget storici restano importabili solo come riferimento di parita'.
"""

__all__ = ["adapters", "drawing_engine", "models", "native", "qml", "quick", "tray_icon"]
