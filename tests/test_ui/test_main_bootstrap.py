"""Bootstrap helpers in main.py that run before and around the Qt event loop."""

from __future__ import annotations

import logging
import os
import signal

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import main

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def restore_signal_handlers():
    saved = {signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)}
    yield
    for signum, handler in saved.items():
        signal.signal(signum, handler)


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_signal_received_before_the_event_loop_still_quits(
    restore_signal_handlers, signum: int
) -> None:
    timer = main._install_quit_signal_handlers(_APP, logging.getLogger(__name__))
    try:
        # Delivered before exec(): quit() on a loop that is not running yet
        # would be a no-op and the app would keep running.
        os.kill(os.getpid(), signum)
        QTimer.singleShot(3000, lambda: _APP.exit(99))
        assert _APP.exec() == 0
    finally:
        timer.stop()


def test_qt_mismatch_hint_only_for_layer_shell_or_qt_abi_errors() -> None:
    assert main._looks_like_qt_mismatch(
        ['module "org.kde.layershell" plugin "LayerShellQtQml" not found']
    )
    assert main._looks_like_qt_mismatch(
        ["Cannot load library liblayer-shell-qt.so: incompatible Qt library"]
    )
    assert not main._looks_like_qt_mismatch(
        ["ControlPanel.qml:12: Type RaisedSurface unavailable"]
    )
