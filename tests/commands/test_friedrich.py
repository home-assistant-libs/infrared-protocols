"""Tests for friedrich protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.friedrich import FriedrichCommand


@pytest.mark.parametrize(
    "mode,temperature",
    [
        pytest.param(ClimateMode.HEAT, 60, id="heat-min"),
        pytest.param(ClimateMode.HEAT, 88, id="heat-max"),
        pytest.param(ClimateMode.COOL, 64, id="cool-min"),
        pytest.param(ClimateMode.COOL, 88, id="cool-max"),
    ],
)
def test_friedrich_economy_boundaries(mode: ClimateMode, temperature: int) -> None:
    """Native even-degree Fahrenheit endpoints and economy decode together."""
    sent = FriedrichCommand(mode=mode, temperature_f=temperature, economy=True)
    received = FriedrichCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.temperature_f == temperature
    assert received.state.temperature == pytest.approx((temperature - 32) * 5 / 9)
    assert received.economy
