"""Tests for midea protocol behavior."""

from itertools import product

import pytest

from infrared_protocols.commands.midea import (
    MideaCommand,
    MideaFanSpeed,
    MideaMode,
    MideaState,
)


@pytest.mark.parametrize(
    "mode,power,is_fahrenheit,temperature,expected_mode,expected",
    [
        pytest.param(
            mode,
            power,
            is_fahrenheit,
            temp,
            mode if power else None,
            None if power and mode == MideaMode.FAN_ONLY else expected,
            id=f"{mode}-{power}-{temp}-is_fahrenheit{is_fahrenheit}",
        )
        for mode, power, (is_fahrenheit, temp, expected) in product(
            MideaMode, (False, True), [(False, 21, 21), (True, 68, 68)]
        )
    ],
)
def test_midea_state(
    mode: MideaMode,
    power: bool,
    is_fahrenheit: bool,
    temperature: int,
    expected_mode: MideaMode | None,
    expected: float | None,
) -> None:
    """Native temperatures retain their units and off remains explicit."""
    command = MideaCommand.climate(
        mode=mode, temperature=temperature, power=power, is_fahrenheit=is_fahrenheit
    )
    assert command.state == MideaState(
        power=power,
        mode=expected_mode,
        temperature=expected,
        is_fahrenheit=is_fahrenheit,
        fan=MideaFanSpeed.AUTO,
    )


def test_midea_follow_me() -> None:
    """The sensor report's temperature and beeper fields have fixed positions."""
    command = MideaCommand.follow_me(temperature=23, beeper=True)
    assert command.data == bytes.fromhex("a48248ff18")
    assert command.state is None
    received = MideaCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.follow_me_temperature == 23
    assert received.follow_me_beeper is True


@pytest.mark.parametrize(
    "mode,temp,fan,packet",
    [
        pytest.param(
            MideaMode.COOL, 24, MideaFanSpeed.LOW, "a18847ffff", id="cool-low"
        ),
        pytest.param(
            MideaMode.COOL, 24, MideaFanSpeed.MEDIUM, "a19047ffff", id="cool-medium"
        ),
        pytest.param(
            MideaMode.COOL, 24, MideaFanSpeed.AUTO, "a1a047ffff", id="cool-auto"
        ),
        pytest.param(
            MideaMode.HEAT, 24, MideaFanSpeed.AUTO, "a1a347ffff", id="heat-auto"
        ),
        pytest.param(
            MideaMode.HEAT, 24, MideaFanSpeed.HIGH, "a19b47ffff", id="heat-high"
        ),
        pytest.param(
            MideaMode.FAN_ONLY, 24, MideaFanSpeed.AUTO, "a1a45fffff", id="fan-auto"
        ),
    ],
)
def test_midea_control_bytes(
    mode: MideaMode, temp: int, fan: MideaFanSpeed, packet: str
) -> None:
    """Known control bytes constrain the tables independently of decoding."""
    sent = MideaCommand.climate(mode=mode, temperature=temp, fan=fan)
    assert sent.data == bytes.fromhex(packet)
    state = MideaCommand(data=bytes.fromhex(packet)).state
    assert state is not None
    assert state.mode == mode
    assert state.fan == fan


def test_midea_unknown_state() -> None:
    """Checksum-valid but unknown control values do not fabricate a climate state."""
    sent = MideaCommand(data=bytes.fromhex("a1875fffff"))
    received = MideaCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state is None


def test_midea_sleep_decode() -> None:
    """Sleep is readable after receiving an ordinary control packet."""
    sent = MideaCommand.climate(mode=MideaMode.COOL, temperature=23, sleep=True)
    received = MideaCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.sleep is True
    assert received.state is not None
    assert received.state.temperature == 23


def test_captured_off_placeholder() -> None:
    """The standard off frame's AUTO bits are not retained operating state."""
    command = MideaCommand(data=bytes.fromhex("a10247ffff"))
    assert command.state is not None
    assert command.state.power is False
    assert command.state.mode is None
    assert (
        MideaCommand.climate(mode=MideaMode.COOL, temperature=24, power=False).data
        == command.data
    )


def test_incomplete_packet_rejected() -> None:
    """A partial payload cannot satisfy the paired Midea frame format."""
    assert (
        MideaCommand.from_raw_timings(
            MideaCommand(data=bytes(5)).get_raw_timings()[:99]
        )
        is None
    )


@pytest.mark.parametrize(
    "temperature,is_fahrenheit",
    [
        pytest.param(17, False, id="c-min"),
        pytest.param(30, False, id="c-max"),
        pytest.param(62, True, id="f-min"),
        pytest.param(75, True, id="f-normal"),
        pytest.param(86, True, id="f-max"),
    ],
)
def test_native_temperature(temperature: int, is_fahrenheit: bool) -> None:
    """Native temperature and unit metadata survive decoding together."""
    command = MideaCommand.climate(
        mode=MideaMode.COOL, temperature=temperature, is_fahrenheit=is_fahrenheit
    )
    received = MideaCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.is_fahrenheit is is_fahrenheit
    assert received.temperature == temperature
    assert received.state is not None
    assert received.state.temperature == temperature
    assert received.state.is_fahrenheit is is_fahrenheit
