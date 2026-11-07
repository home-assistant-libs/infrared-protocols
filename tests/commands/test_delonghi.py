"""Tests for delonghi protocol behavior."""

import pytest

from infrared_protocols.commands._climate import ClimatePacket
from infrared_protocols.commands.delonghi import (
    DelonghiCommand,
    DelonghiFanSpeed,
    DelonghiMode,
)


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


@pytest.mark.parametrize(
    "temperature,packet",
    [
        pytest.param(64, "53810100000000d5", id="minimum"),
        pytest.param(80, "53910100000000e5", id="fifth-bit"),
        pytest.param(90, "539b0100000000ef", id="maximum"),
    ],
)
def test_fahrenheit_packets(temperature: int, packet: str) -> None:
    """The unit bit and fifth temperature bit are independent of fan speed."""
    sent = DelonghiCommand(
        mode=DelonghiMode.COOL, temperature=temperature, is_fahrenheit=True
    )
    assert sent.data == bytes.fromhex(packet)
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    state = received.state
    assert state.is_fahrenheit is True
    assert state.temperature == temperature
    assert state.fan is DelonghiFanSpeed.AUTO
    assert state.mode is not None
    rebuilt = DelonghiCommand(
        mode=state.mode,
        temperature=state.temperature,
        fan=state.fan,
        is_fahrenheit=state.is_fahrenheit,
    )
    assert rebuilt.data == received.data


@pytest.mark.parametrize("fan", list(DelonghiFanSpeed))
def test_fahrenheit_fan(fan: DelonghiFanSpeed) -> None:
    """The high unit bit must not become a third fan bit."""
    sent = DelonghiCommand(
        mode=DelonghiMode.COOL, temperature=80, fan=fan, is_fahrenheit=True
    )
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.fan is fan
    assert received.state.temperature == 80
    assert received.state.is_fahrenheit is True


@pytest.mark.parametrize("mode", [DelonghiMode.AUTO, DelonghiMode.DRY])
def test_fahrenheit_placeholder(mode: DelonghiMode) -> None:
    """The native zero placeholder does not invent a 63 °F target."""
    sent = DelonghiCommand(mode=mode, temperature=None, is_fahrenheit=True)
    assert sent.data[1] == 0x80
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature is None
    assert received.state.is_fahrenheit is True


@pytest.mark.parametrize("temperature", [63, 91])
def test_invalid_fahrenheit(temperature: int) -> None:
    """The Fahrenheit endpoints are validated in their native unit."""
    with pytest.raises(ValueError, match="temperature"):
        DelonghiCommand(
            mode=DelonghiMode.COOL, temperature=temperature, is_fahrenheit=True
        )


@pytest.mark.parametrize(
    "packet,boost,sleep",
    [
        pytest.param("53910100000000e5", False, False, id="neither"),
        pytest.param("53911100000000f5", True, False, id="boost"),
        pytest.param("5391210000000005", False, True, id="sleep"),
        pytest.param("5391310000000015", True, True, id="both"),
    ],
)
def test_native_feature_bits(packet: str, boost: bool, sleep: bool) -> None:
    """Feature flags in received packets do not alter the mode or unit."""
    sent = DelonghiCommand.__new__(DelonghiCommand)
    ClimatePacket.__init__(sent, data=bytes.fromhex(packet))
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.data == bytes.fromhex(packet)
    assert received.boost is boost
    assert received.sleep is sleep
    assert received.state.mode is DelonghiMode.COOL
    assert received.state.is_fahrenheit is True
