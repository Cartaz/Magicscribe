# MagicScribe

MagicScribe is a lightweight, local-first screen annotation tool for KDE Plasma on native Wayland. It provides pen, smooth-stroke, line, rectangle, circle and eraser tools, plus undo/redo, visibility, clear-screen actions and keyboard shortcuts. The application is entirely local: Python/PySide6 owns state and native integration, while Qt Quick/QML owns presentation and interaction.

## Supported platform

MagicScribe 2.x has one production platform contract: **KDE Plasma on native Wayland**. Production uses KDE `layer-shell-qt`; X11/XWayland is not a supported fallback. Portable/offscreen Qt components remain only so CI can exercise QML and rendering logic without a compositor; they use the same fullscreen-host geometry as production rather than a second desktop-window behavior.

Python 3.12, 3.13 and 3.14 are covered by CI. Qt/PySide6 6.11+ is required. Because KDE `layer-shell-qt` uses private QtWayland APIs, `install.sh` requires the PySide6 Qt version to match the system Qt version reported by `qtpaths6`.

## Architecture

The dependency direction is intentionally narrow:

```text
QML -> adapters -> AppController -> domain services -> Settings
                         |
                         +-> immutable AppState
```

`AppController` is the only mutable application boundary exposed to UI/native services. It owns drawing/visibility state, stroke history and tool workflows and publishes explicit lifecycle-safe callbacks to the Qt adapters. The core does not import Qt.

Tool capabilities and defaults have one canonical declaration in `core.models.TOOL_SPECS`. Settings schema and tool configuration are derived from those domain specifications, while labels and glyphs remain presentation data in `ui.models.tool_list_model`. `Settings` is the sole persisted source of truth for tool selection/configuration; `ToolManager` derives live values instead of caching a second copy.

`WindowCoordinator` is the sole owner of control/floating `QWindow` objects, input masks and 1:1 minimize/restore geometry. `ShellAdapter` only exposes that public behavior to QML and never reaches into coordinator internals.

The Wayland overlay creates one Top-layer surface per `QScreen`. All canvases write strokes into one canonical global-desktop coordinate space, so history operations remain single-owner across monitors. Control and floating surfaces use the Overlay layer. Their layer-surfaces stay stationary; only `toolbarHost` / `paletteHost` move, while `QWindow.setMask()` restricts pointer input to the visible host.

Click-through uses `WindowTransparentForInput`; runtime changes call `requestUpdate()` so the Wayland input region is committed immediately. Global drawing shortcuts use XDG Desktop Portal through Jeepney on a dedicated worker thread, keeping blocking D-Bus operations off the GUI thread.

The Smooth tool spatially resamples dense pointer input before causal filtering and cubic approximation. This makes smoothing depend on physical path distance rather than mouse event frequency and keeps already-consolidated geometry append-stable.

## Dependencies and development

Dependency metadata is intentionally consolidated in one `pyproject.toml` using standard dependency groups:

- `runtime`: exact audited runtime dependencies;
- `dev`: runtime plus exact CI/development dependencies.

The installer and CI consume those groups directly. CI additionally pins GitHub Actions to commit SHAs, pins pip, runs Ruff, tests Python 3.12–3.14, compiles all Python sources, lints portable QML, executes pytest and records a quick renderer benchmark.

Typical local checks are:

```bash
python -m pip install --group ./pyproject.toml:dev
python -m ruff check config core ui scripts main.py
python -m compileall -q config core ui scripts main.py
python -m pytest -q
python scripts/benchmark_renderer.py --quick
bash -n install.sh scripts/local_desktop_gate.sh
```

The renderer benchmark is observational rather than a hard CI performance threshold; optimizations should be introduced only when measurements justify their complexity.

## Installation

MagicScribe is intentionally a **repo-based desktop application**, not a wheel/PyPI package. From a checkout on the target KDE/Wayland system:

```bash
bash install.sh
```

The installer creates `.venv`, installs the pinned `runtime` dependency group, verifies Qt/Wayland/layer-shell compatibility, lints the complete QML module, installs application icons and creates the XDG `.desktop` entry.

The desktop entry points to the current checkout. Moving or deleting the repository therefore invalidates that launcher; after moving the checkout, run `bash install.sh` again. This is an explicit deployment model rather than an accidental packaging contract.

## Permanent desktop regression gate

CI cannot validate compositor-specific behavior. Run the permanent acceptance harness on the target KDE Plasma Wayland desktop after changes involving windows, QML shell behavior, input, shortcuts, drawing, dependencies or lifecycle:

```bash
bash scripts/local_desktop_gate.sh
```

The gate verifies native Wayland selection, KDE layer-shell activation, one overlay surface per `QScreen`, Portal registration/fallback, stacking, Alt+Tab exclusion, toolbar/floating drag, exact 1:1 minimize/restore, immediate click-through, all drawing tools, undo/redo/clear/visibility, memory evidence and graceful shutdown. Multi-monitor checks become `N/A` only when the machine genuinely has one `QScreen`; any real `SKIP` leaves the gate incomplete.

## Visual system

The production UI is Qt Quick only. Visual tokens live in `ui/qml/MagicScribe/Theme.qml`: dark surface `#141414`, accent `#ff6600`, Noto Sans and centralized radii/animation timings. Historical QWidget/QSS UI and migration-only compatibility paths are not part of the runtime.

## License

MagicScribe is released under the **MIT License**. You may use, copy, modify, merge, publish, distribute, sublicense and sell the software, provided that the copyright notice and MIT permission notice are retained in copies or substantial portions of the software. See `LICENSE` for the complete terms.
