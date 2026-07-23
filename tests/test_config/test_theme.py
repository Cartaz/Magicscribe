"""Test per config.theme.ThemeColors."""

from config.theme import ThemeColors


def test_primary_is_teal() -> None:
    """Il colore primario deve essere Teal, non blu (§5.1.1)."""
    assert ThemeColors.PRIMARY == "#00bfa5"
    assert ThemeColors.PRIMARY_DARK == "#00695c"


def test_danger_is_orange() -> None:
    """Il colore pericolo deve essere Arancione, non rosso (§5.1.2)."""
    assert ThemeColors.DANGER == "#db4105"
    assert ThemeColors.DANGER_DARK == "#7a2400"


def test_no_blue_in_tokens() -> None:
    """Nessun token di colore primario deve contenere sfumature di blu."""
    # I token di accento primario non devono essere blu
    assert "0000ff" not in ThemeColors.PRIMARY.lower()
    assert "0000ff" not in ThemeColors.PRIMARY_DARK.lower()


def test_immutable_instance() -> None:
    """L'istanza ThemeColors deve essere immutabile."""
    try:
        ThemeColors.PRIMARY = "#0000ff"
        assert False, "Non doveva essere possibile modificare ThemeColors"
    except AttributeError:
        pass
