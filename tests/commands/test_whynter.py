"""Tests for whynter protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.whynter import WhynterCommand


def test_whynter_fahrenheit() -> None:
    """Native Fahrenheit encoding is decoded to the shared Celsius state."""
    sent = WhynterCommand(mode=ClimateMode.COOL, temperature=75, fahrenheit=True)
    received = WhynterCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == pytest.approx((75 - 32) * 5 / 9)


@pytest.mark.parametrize("temperature", [61, 75, 89])
def test_whynter_native_fahrenheit(temperature: int) -> None:
    """Native units and set points survive decoding without rounding."""
    sent = WhynterCommand(
        mode=ClimateMode.COOL, temperature=temperature, fahrenheit=True
    )
    received = WhynterCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fahrenheit
    assert received.temperature == temperature
    assert received.state.temperature == (temperature - 32) * 5 / 9
