from core.models import DrawingState


def test_drawing_state_contains_only_operational_states():
    assert tuple(DrawingState) == (DrawingState.INACTIVE, DrawingState.ACTIVE)
