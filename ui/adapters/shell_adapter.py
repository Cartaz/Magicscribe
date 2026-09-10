"""Adapter QML per le azioni della shell applicativa."""

from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, QPointF, Property, QRect, QTimer, Signal, Slot
from PySide6.QtGui import QCursor, QRegion
from PySide6.QtQuick import QQuickItem

from config.constants import HotkeyDefaults
from ui.native.global_shortcuts import GlobalShortcutService
from ui.native.window_coordinator import WindowCoordinator


class ShellAdapter(QObject):
    """API QML minimale per finestra, minimizzazione e lifecycle."""

    globalDrawingShortcutsActiveChanged = Signal()

    def __init__(
        self,
        coordinator: WindowCoordinator,
        global_shortcuts: GlobalShortcutService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._coordinator = coordinator
        self._global_shortcuts = global_shortcuts
        if global_shortcuts is not None:
            global_shortcuts.activeChanged.connect(
                self.globalDrawingShortcutsActiveChanged.emit
            )

    @Property(str, constant=True)
    def toggleDrawingShortcut(self) -> str:
        return HotkeyDefaults.TOGGLE_DRAW

    @Property(str, constant=True)
    def visibilityShortcut(self) -> str:
        return HotkeyDefaults.TOGGLE_VISIBILITY

    @Property(str, constant=True)
    def clearShortcut(self) -> str:
        return HotkeyDefaults.CLEAR

    @Property(str, constant=True)
    def undoShortcut(self) -> str:
        return HotkeyDefaults.UNDO

    @Property(str, constant=True)
    def redoShortcut(self) -> str:
        return HotkeyDefaults.REDO

    @Property(str, constant=True)
    def minimizeShortcut(self) -> str:
        return HotkeyDefaults.MINIMIZE

    @Property(str, constant=True)
    def quitShortcut(self) -> str:
        return HotkeyDefaults.QUIT_APP

    @Property(bool, notify=globalDrawingShortcutsActiveChanged)
    def globalDrawingShortcutsActive(self) -> bool:
        service = self._global_shortcuts
        return service is not None and service.active

    def _control_panel_coordinate(self, name: str, fallback: float) -> float:
        window = self._coordinator._control_window
        if window is None:
            return fallback
        value = window.property(name)
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    @Property(float)
    def controlPanelX(self) -> float:
        return self._control_panel_coordinate("layerShellPanelX", 20.0)

    @Property(float)
    def controlPanelY(self) -> float:
        return self._control_panel_coordinate("layerShellPanelY", 20.0)

    def _control_logo_center(self) -> QPointF:
        """Centro del pulsante logo nelle coordinate della control surface.

        Il mapping parte dal QQuickItem reale, quindi include automaticamente
        margini, Column/Flickable e l'eventuale contentY. Questo evita offset
        hard-coded tra toolbar e floating palette.
        """
        window = self._coordinator._control_window
        if window is not None:
            logo = window.findChild(QQuickItem, "minimizeButton")
            if logo is not None:
                return logo.mapToScene(
                    QPointF(logo.width() / 2.0, logo.height() / 2.0)
                )

        # Fallback coerente con il layout corrente, usato solo se il QML non e'
        # ancora completamente materializzato quando viene interrogato.
        return QPointF(
            self._control_panel_coordinate("layerShellPanelX", 20.0) + 52.0,
            self._control_panel_coordinate("layerShellPanelY", 20.0) + 50.0,
        )

    @Property(float)
    def controlLogoCenterX(self) -> float:
        return self._control_logo_center().x()

    @Property(float)
    def controlLogoCenterY(self) -> float:
        return self._control_logo_center().y()

    def _floating_palette_center(self) -> QPointF | None:
        """Centro corrente della floating icon nella sua layer-surface."""
        window = self._coordinator._floating_window
        if window is None:
            return None

        try:
            x = float(window.property("layerShellPaletteX"))
            y = float(window.property("layerShellPaletteY"))
            width = float(window.property("paletteWidth"))
            height = float(window.property("paletteHeight"))
        except (TypeError, ValueError):
            return None
        return QPointF(x + width / 2.0, y + height / 2.0)

    def _align_control_logo_to_floating(self) -> None:
        """Allinea 1:1 il logo toolbar alla floating icon prima del restore.

        Le due layer-surface Wayland sono fullscreen e condividono lo stesso
        sistema di coordinate. Trasliamo soltanto ``toolbarHost`` del delta tra
        i due centri: il logo della toolbar riappare quindi esattamente dove si
        trovava la floating icon, anche dopo averla trascinata.
        """
        if self._coordinator._absolute_positioning:
            return

        control = self._coordinator._control_window
        floating_center = self._floating_palette_center()
        if control is None or floating_center is None:
            return

        logo_center = self._control_logo_center()
        panel_x = self._control_panel_coordinate("layerShellPanelX", 20.0)
        panel_y = self._control_panel_coordinate("layerShellPanelY", 20.0)

        control.setProperty(
            "layerShellPanelX",
            panel_x + floating_center.x() - logo_center.x(),
        )
        control.setProperty(
            "layerShellPanelY",
            panel_y + floating_center.y() - logo_center.y(),
        )

    @Slot(result=QPoint)
    def global_cursor_position(self) -> QPoint:
        """Restituisce l'ultima posizione globale del puntatore nota a Qt."""
        return QCursor.pos()

    def _set_window_input_region(
        self,
        window_attr: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        region = QRegion(
            QRect(
                round(x),
                round(y),
                max(1, round(width)),
                max(1, round(height)),
            )
        )

        def apply_region() -> None:
            # ShellAdapter e WindowCoordinator costituiscono lo stesso boundary UI;
            # le finestre vengono associate subito dopo la creazione QML.
            window = getattr(self._coordinator, window_attr)
            if window is not None:
                window.setMask(region)

        apply_region()
        # QWindow::setMask prima della creazione native non ha effetto; ripetiamo
        # nel prossimo giro dell'event loop per coprire il primo show().
        QTimer.singleShot(0, apply_region)

    @Slot(float, float, float, float)
    def set_control_input_region(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Limita l'input della control surface fullscreen al pannello visibile."""
        self._set_window_input_region(
            "_control_window", x, y, width, height
        )

    @Slot(float, float, float, float)
    def set_floating_input_region(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Limita l'input della floating surface fullscreen alla palette visibile."""
        self._set_window_input_region(
            "_floating_window", x, y, width, height
        )

    @Slot()
    def minimize_to_floating(self) -> None:
        self._coordinator.minimize_to_floating()

    @Slot()
    def restore_control_panel(self) -> None:
        self._align_control_logo_to_floating()
        self._coordinator.restore_control_panel()

    @Slot()
    def quit_application(self) -> None:
        self._coordinator.quit_application()
