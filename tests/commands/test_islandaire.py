"""Tests for Islandaire native temperature units."""

import pytest

from infrared_protocols.commands.islandaire import (
    IslandaireCommand,
    IslandaireFanSpeed,
    IslandaireMode,
)


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
    assert received.state.temperature == temperature
    assert received.state.is_fahrenheit is True


def test_reject_celsius() -> None:
    """Fahrenheit-only remotes reject a conflicting unit argument."""
    with pytest.raises(ValueError, match="only supports Fahrenheit"):
        IslandaireCommand(mode=IslandaireMode.COOL, temperature=24, is_fahrenheit=False)


@pytest.mark.parametrize("fan", list(IslandaireFanSpeed), ids=lambda fan: fan.name)
def test_native_fan_codes(fan: IslandaireFanSpeed) -> None:
    """The alternative low-speed code remains distinct when a state is rebuilt."""
    command = IslandaireCommand(mode=IslandaireMode.COOL, temperature=72, fan=fan)
    assert command.data[8] == int(fan)
    received = IslandaireCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    state = received.state
    assert state.fan is fan
    assert state.fan is not None
    rebuilt = IslandaireCommand(mode=IslandaireMode.COOL, temperature=72, fan=state.fan)
    assert rebuilt.data == command.data
