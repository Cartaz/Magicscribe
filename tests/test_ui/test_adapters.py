"""Behavioral tests for the QML adapters and tool model."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QPointF

from config.settings import Settings
from core.app_controller import AppController
from core.models import Point, Stroke, TOOL_SPECS, ToolType
from ui.adapters.drawing_adapter import DrawingAdapter
from ui.adapters.shell_adapter import ShellAdapter
from ui.adapters.tool_adapter import ToolAdapter
from ui.models.tool_list_model import ToolListModel


def _controller(tmp_path) -> AppController:
    return AppController(Settings(path=tmp_path / "adapter.json"))


def test_drawing_adapter_actions_and_close(tmp_path) -> None:
    controller = _controller(tmp_path)
    adapter = DrawingAdapter(controller)
    active_changes: list[bool] = []
    history_changes: list[int] = []
    adapter.activeChanged.connect(lambda: active_changes.append(adapter.active))
    adapter.historyChanged.connect(lambda: history_changes.append(adapter.strokeCount))

    adapter.toggle_drawing()
    controller.finalize_stroke(Stroke(tool_type=ToolType.PEN, points=[Point(1, 2)]))
    assert adapter.active is True
    assert adapter.canUndo is True
    assert active_changes == [True]
    assert history_changes == [1]

    adapter.close()
    controller.toggle_drawing()
    assert active_changes == [True]


def test_tool_adapter_uses_controller_boundary_only(tmp_path) -> None:
    controller = _controller(tmp_path)
    adapter = ToolAdapter(controller)
    adapter.select_tool("circle")
    adapter.set_color("#00ff00")
    adapter.set_size(12)
    assert adapter.currentTool == "circle"
    assert adapter.currentColor == "#00ff00"
    assert adapter.currentSize == 12.0

    adapter.select_tool("eraser")
    assert adapter.colorAvailable is False
    adapter.close()


def test_tool_adapter_rejects_invalid_values(tmp_path) -> None:
    controller = _controller(tmp_path)
    adapter = ToolAdapter(controller)
    adapter.select_tool("laser")
    adapter.set_size(0)
    adapter.set_color("not-a-color")
    assert adapter.currentTool == "pen"
    assert adapter.currentSize == 5.0
    assert adapter.currentColor == "#ff0000"
    adapter.close()


def test_qml_adapters_never_alias_slot_names() -> None:
    root = Path(__file__).resolve().parents[2]
    alias_pattern = re.compile(r"^\s*@Slot\([^)]*\bname\s*=", re.MULTILINE)
    for relative_path in (
        "ui/adapters/drawing_adapter.py",
        "ui/adapters/tool_adapter.py",
        "ui/adapters/shell_adapter.py",
    ):
        assert alias_pattern.search((root / relative_path).read_text(encoding="utf-8")) is None


def test_shell_adapter_only_uses_public_coordinator_api() -> None:
    class FakeCoordinator:
        def __init__(self) -> None:
            self.calls: list[object] = []

        def control_logo_center(self) -> QPointF:
            return QPointF(100, 200)

        def set_control_input_region(self, *args) -> None:
            self.calls.append(("control", args))

        def set_floating_input_region(self, *args) -> None:
            self.calls.append(("floating", args))

        def minimize_to_floating(self) -> None:
            self.calls.append("minimize")

        def restore_control_panel(self) -> None:
            self.calls.append("restore")

        def quit_application(self) -> None:
            self.calls.append("quit")

    coordinator = FakeCoordinator()
    adapter = ShellAdapter(coordinator)  # type: ignore[arg-type]
    assert adapter.controlLogoCenterX == 100
    assert adapter.controlLogoCenterY == 200
    adapter.set_control_input_region(1, 2, 3, 4)
    adapter.set_floating_input_region(5, 6, 7, 8)
    adapter.minimize_to_floating()
    adapter.restore_control_panel()
    assert coordinator.calls == [
        ("control", (1.0, 2.0, 3.0, 4.0)),
        ("floating", (5.0, 6.0, 7.0, 8.0)),
        "minimize",
        "restore",
    ]


def test_tool_list_model_is_derived_from_canonical_specs() -> None:
    model = ToolListModel()
    assert model.rowCount() == len(TOOL_SPECS)
    for row, spec in enumerate(TOOL_SPECS):
        index = model.index(row, 0)
        assert model.data(index, model.ToolIdRole) == spec.key
        assert model.data(index, model.DisplayLabelRole) == spec.label
        assert model.data(index, model.GlyphRole) == spec.glyph
        assert model.data(index, model.SupportsColorRole) is spec.supports_color
