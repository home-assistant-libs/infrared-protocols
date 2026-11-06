"""Tests for daikin brc protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.daikin_brc import (
    DaikinBrcCommand,
    DaikinBrcFahrenheitCommand,
)


@pytest.mark.parametrize("sub_unit", [0, 1])
@pytest.mark.parametrize("mode_button", [False, True])
def test_brc_fahrenheit(sub_unit: int, mode_button: bool) -> None:
    """The constructor uses native Fahrenheit; common state exposes exact Celsius."""
    sent = DaikinBrcFahrenheitCommand(
        mode=ClimateMode.COOL,
        temperature=72,
        sub_unit=sub_unit,
        mode_button=mode_button,
    )
    received = DaikinBrcFahrenheitCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == pytest.approx(22.222222)
    assert received.sub_unit == sub_unit
    assert received.mode_button == mode_button


@pytest.mark.parametrize("mode", list(ClimateMode))
@pytest.mark.parametrize(
    "sender,receiver,temp",
    [
        pytest.param(
            DaikinBrcCommand, DaikinBrcFahrenheitCommand, 24, id="celsius-as-fahrenheit"
        ),
        pytest.param(
            DaikinBrcFahrenheitCommand, DaikinBrcCommand, 72, id="fahrenheit-as-celsius"
        ),
    ],
)
def test_brc_distinct_temperature_variants(
    sender: type[DaikinBrcCommand],
    receiver: type[DaikinBrcCommand],
    temp: int,
    mode: ClimateMode,
) -> None:
    """Non-overlapping temperature encodings identify the configured variant."""
    raw = sender(mode=mode, temperature=temp).get_raw_timings()
    assert sender.from_raw_timings(raw) is not None
    assert receiver.from_raw_timings(raw) is None


def test_brc_rejects_fractional_celsius_wire_value() -> None:
    """An odd temperature byte is not a valid whole-degree Celsius set point."""
    sent = DaikinBrcCommand(mode=ClimateMode.COOL, temperature=24)
    data = bytearray(sent.data)
    data[17] += 1
    data[-1] = (data[-1] + 1) & 255
    sent.data = bytes(data)
    assert DaikinBrcCommand.from_raw_timings(sent.get_raw_timings()) is None
