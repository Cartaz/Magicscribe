"""Read-only Qt model derived from the canonical tool specifications."""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from core.models import TOOL_SPECS


class ToolListModel(QAbstractListModel):
    ToolIdRole = Qt.ItemDataRole.UserRole + 1
    DisplayLabelRole = Qt.ItemDataRole.UserRole + 2
    SupportsColorRole = Qt.ItemDataRole.UserRole + 3

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(TOOL_SPECS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(TOOL_SPECS):
            return None
        spec = TOOL_SPECS[index.row()]
        if role == self.ToolIdRole:
            return spec.key
        if role in (self.DisplayLabelRole, Qt.ItemDataRole.DisplayRole):
            return spec.label
        if role == self.SupportsColorRole:
            return spec.supports_color
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.ToolIdRole: b"toolId",
            self.DisplayLabelRole: b"displayLabel",
            self.SupportsColorRole: b"supportsColor",
        }
