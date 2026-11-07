"""Tests for Islandaire native temperature units."""

import pytest

from infrared_protocols.commands.islandaire import IslandaireCommand, IslandaireMode


@pytest.mark.parametrize(
    "temperature",
    [pytest.param(61, id="minimum"), pytest.param(88, id="maximum")],
)
def test_native_temperature(temperature: int) -> None:
    """Both native endpoints retain Fahrenheit in command and state readback."""
    command = IslandaireCommand(
        mode=IslandaireMode.COOL, temperature=temperature, is_fahrenheit=True
    )
    received = IslandaireCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.temperature == temperature
    assert received.state.temperature == temperature
    assert received.is_fahrenheit is True
    assert received.state.is_fahrenheit is True


def test_reject_celsius() -> None:
    """Fahrenheit-only remotes reject a conflicting unit argument."""
    with pytest.raises(ValueError, match="only supports Fahrenheit"):
        IslandaireCommand(mode=IslandaireMode.COOL, temperature=24, is_fahrenheit=False)
