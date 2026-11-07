"""Tests for delonghi protocol behavior."""

import pytest

from infrared_protocols.commands.delonghi import DelonghiCommand, DelonghiMode


@pytest.mark.parametrize(
    "mode,temperature",
    [
        pytest.param(DelonghiMode.HEAT, 13, id="heat-min"),
        pytest.param(DelonghiMode.HEAT, 27, id="heat-max"),
        pytest.param(DelonghiMode.COOL, 17, id="cool-min"),
        pytest.param(DelonghiMode.COOL, 32, id="cool-max"),
    ],
)
def test_delonghi_temperature_ranges(mode: DelonghiMode, temperature: int) -> None:
    """Heating and cooling use different offsets and valid endpoints."""
    sent = DelonghiCommand(mode=mode, temperature=temperature)
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode == mode
    assert received.state.temperature == temperature


@pytest.mark.parametrize(
    "mode,temperature",
    [
        pytest.param(DelonghiMode.HEAT, 12, id="below-heat"),
        pytest.param(DelonghiMode.HEAT, 28, id="above-heat"),
        pytest.param(DelonghiMode.COOL, 16, id="below-cool"),
        pytest.param(DelonghiMode.COOL, 33, id="above-cool"),
    ],
)
def test_delonghi_invalid_temperature(mode: DelonghiMode, temperature: int) -> None:
    """A mode's temperature field cannot encode the adjacent out-of-range values."""
    with pytest.raises(ValueError, match="temperature"):
        DelonghiCommand(mode=mode, temperature=temperature)


def test_delonghi_low_heat_off() -> None:
    """Turning off a low heat setpoint does not require a cool-mode temperature."""
    sent = DelonghiCommand(mode=DelonghiMode.HEAT, temperature=15, power=False)
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.power is False
    assert received.state.temperature is None
