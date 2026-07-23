"""Test per core.app_controller.AppController."""

from core.app_controller import AppController
from core.models import ToolType, DrawingState
from core.event_bus import event_bus
from config.settings import Settings


def _make_controller() -> AppController:
    """Crea un controller con impostazioni di default."""
    settings = Settings()
    return AppController(settings)


def test_toggle_drawing() -> None:
    """toggle_drawing deve cambiare lo stato tra INACTIVE e ACTIVE."""
    ctrl = _make_controller()
    assert ctrl.state.drawing_state == DrawingState.INACTIVE

    ctrl.toggle_drawing()
    assert ctrl.is_drawing_active()
    assert ctrl.state.drawing_state == DrawingState.ACTIVE

    ctrl.toggle_drawing()
    assert not ctrl.is_drawing_active()
    assert ctrl.state.drawing_state == DrawingState.INACTIVE


def test_toggle_visibility() -> None:
    """toggle_visibility deve cambiare la visibilita' delle annotazioni."""
    ctrl = _make_controller()
    assert ctrl.is_visible()

    ctrl.toggle_visibility()
    assert not ctrl.is_visible()

    ctrl.toggle_visibility()
    assert ctrl.is_visible()


def test_set_tool() -> None:
    """set_tool deve cambiare lo strumento corrente."""
    ctrl = _make_controller()
    assert ctrl.get_current_tool() == ToolType.PEN

    ctrl.set_tool(ToolType.ERASER)
    assert ctrl.get_current_tool() == ToolType.ERASER


def test_create_stroke() -> None:
    """create_stroke deve creare uno stroke con la configurazione corretta."""
    ctrl = _make_controller()
    stroke = ctrl.create_stroke(ToolType.PEN)
    assert stroke.tool_type == ToolType.PEN
    assert len(stroke.points) == 0


def test_finalize_stroke() -> None:
    """finalize_stroke deve aggiungere lo stroke alla cronologia."""
    from core.models import Stroke, Point
    ctrl = _make_controller()
    stroke = Stroke(tool_type=ToolType.PEN)
    stroke.points.append(Point(x=10, y=20))
    ctrl.finalize_stroke(stroke)
    assert ctrl.stroke_manager.stroke_count == 1
