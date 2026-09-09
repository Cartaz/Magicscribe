# MagicScribe

MagicScribe is a lightweight, local-first screen annotation tool for KDE Plasma/Linux, inspired by Epic Pen. It lets you draw directly over any application with pen, smooth-stroke, line, rectangle, circle and eraser tools, with undo/redo, annotation visibility, clear-screen actions and keyboard shortcuts. The desktop UI is built with PySide6 and Qt Quick/QML; no web stack or remote service is required.

## Runtime architecture

Production uses `Python 3.12+ -> PySide6 / Qt 6.11+ -> QApplication + QQmlApplicationEngine -> Qt Quick/QML`.

Python owns canonical state, persistence, drawing history, desktop integration and native services. QML owns presentation, animation and temporary interaction state. The overlay uses `QQuickWindow` plus Python `QQuickPaintedItem` canvases, reusing the QPainter renderer.

The QML boundary is intentionally small: `DrawingAdapter`, `ToolAdapter`, `ShellAdapter` and `ToolListModel`.

Global drawing shortcuts use the XDG Desktop Portal. The portal transport is isolated in `ui/native/global_shortcuts.py` and uses Jeepney in a dedicated Python worker thread. Blocking D-Bus I/O therefore stays off the GUI thread; the rest of the application only sees the focused `GlobalShortcutService` API.

## Development checks

```bash
python scripts/verify_release_constraints.py
python -m compileall -q config core ui scripts main.py
python -m pytest -q
python scripts/benchmark_renderer.py --quick
bash -n install.sh scripts/local_desktop_gate.sh
```

Portable QML is linted in CI. `install.sh` additionally lints the Wayland-specific QML against the actual system `org.kde.layershell` module, because that module is supplied by KDE rather than the PySide6 wheel.

## Reproducible dependency policy

`requirements.txt` and `requirements-dev.txt` are compatibility contracts: they state the dependency ranges the code is expected to support.

`constraints-release.txt` selects the exact audited runtime versions used by `install.sh`. `constraints-ci.txt` extends that set with exact development/test versions used by CI. `scripts/verify_release_constraints.py` requires every direct runtime and CI dependency to have exactly one corresponding pin, and rejects stale or missing pins.

Updating Qt on the native Wayland path requires extra care: KDE `layer-shell-qt` uses QtWayland private APIs. `install.sh` therefore requires the PySide6 Qt runtime and the system Qt reported by `qtpaths6` to have the same version before enabling the layer-shell QML module.

## Native Wayland architecture

On a Wayland session MagicScribe selects Qt's native `wayland` QPA by default. An explicit environment override such as `QT_QPA_PLATFORM=xcb` remains only as a diagnostic rollback until the target KDE/KWin parity gate in GitHub issue #24 is complete.

The first native prototype used ordinary XDG Shell top-level windows. Real testing on the target KDE/KWin desktop rejected that design: the fullscreen transparent drawing window appeared in the task switcher, could retain desktop interaction/focus after drawing was disabled, the toolbar was not reliably above ordinary windows, and the shell could not provide the positioning/drag semantics MagicScribe needs.

The native design therefore uses KDE `layer-shell-qt`, which exposes the Wayland layer-shell protocol to Qt/QML. One drawing layer-surface is created per `QScreen` on the **Top** layer. The control panel and floating palette use the **Overlay** layer, so they remain above the drawing surface. The drawing surface has no keyboard interactivity; the control panel requests keyboard interaction only on demand, while the floating palette requests none.

Every `DrawingCanvas` maps local pointer coordinates into one canonical global desktop coordinate space before committing strokes and translates that history back into screen-local painter coordinates when rendering. Undo/redo/clear/visibility therefore remain single-owner operations in Python regardless of which monitor received the gesture.

Layer-shell windows are positioned by compositor-owned anchors and margins. The toolbar and floating palette are dragged by updating those margins; `QWindow.startSystemMove()` remains only on the ordinary X11/offscreen window path. No absolute top-level positioning is emulated on native Wayland.

Native click-through still uses Qt's `WindowTransparentForInput`, which maps to the Wayland surface input region. `ui/native/x11_input_shape.py` is retained only for an explicit xcb/XWayland rollback and must not be removed until the physical KWin parity gate is green.

## Local desktop parity harness

Run the acceptance harness from the target CachyOS/KDE Plasma Wayland session:

```bash
bash scripts/local_desktop_gate.sh
```

The harness runs `install.sh` first, so it verifies the system `layer-shell-qt` QML module and Qt ABI before starting the application. It then verifies the effective Wayland QPA, layer-shell runtime activation, one drawing surface per `QScreen`, the final XDG GlobalShortcuts registration result, Linux PSS from `/proc/<pid>/smaps_rollup`, and guides the physical checks for stacking, Alt+Tab exclusion, toolbar dragging, click-through/input capture, drawing parity, multi-monitor behavior and lifecycle.

A real manual `SKIP` leaves the gate incomplete. Conditions that genuinely do not apply to the machine, such as multi-monitor checks on a single-monitor desktop, are recorded as `N/A`. The report must contain no `FAIL` or `SKIP` before issue #24 is closed and PR #25 is merged.

## Platform policy

The production shell and overlay are Qt Quick only; the historical QWidget shell/overlay and its QSS theme have been removed.

Native Wayland plus KDE layer-shell is the target architecture for Plasma. X11-specific code is no longer part of the default Wayland execution path and is retained temporarily only to provide a controlled rollback during parity validation.

## Visual system

Production QML uses the dark-neumorphic tokens centralized in `ui/qml/MagicScribe/Theme.qml`: surface `#141414`, accent `#ff6600`, Noto Sans, radii `28 / 22 / 16 / 12`.

The primary control shell is a compact frameless vertical toolbar. Clicking the MagicScribe icon reduces it to the small draggable `FloatingPalette`; clicking that palette restores the toolbar. Tool state, drawing state and configuration remain owned by Python and are only presented through the existing QML adapters.
