"""Tests for whynter protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.whynter import WhynterCommand


@pytest.mark.parametrize(
    "temperature,fahrenheit,celsius",
    [
        pytest.param(16, False, 16, id="c-min"),
        pytest.param(32, False, 32, id="c-max"),
        pytest.param(61, True, (61 - 32) * 5 / 9, id="f-min"),
        pytest.param(75, True, (75 - 32) * 5 / 9, id="f-normal"),
        pytest.param(89, True, (89 - 32) * 5 / 9, id="f-max"),
    ],
)
def test_whynter_native_units(
    temperature: int, fahrenheit: bool, celsius: float
) -> None:
    """Native units and set points survive decoding without rounding."""
    sent = WhynterCommand(
        mode=ClimateMode.COOL, temperature=temperature, fahrenheit=fahrenheit
    )
    received = WhynterCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fahrenheit is fahrenheit
    assert received.temperature == temperature
    assert received.state.temperature == celsius
