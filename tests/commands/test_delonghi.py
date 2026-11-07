"""Tests for delonghi protocol behavior."""

import pytest

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
    sent = DelonghiCommand(
        mode=DelonghiMode.COOL,
        temperature=80,
        is_fahrenheit=True,
        boost=boost,
        sleep=sleep,
    )
    assert sent.data == bytes.fromhex(packet)
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.data == bytes.fromhex(packet)
    assert received.boost is boost
    assert received.sleep is sleep
    assert received.state.mode is DelonghiMode.COOL
    assert received.state.is_fahrenheit is True
    rebuilt = DelonghiCommand(
        mode=DelonghiMode.COOL,
        temperature=81,
        is_fahrenheit=received.state.is_fahrenheit,
        boost=received.boost,
        sleep=received.sleep,
    )
    assert rebuilt.data[2] == received.data[2]
    assert rebuilt.state.temperature == 81


@pytest.mark.parametrize(
    "is_fahrenheit,temperature",
    [
        pytest.param(False, None, id="celsius-placeholder"),
        pytest.param(False, 24, id="celsius-24"),
        pytest.param(False, 27, id="celsius-27"),
        pytest.param(True, None, id="fahrenheit-placeholder"),
        pytest.param(True, 74, id="fahrenheit-74"),
        pytest.param(True, 77, id="fahrenheit-77"),
    ],
)
def test_off_rebuild(temperature: int | None, is_fahrenheit: bool) -> None:
    """Off carries no set point, but a retained field can reproduce exact bytes."""
    sent = DelonghiCommand(
        mode=None,
        temperature=temperature,
        power=False,
        is_fahrenheit=is_fahrenheit,
    )
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode is None
    assert received.state.temperature is None
    rebuilt = DelonghiCommand(
        mode=received.state.mode,
        temperature=received.retained_temperature,
        power=False,
        is_fahrenheit=received.state.is_fahrenheit,
    )
    assert rebuilt.get_raw_timings() == sent.get_raw_timings()


@pytest.mark.parametrize(
    "mode,packet",
    [
        pytest.param(DelonghiMode.DRY, "530702000000005c", id="retained-dry"),
        pytest.param(DelonghiMode.FAN_ONLY, "530704000000005e", id="retained-fan"),
        pytest.param(DelonghiMode.AUTO, "5307080000000062", id="retained-auto"),
    ],
)
def test_retained_off_mode(mode: DelonghiMode, packet: str) -> None:
    """Off packets may retain mode bits without carrying an active mode."""
    sent = DelonghiCommand(mode=None, temperature=24, power=False, retained_mode=mode)
    assert sent.data == bytes.fromhex(packet)
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode is None
    assert received.state.temperature is None
    assert received.retained_mode is mode
    assert received.retained_temperature == 24
    rebuilt = DelonghiCommand(
        mode=received.state.mode,
        temperature=received.retained_temperature,
        power=False,
        retained_mode=received.retained_mode,
    )
    assert rebuilt.data == bytes.fromhex(packet)


def test_retained_mode_requires_off() -> None:
    """An on packet has one active mode, not a second retained mode."""
    with pytest.raises(ValueError, match="retained_mode"):
        DelonghiCommand(
            mode=DelonghiMode.COOL, temperature=24, retained_mode=DelonghiMode.DRY
        )
