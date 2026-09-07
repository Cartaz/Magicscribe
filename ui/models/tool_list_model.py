"""Modello Qt degli strumenti disponibili alla UI QML."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from core.models import ToolType


@dataclass(frozen=True)
class _ToolPresentation:
    tool_type: ToolType
    label: str
    glyph: str
    supports_color: bool = True


_TOOLS = (
    _ToolPresentation(ToolType.PEN, "Penna", "P"),
    _ToolPresentation(ToolType.ERASER, "Gomma", "G", False),
    _ToolPresentation(ToolType.LINE, "Linea", "/"),
    _ToolPresentation(ToolType.RECT, "Rett.", "[ ]"),
    _ToolPresentation(ToolType.CIRCLE, "Cerchio", "O"),
    _ToolPresentation(ToolType.SMOOTH, "Smuss.", "~"),
)


class ToolListModel(QAbstractListModel):
    """Lista stabile e read-only degli strumenti presentabili."""

    ToolIdRole = Qt.ItemDataRole.UserRole + 1
    DisplayLabelRole = Qt.ItemDataRole.UserRole + 2
    GlyphRole = Qt.ItemDataRole.UserRole + 3
    SupportsColorRole = Qt.ItemDataRole.UserRole + 4

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(_TOOLS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(_TOOLS):
            return None

        tool = _TOOLS[index.row()]
        if role == self.ToolIdRole:
            return tool.tool_type.name.lower()
        if role in (self.DisplayLabelRole, Qt.ItemDataRole.DisplayRole):
            return tool.label
        if role == self.GlyphRole:
            return tool.glyph
        if role == self.SupportsColorRole:
            return tool.supports_color
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.ToolIdRole: b"toolId",
            self.DisplayLabelRole: b"displayLabel",
            self.GlyphRole: b"glyph",
            self.SupportsColorRole: b"supportsColor",
        }
