"""Tests for midea protocol behavior."""

from itertools import product

import pytest

from infrared_protocols.commands.climate import ClimateFan, ClimateMode, ClimateState
from infrared_protocols.commands.midea import MideaCommand


@pytest.mark.parametrize(
    "mode,power,fahrenheit,temperature,expected_mode,expected",
    [
        pytest.param(
            mode,
            power,
            fahrenheit,
            temp,
            mode if power else None,
            None if power and mode == ClimateMode.FAN_ONLY else expected,
            id=f"{mode}-{power}-{temp}-fahrenheit{fahrenheit}",
        )
        for mode, power, (fahrenheit, temp, expected) in product(
            ClimateMode, (False, True), [(False, 21, 21), (True, 68, 20)]
        )
    ],
)
def test_midea_state(
    mode: ClimateMode,
    power: bool,
    fahrenheit: bool,
    temperature: int,
    expected_mode: ClimateMode | None,
    expected: float | None,
) -> None:
    """Native Fahrenheit codes decode to Celsius and off remains explicit."""
    command = MideaCommand.climate(
        mode=mode, temperature=temperature, power=power, fahrenheit=fahrenheit
    )
    assert command.state == ClimateState(
        power=power,
        mode=expected_mode,
        temperature=expected,
        fan=ClimateFan.AUTO,
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
        pytest.param(ClimateMode.COOL, 24, ClimateFan.LOW, "a18847ffff", id="cool-low"),
        pytest.param(
            ClimateMode.COOL, 24, ClimateFan.MEDIUM, "a19047ffff", id="cool-medium"
        ),
        pytest.param(
            ClimateMode.COOL, 24, ClimateFan.AUTO, "a1a047ffff", id="cool-auto"
        ),
        pytest.param(
            ClimateMode.HEAT, 24, ClimateFan.AUTO, "a1a347ffff", id="heat-auto"
        ),
        pytest.param(
            ClimateMode.HEAT, 24, ClimateFan.HIGH, "a19b47ffff", id="heat-high"
        ),
        pytest.param(
            ClimateMode.FAN_ONLY, 24, ClimateFan.AUTO, "a1a45fffff", id="fan-auto"
        ),
    ],
)
def test_midea_control_bytes(
    mode: ClimateMode, temp: int, fan: ClimateFan, packet: str
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
    sent = MideaCommand.climate(mode=ClimateMode.COOL, temperature=23, sleep=True)
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
        MideaCommand.climate(mode=ClimateMode.COOL, temperature=24, power=False).data
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
    "temperature,fahrenheit,celsius",
    [
        pytest.param(17, False, 17, id="c-min"),
        pytest.param(30, False, 30, id="c-max"),
        pytest.param(62, True, (62 - 32) * 5 / 9, id="f-min"),
        pytest.param(75, True, (75 - 32) * 5 / 9, id="f-normal"),
        pytest.param(86, True, (86 - 32) * 5 / 9, id="f-max"),
    ],
)
def test_native_temperature(temperature: int, fahrenheit: bool, celsius: float) -> None:
    """Native unit metadata survives decoding alongside normalized Celsius."""
    command = MideaCommand.climate(
        mode=ClimateMode.COOL, temperature=temperature, fahrenheit=fahrenheit
    )
    received = MideaCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.fahrenheit is fahrenheit
    assert received.temperature == temperature
    assert received.state is not None
    assert received.state.temperature == celsius
