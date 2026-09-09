# MagicScribe

MagicScribe is a lightweight, local-first screen annotation tool for KDE Plasma/Linux, inspired by Epic Pen. It lets you draw directly over any application with pen, smooth-stroke, line, rectangle, circle and eraser tools, with undo/redo, annotation visibility, clear-screen actions and keyboard shortcuts. The desktop UI is built with PySide6 and Qt Quick/QML; no web stack or remote service is required.

## Runtime architecture

Production uses `Python 3.12+ -> PySide6 / Qt 6.11+ -> QApplication + QQmlApplicationEngine -> Qt Quick/QML`.

Python owns canonical state, persistence, drawing history, desktop integration and native services. QML owns presentation, animation and temporary interaction state. The overlay uses `QQuickWindow` plus a Python `QQuickPaintedItem`, reusing the QPainter renderer.

The QML boundary is intentionally small: `DrawingAdapter`, `ToolAdapter`, `ShellAdapter` and `ToolListModel`.

Global drawing shortcuts use the XDG Desktop Portal. The portal transport is isolated in `ui/native/global_shortcuts.py` and uses Jeepney in a dedicated Python worker thread. This avoids implicit QtDBus conversion of the portal's compound `a(sa{sv})` payload while keeping blocking D-Bus I/O off the GUI thread; the rest of the application only sees the focused `GlobalShortcutService` API.

## Development checks

```bash
python scripts/verify_release_constraints.py
python -m compileall -q config core ui scripts main.py
pyside6-qmllint --max-warnings 0 -I ui/qml ui/qml/MagicScribe/*.qml
python -m pytest -q
python scripts/benchmark_renderer.py --quick
bash -n install.sh scripts/local_desktop_gate.sh
```

## Reproducible dependency policy

`requirements.txt` and `requirements-dev.txt` are compatibility contracts: they state the dependency ranges the code is expected to support.

`constraints-release.txt` selects the exact audited runtime versions used by `install.sh`. `constraints-ci.txt` extends that set with exact development/test versions used by CI. `scripts/verify_release_constraints.py` requires every direct runtime and CI dependency to have exactly one corresponding pin, and rejects stale or missing pins.

Updating a dependency is therefore explicit: update its compatibility range only when needed, update the corresponding constraint pin, run the full CI matrix, and perform the local desktop gate when the change can affect Qt, QML, portals, windowing or native integration.

## Local desktop parity harness

The KDE/KWin parity harness remains available for regression checks on the target CachyOS desktop:

```bash
bash scripts/local_desktop_gate.sh
```

It records session/portal information, per-run application logs, Linux PSS from `/proc/<pid>/smaps_rollup`, global/local shortcut behavior, overlay/floating-window observations and lifecycle results under `~/.local/state/magicscribe/desktop-gate-<timestamp>/`.

The migration gate tracked in GitHub issue #6 was completed on the target desktop after review of a run with no failures. The harness intentionally reports a non-zero result when checks are skipped, so future reports must still be interpreted in context when a check is genuinely not applicable, such as multi-monitor geometry on a single-monitor system.

## Platform policy

The production shell and overlay are Qt Quick only; the historical QWidget shell/overlay and its QSS theme have been removed.

On a Wayland session `main.py` still forces Qt `xcb`/XWayland until native-Wayland parity is demonstrated separately. `ui/native/x11_input_shape.py` therefore remains part of the production runtime: it owns the X11 Shape input-region handling needed for reliable click-through under the current xcb/XWayland policy and is not a legacy QWidget fallback.

Native Wayland support is deliberately a separate future milestone rather than a silent backend switch. Its acceptance gate must demonstrate equivalent behavior for overlay input/click-through, always-on-top semantics, global shortcuts, toolbar/floating-window interaction, multi-monitor behavior, lifecycle and memory on the target KDE/KWin desktop. Only after that parity is observed should the forced `QT_QPA_PLATFORM=xcb` policy and X11 input-shape path be removed.

The floating palette intentionally uses `WindowDoesNotAcceptFocus` so it does not steal focus from the application being annotated.

## Visual system

Production QML uses the dark-neumorphic tokens centralized in `ui/qml/MagicScribe/Theme.qml`: surface `#141414`, accent `#ff6600`, Noto Sans, radii `28 / 22 / 16 / 12`.

The primary control shell is a compact frameless vertical toolbar placed on the left side by default. Clicking the MagicScribe icon reduces it to the small draggable `FloatingPalette`; clicking that palette restores the toolbar. Tool state, drawing state and configuration remain owned by Python and are only presented through the existing QML adapters.
