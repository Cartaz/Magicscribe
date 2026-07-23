"""Finestra principale di controllo di MagicScribe.

Pannello di controllo per gestire tutte le funzionalita'
dell'applicazione: attivazione disegno, strumenti, colori,
undo/redo, visibilita', cancellazione.

La chiusura tramite X o Ctrl+Q termina completamente
l'applicazione (override utente: chiusura immediata).
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication

from core.models import ToolType
from core.app_controller import AppController
from core.event_bus import event_bus
from config.constants import HotkeyDefaults
from ui.widgets.status_indicator import StatusIndicator
from ui.widgets.action_button import ActionButton
from ui.widgets.card import Card
from ui.widgets.tool_selector import ToolSelector
from ui.widgets.color_size_picker import ColorSizePicker
from ui.widgets.floating_icon import FloatingIcon
from ui.main_window_components import (
    build_header, build_separator, build_footer,
)

logger = logging.getLogger(__name__)


class MainWindow(QWidget):
    """Finestra principale di controllo di MagicScribe.

    WindowStaysOnTopHint per stare sopra l'overlay.
    La chiusura tramite X termina completamente l'app.

    Attributes:
        _controller: riferimento al controller dell'app.
        _is_minimized: se la GUI e' ridotta a icona volante.
        _overlay: riferimento all'overlay per il fallback click.
    """

    def __init__(
        self,
        controller: AppController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._status_indicator: StatusIndicator | None = None
        self._tool_selector: ToolSelector | None = None
        self._color_size_picker: ColorSizePicker | None = None
        self._is_minimized: bool = False
        self._last_pos: QPoint | None = None

        self._floating_icon = FloatingIcon(
            on_clicked=self._restore_from_floating,
        )
        self._overlay: QWidget | None = None

        self._build_ui()
        self._connect_events()
        self._register_shortcuts()
        self._refresh_state()

    # ── Costruzione UI ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Costruisce l'interfaccia della finestra principale."""
        self.setWindowTitle("MagicScribe")
        self.setMinimumWidth(300)
        self.setMaximumWidth(360)
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────
        self._status_indicator = StatusIndicator(
            size=10,
        )
        root.addLayout(build_header(self._status_indicator))

        # ── Status bar ───────────────────────────────────────────────
        self._status_label = QLabel("Disegno disattivato")
        self._status_label.setObjectName("status_label")
        root.addWidget(self._status_label)
        root.addWidget(build_separator())

        # ── Card: Disegno ────────────────────────────────────────────
        card_draw = Card("Disegno")
        self._btn_toggle = ActionButton(
            "Attiva / Disattiva disegno", HotkeyDefaults.TOGGLE_DRAW,
            self._controller.toggle_drawing, obj_name="btn_primary",
        )
        self._btn_visibility = ActionButton(
            "Mostra / Nascondi", HotkeyDefaults.TOGGLE_VISIBILITY,
            self._controller.toggle_visibility,
        )
        self._btn_clear = ActionButton(
            "Cancella schermo", HotkeyDefaults.CLEAR,
            self._controller.clear_screen, obj_name="btn_danger",
        )
        card_draw.add_widget(self._btn_toggle)
        card_draw.add_widget(self._btn_visibility)
        card_draw.add_spacing(8)
        card_draw.add_widget(self._btn_clear)
        root.addWidget(card_draw)

        # ── Card: Cronologia ─────────────────────────────────────────
        card_history = Card("Cronologia")
        self._btn_undo = ActionButton(
            "Annulla tratto", HotkeyDefaults.UNDO,
            self._controller.undo,
        )
        self._btn_redo = ActionButton(
            "Ripristina tratto", HotkeyDefaults.REDO,
            self._controller.redo,
        )
        card_history.add_widget(self._btn_undo)
        card_history.add_widget(self._btn_redo)
        root.addWidget(card_history)

        # ── Card: Strumenti ──────────────────────────────────────────
        card_tools = Card("Strumenti")
        self._tool_selector = ToolSelector()
        self._tool_selector.tool_selected.connect(self._on_tool_selected)
        card_tools.add_widget(self._tool_selector)

        self._color_size_picker = ColorSizePicker()
        self._color_size_picker.color_changed.connect(self._on_color_changed)
        self._color_size_picker.size_changed.connect(self._on_size_changed)
        card_tools.add_widget(self._color_size_picker)
        root.addWidget(card_tools)

        # ── Footer con pulsante minimizza ────────────────────────────
        root.addWidget(build_separator())
        root.addLayout(
            build_footer(self._minimize_to_floating, HotkeyDefaults.MINIMIZE),
        )
        self.adjustSize()

    # ── Icona volante ────────────────────────────────────────────────────

    def _minimize_to_floating(self) -> None:
        """Nasconde la GUI e mostra l'icona volante."""
        self._is_minimized = True
        self._last_pos = self.pos()
        self.hide()
        self._floating_icon.show_at()
        self._floating_icon.raise_()
        logger.info("GUI ridotta a icona volante")

    def _restore_from_floating(self) -> None:
        """Ripristina la GUI dall'icona volante.

        Metodo pubblico: usato dal tray icon e dal floating icon.
        """
        self._is_minimized = False
        self._floating_icon.hide()
        if self._last_pos is not None:
            self.move(self._last_pos)
        self.show()
        self.raise_()
        self.activateWindow()
        logger.info("GUI ripristinata dall'icona volante")

    def is_minimized_to_floating(self) -> bool:
        """Se la GUI e' ridotta a icona volante."""
        return self._is_minimized

    def restore_from_floating(self) -> None:
        """Alias pubblico per _restore_from_floating (per client esterni)."""
        self._restore_from_floating()

    def set_overlay(self, overlay: QWidget) -> None:
        """Imposta il riferimento all'overlay per il fallback click.

        Args:
            overlay: finestra overlay di disegno.
        """
        self._overlay = overlay
        if overlay:
            overlay.set_floating_icon(self._floating_icon)

    # ── Eventi ───────────────────────────────────────────────────────────

    def _connect_events(self) -> None:
        """Connette i segnali dell'event bus."""
        event_bus.subscribe("drawing_toggled", self._on_drawing_toggled)
        event_bus.subscribe("visibility_toggled", self._on_visibility_toggled)
        event_bus.subscribe("strokes_changed", self._on_strokes_changed)
        event_bus.subscribe("tool_changed", self._on_tool_changed_evt)

    def _register_shortcuts(self) -> None:
        """Registra le scorciatoie da tastiera sulla finestra principale."""
        shortcuts = [
            (HotkeyDefaults.TOGGLE_DRAW, self._controller.toggle_drawing),
            (HotkeyDefaults.TOGGLE_VISIBILITY, self._controller.toggle_visibility),
            (HotkeyDefaults.CLEAR, self._controller.clear_screen),
            (HotkeyDefaults.UNDO, self._controller.undo),
            (HotkeyDefaults.REDO, self._controller.redo),
            (HotkeyDefaults.MINIMIZE, self._minimize_to_floating),
            (HotkeyDefaults.QUIT_APP, self.close),
        ]
        for key, slot in shortcuts:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)

    # ── Handler eventi ───────────────────────────────────────────────────

    def _on_drawing_toggled(self, active: bool, **kwargs) -> None:
        """Aggiorna l'UI e si assicura di stare sopra l'overlay."""
        self._refresh_state()
        if self.isVisible():
            QTimer.singleShot(100, self._raise_above_overlay)
        if self._floating_icon.isVisible():
            QTimer.singleShot(80, self._floating_icon.raise_)

    def _raise_above_overlay(self) -> None:
        """Solleva la GUI sopra l'overlay."""
        self.raise_()
        self.activateWindow()

    def _on_visibility_toggled(self, visible: bool, **kwargs) -> None:
        """Aggiorna l'UI quando la visibilita' cambia."""
        self._refresh_state()
        self.raise_()

    def _on_strokes_changed(self, **kwargs) -> None:
        """Aggiorna i pulsanti undo/redo."""
        self._update_undo_redo_state()

    def _on_tool_changed_evt(self, new_tool: ToolType, **kwargs) -> None:
        """Aggiorna l'UI quando lo strumento cambia."""
        if self._tool_selector:
            self._tool_selector.set_current_tool(new_tool)
        config = self._controller.tool_manager.config_for(new_tool)
        if self._color_size_picker:
            self._color_size_picker.set_tool(new_tool, config.color, config.size)

    def _on_tool_selected(self, tool: ToolType) -> None:
        """Handler per la selezione strumento dal selettore."""
        self._controller.set_tool(tool)
        config = self._controller.tool_manager.config_for(tool)
        if self._color_size_picker:
            self._color_size_picker.set_tool(tool, config.color, config.size)

    def _on_color_changed(self, color: str) -> None:
        """Handler per il cambio colore dal picker."""
        tool = self._controller.get_current_tool()
        self._controller.tool_manager.set_color(tool, color)

    def _on_size_changed(self, size: float) -> None:
        """Handler per il cambio dimensione dal picker."""
        tool = self._controller.get_current_tool()
        self._controller.tool_manager.set_size(tool, size)

    # ── Aggiornamento stato ──────────────────────────────────────────────

    def _refresh_state(self) -> None:
        """Aggiorna l'intera UI in base allo stato corrente."""
        active = self._controller.is_drawing_active()

        if active:
            self._status_indicator.set_state("running")
            self._status_label.setText("Disegno ATTIVO")
            self._btn_toggle.set_text(
                "Disegno ATTIVO — clicca per disattivare",
            )
            self._btn_toggle.set_object_name("btn_active")
        else:
            self._status_indicator.set_state("stopped")
            self._status_label.setText("Disegno disattivato")
            self._btn_toggle.set_text("Attiva / Disattiva disegno")
            self._btn_toggle.set_object_name("btn_primary")

        self._btn_visibility.set_enabled(active)
        self._btn_clear.set_enabled(active)
        self._update_undo_redo_state()

    def _update_undo_redo_state(self) -> None:
        """Aggiorna lo stato dei pulsanti undo/redo."""
        sm = self._controller.stroke_manager
        self._btn_undo.set_enabled(sm.can_undo)
        self._btn_redo.set_enabled(sm.can_redo)

    # ── Chiusura ────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        """Chiude completamente l'applicazione (override utente)."""
        if self._floating_icon.isVisible():
            self._floating_icon.hide()
        event.accept()
        QApplication.quit()
        logger.info("Applicazione chiusa dall'utente")
