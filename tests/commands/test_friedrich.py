"""Tests for friedrich protocol behavior."""

import pytest

from infrared_protocols.commands.friedrich import FriedrichCommand, FriedrichMode


@pytest.mark.parametrize(
    "mode,temperature",
    [
        pytest.param(FriedrichMode.HEAT, 60, id="heat-min"),
        pytest.param(FriedrichMode.HEAT, 88, id="heat-max"),
        pytest.param(FriedrichMode.COOL, 64, id="cool-min"),
        pytest.param(FriedrichMode.COOL, 88, id="cool-max"),
    ],
)
def test_friedrich_economy_boundaries(mode: FriedrichMode, temperature: int) -> None:
    """Native even-degree Fahrenheit endpoints and economy decode together."""
    sent = FriedrichCommand(mode=mode, temperature=temperature, economy=True)
    received = FriedrichCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == temperature
    assert received.state.is_fahrenheit is True
    assert received.economy


def test_reject_celsius() -> None:
    """Fahrenheit-only remotes reject a conflicting unit argument."""
    with pytest.raises(ValueError, match="only supports Fahrenheit"):
        FriedrichCommand(mode=FriedrichMode.COOL, temperature=24, is_fahrenheit=False)
