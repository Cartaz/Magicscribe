"""Controller principale dell'applicazione MagicScribe.

Orchestra i moduli core e fornisce l'interfaccia pubblica
che il livello UI utilizza per interagire con la logica applicativa.
Non importa mai moduli Qt.
"""

from __future__ import annotations

import logging

from core.models import ToolType, DrawingState, AppState, Stroke, ToolConfig
from core.stroke_manager import StrokeManager
from core.tool_manager import ToolManager
from core.event_bus import event_bus
from config.settings import Settings
from config.constants import ToolDefaults

logger = logging.getLogger(__name__)


class AppController:
    """Controller principale dell'applicazione.

    Espone metodi tipizzati per il livello UI e coordina i proprietari
    canonici dello stato applicativo.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stroke_manager = StrokeManager(
            max_depth=ToolDefaults.UNDO_MAX_DEPTH
        )
        self._tool_manager = ToolManager(settings)
        self._state = AppState()

    # ── Proprieta' ────────────────────────────────────────────────────────

    @property
    def state(self) -> AppState:
        """Stato globale dell'applicazione (sola lettura)."""
        return self._state

    @property
    def stroke_manager(self) -> StrokeManager:
        """Gestore cronologia tratti."""
        return self._stroke_manager

    @property
    def tool_manager(self) -> ToolManager:
        """Gestore strumenti."""
        return self._tool_manager

    @property
    def settings(self) -> Settings:
        """Gestore impostazioni."""
        return self._settings

    # ── Azioni di disegno ─────────────────────────────────────────────────

    def toggle_drawing(self) -> None:
        """Attiva/disattiva la modalita' disegno."""
        if self._state.drawing_state == DrawingState.INACTIVE:
            self._state.drawing_state = DrawingState.ACTIVE
            logger.info("Disegno ATTIVATO")
        else:
            self._state.drawing_state = DrawingState.INACTIVE
            logger.info("Disegno DISATTIVATO")
        event_bus.emit(
            "drawing_toggled", active=self.is_drawing_active(),
        )

    def toggle_visibility(self) -> None:
        """Mostra/nasconde le annotazioni."""
        self._state.annotations_visible = not self._state.annotations_visible
        logger.info(
            "Visibilita' annotazioni: %s", self._state.annotations_visible,
        )
        event_bus.emit(
            "visibility_toggled", visible=self._state.annotations_visible,
        )

    def clear_screen(self) -> None:
        """Cancella tutte le annotazioni dallo schermo."""
        self._stroke_manager.clear_all()

    def undo(self) -> None:
        """Annulla l'ultimo tratto."""
        self._stroke_manager.undo()

    def redo(self) -> None:
        """Ripristina l'ultimo tratto annullato."""
        self._stroke_manager.redo()

    # ── Query di stato ────────────────────────────────────────────────────

    def is_drawing_active(self) -> bool:
        """Se la modalita' disegno e' attiva."""
        return self._state.drawing_state != DrawingState.INACTIVE

    def is_visible(self) -> bool:
        """Se le annotazioni sono visibili."""
        return self._state.annotations_visible

    # ── Creazione tratti ──────────────────────────────────────────────────

    def create_stroke(self, tool_type: ToolType) -> Stroke:
        """Crea un nuovo tratto con la configurazione corrente dello strumento."""
        config = self._tool_manager.config_for(tool_type)
        return Stroke(
            tool_type=config.tool_type,
            color=config.color,
            size=config.size,
        )

    def finalize_stroke(self, stroke: Stroke) -> None:
        """Aggiunge un tratto completato alla cronologia."""
        if stroke.points:
            self._stroke_manager.add_stroke(stroke)

    # ── Selezione strumento ───────────────────────────────────────────────

    def set_tool(self, tool_type: ToolType) -> None:
        """Seleziona uno strumento di disegno.

        ToolManager e' l'unico proprietario canonico dello strumento corrente.
        """
        self._tool_manager.set_tool(tool_type)

    def get_current_tool(self) -> ToolType:
        """Restituisce lo strumento corrente."""
        return self._tool_manager.current_tool()

    def get_current_config(self) -> ToolConfig:
        """Restituisce la configurazione dello strumento corrente."""
        return self._tool_manager.current_config()
