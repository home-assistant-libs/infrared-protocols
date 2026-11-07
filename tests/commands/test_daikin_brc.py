"""Tests for daikin brc protocol behavior."""

import pytest

from infrared_protocols.commands.daikin_brc import (
    DaikinBrcCommand,
    DaikinBrcMode,
)


@pytest.mark.parametrize("sub_unit", [0, 1])
@pytest.mark.parametrize("mode_button", [False, True])
def test_brc_fahrenheit(sub_unit: int, mode_button: bool) -> None:
    """The constructor and decoded state use native Fahrenheit."""
    sent = DaikinBrcCommand(
        mode=DaikinBrcMode.COOL,
        temperature=72,
        is_fahrenheit=True,
        sub_unit=sub_unit,
        mode_button=mode_button,
    )
    received = DaikinBrcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == 72
    assert received.state.is_fahrenheit is True
    assert received.sub_unit == sub_unit
    assert received.mode_button == mode_button


@pytest.mark.parametrize("mode", list(DaikinBrcMode))
@pytest.mark.parametrize(
    "temperature,is_fahrenheit",
    [pytest.param(24, False, id="celsius"), pytest.param(72, True, id="fahrenheit")],
)
def test_brc_temperature_units(
    temperature: int, is_fahrenheit: bool, mode: DaikinBrcMode
) -> None:
    """The receiver identifies native units from the disjoint wire ranges."""
    sent = DaikinBrcCommand(
        mode=mode, temperature=temperature, is_fahrenheit=is_fahrenheit
    )
    received = DaikinBrcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.is_fahrenheit is is_fahrenheit
    assert received.state == sent.state


def test_brc_rejects_fractional_celsius_wire_value() -> None:
    """An odd temperature byte is not a valid whole-degree Celsius set point."""
    sent = DaikinBrcCommand(mode=DaikinBrcMode.COOL, temperature=24)
    data = bytearray(sent.data)
    data[17] += 1
    data[-1] = (data[-1] + 1) & 255
    sent.data = bytes(data)
    assert DaikinBrcCommand.from_raw_timings(sent.get_raw_timings()) is None


@pytest.mark.parametrize(
    "temperature,is_fahrenheit",
    [
        pytest.param(16, False, id="celsius-minimum"),
        pytest.param(24, False, id="celsius"),
        pytest.param(32, False, id="celsius-maximum"),
        pytest.param(60, True, id="fahrenheit-minimum"),
        pytest.param(75, True, id="fahrenheit"),
        pytest.param(90, True, id="fahrenheit-maximum"),
    ],
)
def test_native_temperature(temperature: int, is_fahrenheit: bool) -> None:
    """BRC readback retains native units and an exact native set point."""
    command = DaikinBrcCommand(
        mode=DaikinBrcMode.COOL, temperature=temperature, is_fahrenheit=is_fahrenheit
    )
    received = DaikinBrcCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.is_fahrenheit is is_fahrenheit
    assert received.temperature == temperature
    assert received.state.temperature == temperature
    assert isinstance(received.temperature, int)
    rebuilt = DaikinBrcCommand(
        mode=DaikinBrcMode.COOL,
        temperature=received.temperature,
        is_fahrenheit=received.is_fahrenheit,
    )
    assert rebuilt.get_raw_timings() == command.get_raw_timings()
