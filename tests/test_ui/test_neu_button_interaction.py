"""Interaction regression test for the shared QML NeuButton component."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

_APP = QApplication.instance() or QApplication([])


def test_neu_button_survives_real_mouse_press_and_release() -> None:
    QQuickWindow.setDefaultAlphaBuffer(True)
    engine = QQmlApplicationEngine()
    qml_root = Path(__file__).resolve().parents[2] / "ui" / "qml"
    engine.addImportPath(str(qml_root))

    component = QQmlComponent(engine)
    component.loadFromModule("MagicScribe", "NeuButton")
    assert component.isReady(), component.errorString()

    button = component.create()
    assert isinstance(button, QQuickItem)
    button.setProperty("text", "Interaction test")
    button.setWidth(160)
    button.setHeight(42)

    window = QQuickWindow()
    window.resize(220, 100)
    button.setParentItem(window.contentItem())
    button.setX(30)
    button.setY(20)

    clicks: list[bool] = []
    button.clicked.connect(lambda: clicks.append(True))

    try:
        window.show()
        _APP.processEvents()

        pos = QPoint(110, 41)
        QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=pos)
        _APP.processEvents()
        assert button.property("pressed") is True

        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=pos)
        _APP.processEvents()
        assert button.property("pressed") is False
        assert clicks == [True]
    finally:
        window.hide()
        button.setParentItem(None)
        button.deleteLater()
        window.deleteLater()
        component.deleteLater()
        engine.deleteLater()
        _APP.processEvents()
