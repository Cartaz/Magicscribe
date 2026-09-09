# MagicScribe

MagicScribe is a lightweight, local-first screen annotation tool for KDE Plasma/Linux, inspired by Epic Pen. It lets you draw directly over any application with pen, smooth-stroke, line, rectangle, circle and eraser tools, with undo/redo, annotation visibility, clear-screen actions and keyboard shortcuts. The desktop UI is built with PySide6 and Qt Quick/QML; no web stack or remote service is required.

## Runtime architecture

Production uses `Python 3.12+ -> PySide6 / Qt 6.11+ -> QApplication + QQmlApplicationEngine -> Qt Quick/QML`.

Python owns canonical state, persistence, drawing history, desktop integration and native services. QML owns presentation, animation and temporary interaction state. The overlay uses `QQuickWindow` plus Python `QQuickPaintedItem` canvases, reusing the QPainter renderer.

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

## Native Wayland migration

On a Wayland session MagicScribe now selects Qt's native `wayland` QPA by default. An explicit environment override such as `QT_QPA_PLATFORM=xcb` is retained only as a diagnostic rollback until the target KDE/KWin parity gate in GitHub issue #24 is complete.

The Wayland overlay does not attempt to reproduce the X11 concept of one absolutely-positioned top-level spanning the virtual desktop. XDG Shell intentionally leaves top-level placement to the compositor, so the native design uses one transparent fullscreen `QQuickWindow` per `QScreen`. Every `DrawingCanvas` maps local pointer coordinates into one global desktop coordinate space before committing strokes, and translates that same canonical history back into its screen-local painter coordinates when rendering. Undo/redo/clear/visibility therefore remain single-owner operations in Python regardless of which monitor received the gesture.

The compact control panel and floating palette remain ordinary QML top-level windows. Native Wayland placement is compositor-owned; manual movement uses `QWindow.startSystemMove()` from the existing QML drag handlers instead of programmatic `setPosition()`. X11/offscreen retains the existing explicit placement/clamp policy.

`ui/native/x11_input_shape.py` is still present only for an explicit xcb/XWayland rollback. Native Wayland uses Qt's `WindowTransparentForInput` path. The X11 helper must not be removed until the interactive KDE/KWin gate has demonstrated stable click-through, input capture, stacking, focus, global shortcuts, multi-monitor behavior, lifecycle and memory.

KDE `layer-shell-qt` is deliberately not a dependency of the first native implementation. Standard Qt/XDG Shell is simpler and avoids coupling the Python application to a system plugin built against QtWayland private APIs. If the real KWin gate proves that standard Qt cannot deliver the required overlay stacking or shell anchoring, `layer-shell-qt` is the documented next alternative rather than an implicit runtime fallback.

## Local desktop parity harness

The native Wayland acceptance harness must be run from the target CachyOS/KDE Plasma Wayland session:

```bash
bash scripts/local_desktop_gate.sh
```

It deliberately removes any inherited `QT_QPA_PLATFORM` override when starting MagicScribe so the test proves that `main.py` selects native Wayland itself. It records the effective QPA, Qt Wayland plugins, QScreen count, Portal state, per-run logs, Linux PSS from `/proc/<pid>/smaps_rollup`, global/local shortcut behavior, click-through and capture behavior, toolbar/floating interaction, stacking/focus, multi-monitor observations and lifecycle results under `~/.local/state/magicscribe/wayland-gate-<timestamp>/`.

A gate result containing a real manual `SKIP` remains incomplete. Conditions that genuinely do not apply to the machine, such as multi-monitor checks on a single-monitor desktop or KDE reusing an already-approved Portal session, are recorded as `N/A` instead. The report must have no `FAIL` or `SKIP` before issue #24 is closed and the xcb/X11 rollback is removed.

## Platform policy

The production shell and overlay are Qt Quick only; the historical QWidget shell/overlay and its QSS theme have been removed.

Native Wayland is the target architecture for KDE Plasma. X11-specific code is no longer part of the default Wayland execution path and is retained temporarily only to provide a controlled rollback during parity validation.

The floating palette intentionally uses `WindowDoesNotAcceptFocus` so it does not steal focus from the application being annotated.

## Visual system

Production QML uses the dark-neumorphic tokens centralized in `ui/qml/MagicScribe/Theme.qml`: surface `#141414`, accent `#ff6600`, Noto Sans, radii `28 / 22 / 16 / 12`.

The primary control shell is a compact frameless vertical toolbar. Under XDG Shell its initial placement is compositor-owned rather than forced to an absolute left-side coordinate. Clicking the MagicScribe icon reduces it to the small draggable `FloatingPalette`; clicking that palette restores the toolbar. Tool state, drawing state and configuration remain owned by Python and are only presented through the existing QML adapters.
