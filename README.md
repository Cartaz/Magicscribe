# MagicScribe

MagicScribe is a lightweight, local-first screen annotation tool for KDE Plasma/Linux, inspired by Epic Pen. It lets you draw directly over any application with pen, smooth-stroke, line, rectangle, circle and eraser tools, with undo/redo, annotation visibility, clear-screen actions and keyboard shortcuts. The desktop UI is built with PySide6 and Qt Quick/QML; no web stack or remote service is required.

## Runtime architecture

Production uses `Python 3.12+ -> PySide6 / Qt 6.11+ -> QApplication + QQmlApplicationEngine -> Qt Quick/QML`.

Python owns canonical state, persistence, drawing history, desktop integration and native services. QML owns presentation, animation and temporary interaction state. The overlay uses `QQuickWindow` plus a Python `QQuickPaintedItem`, reusing the QPainter renderer.

The QML boundary is intentionally small: `DrawingAdapter`, `ToolAdapter`, `ShellAdapter` and `ToolListModel`.

## Development checks

```bash
python -m compileall -q config core ui main.py
pyside6-qmllint --max-warnings 0 -I ui/qml ui/qml/MagicScribe/*.qml
python -m pytest -q
bash -n install.sh scripts/local_desktop_gate.sh
```

## Local desktop parity gate

The remaining KDE/KWin parity checks are intentionally interactive. On the target CachyOS desktop run:

```bash
bash scripts/local_desktop_gate.sh
```

The harness records session/portal information, per-run application logs, Linux PSS from `/proc/<pid>/smaps_rollup`, global/local shortcut behavior, overlay/floating-window observations and lifecycle results under `~/.local/state/magicscribe/desktop-gate-<timestamp>/`.

A zero exit status means the interactive report contains no FAIL or SKIP entries. Exit code `2` means at least one check failed; exit code `3` means the gate is incomplete because at least one check was skipped. Review the generated report before closing issue #6.

## Deliberate migration gate

The production shell is Qt Quick, but native KDE parity is not yet considered demonstrated. On Wayland `main.py` currently forces Qt `xcb`/XWayland. The old QWidget/X11 implementation remains in-tree only as a parity reference.

Do not remove it until GitHub issue #6 is completed on CachyOS/KDE/KWin. The gate covers global shortcuts, click-through, z-order, floating drag, cursors, multi-monitor geometry and Linux PSS from `/proc/<pid>/smaps_rollup`.

The floating palette intentionally uses `WindowDoesNotAcceptFocus` while this gate is open so it does not steal focus from the application being annotated. Keyboard/focus behavior must be evaluated in the same desktop parity pass.

## Visual system

Production QML uses the dark-neumorphic tokens centralized in `ui/qml/MagicScribe/Theme.qml`: surface `#141414`, accent `#ff6600`, Noto Sans, radii `28 / 22 / 16 / 12`.

`config/theme.py`, `ui/styles/` and the QWidget modules are legacy-only and must not be imported by the production bootstrap.
