"""Read-only QML presentation model derived from canonical domain tools."""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from core.models import TOOL_SPECS, ToolType

_PRESENTATION: dict[ToolType, tuple[str, str]] = {
    ToolType.PEN: ("Penna", "P"),
    ToolType.ERASER: ("Gomma", "G"),
    ToolType.LINE: ("Linea", "/"),
    ToolType.RECT: ("Rett.", "[ ]"),
    ToolType.CIRCLE: ("Cerchio", "O"),
    ToolType.SMOOTH: ("Smuss.", "~"),
}


class ToolListModel(QAbstractListModel):
    ToolIdRole = Qt.ItemDataRole.UserRole + 1
    DisplayLabelRole = Qt.ItemDataRole.UserRole + 2
    GlyphRole = Qt.ItemDataRole.UserRole + 3
    SupportsColorRole = Qt.ItemDataRole.UserRole + 4

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(TOOL_SPECS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(TOOL_SPECS):
            return None
        spec = TOOL_SPECS[index.row()]
        label, glyph = _PRESENTATION[spec.tool_type]
        if role == self.ToolIdRole:
            return spec.key
        if role in (self.DisplayLabelRole, Qt.ItemDataRole.DisplayRole):
            return label
        if role == self.GlyphRole:
            return glyph
        if role == self.SupportsColorRole:
            return spec.supports_color
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.ToolIdRole: b"toolId",
            self.DisplayLabelRole: b"displayLabel",
            self.GlyphRole: b"glyph",
            self.SupportsColorRole: b"supportsColor",
        }
