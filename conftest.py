"""Shared pytest setup.

Living at the repository root, this file also puts the root on ``sys.path`` so
plain ``pytest`` finds the application packages, and it selects the offscreen
Qt platform before any test module imports PySide6.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402


class OverlayWindowComponent:
    """Stand-in for the WaylandLayerSurface QML component outside KDE."""

    def __init__(self) -> None:
        self.created: list[QQuickWindow] = []

    def create(self) -> QQuickWindow:
        window = QQuickWindow()
        window.setColor(QColor(0, 0, 0, 0))
        self.created.append(window)
        return window

    @staticmethod
    def errors() -> list[object]:
        return []


@pytest.fixture
def overlay_window_component() -> OverlayWindowComponent:
    return OverlayWindowComponent()
