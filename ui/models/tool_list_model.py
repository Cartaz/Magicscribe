"""Read-only QML presentation model derived from canonical domain tools."""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from core.models import TOOL_SPECS, ToolType

_LABELS: dict[ToolType, str] = {
    ToolType.PEN: "Penna",
    ToolType.ERASER: "Gomma",
    ToolType.LINE: "Linea",
    ToolType.RECT: "Rett.",
    ToolType.CIRCLE: "Cerchio",
    ToolType.SMOOTH: "Smuss.",
}


class ToolListModel(QAbstractListModel):
    ToolIdRole = Qt.ItemDataRole.UserRole + 1
    DisplayLabelRole = Qt.ItemDataRole.UserRole + 2

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(TOOL_SPECS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(TOOL_SPECS):
            return None
        spec = TOOL_SPECS[index.row()]
        if role == self.ToolIdRole:
            return spec.key
        if role in (self.DisplayLabelRole, Qt.ItemDataRole.DisplayRole):
            return _LABELS[spec.tool_type]
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.ToolIdRole: b"toolId",
            self.DisplayLabelRole: b"displayLabel",
        }
