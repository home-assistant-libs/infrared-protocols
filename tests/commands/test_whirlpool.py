"""Tests for whirlpool protocol behavior."""

import pytest

from infrared_protocols.commands._climate import ClimatePacket
from infrared_protocols.commands.climate import ClimateFan, ClimateMode
from infrared_protocols.commands.whirlpool import (
    HisenseArgCommand,
    WhirlpoolCommand,
    WhirlpoolDg11j191Command,
)


def test_whirlpool_short_press() -> None:
    """A 14-byte press validates the first checksum without needing a third part."""
    sent = WhirlpoolCommand(mode=ClimateMode.COOL, temperature=24)
    sent.data = sent.data[:14]
    received = WhirlpoolCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert len(received.data) == 14
    assert received.state.mode == ClimateMode.COOL
    assert received.state.temperature == 24
    assert received.get_raw_timings() == sent.get_raw_timings()


@pytest.mark.parametrize(
    "cls,expected",
    [
        pytest.param(
            WhirlpoolDg11j191Command,
            "83060782000080000000000000050006000008000e",
            id="dg11j1-91",
        ),
        pytest.param(
            HisenseArgCommand,
            "830607820000800000000080189d00010000080009",
            id="hisense-arg",
        ),
    ],
)
def test_whirlpool_independent_packets(
    cls: type[WhirlpoolCommand], expected: str
) -> None:
    """ESPHome's whirlpool_tests.cpp records model-specific complete packets."""
    sent = cls(
        mode=ClimateMode.COOL, temperature=24, fan=ClimateFan.LOW, power_toggle=True
    )
    assert sent.data == bytes.fromhex(expected)
    received = cls.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == 24
    assert received.state.fan == ClimateFan.LOW
    assert received.power_toggle


def test_hisense_fan_sentinel() -> None:
    """Fan-only's fixed temperature nibble is not a set point."""
    sent = HisenseArgCommand(mode=ClimateMode.FAN_ONLY, temperature=24)
    assert sent.state.temperature is None


@pytest.mark.parametrize(
    "temperature,candidates,decoded",
    [
        pytest.param(16, tuple(range(16, 22)), None, id="low-range"),
        pytest.param(22, (22,), 22, id="exact-22"),
        pytest.param(24, (24,), 24, id="exact-24"),
        pytest.param(30, (23, 25, 26, 27, 28, 29, 30), None, id="high-range"),
    ],
)
def test_hisense_ambiguous_auto(
    temperature: int, candidates: tuple[int, ...], decoded: int | None
) -> None:
    """Auto range codes expose ambiguity instead of guessing an exact target."""
    command = HisenseArgCommand(mode=ClimateMode.AUTO, temperature=temperature)
    result = HisenseArgCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state.temperature == decoded
    assert result.temperature_candidates == candidates


def test_whirlpool_toggle_semantics() -> None:
    """Power and swing toggles must not be presented as absolute on states."""
    command = WhirlpoolCommand(
        mode=ClimateMode.COOL, temperature=24, power_toggle=True, swing_toggle=True
    )
    assert command.state.power is None
    assert command.state.swing_v is None
    assert command.power_toggle
    assert command.swing_toggle


def test_hisense_absolute_swing_capture() -> None:
    """The receive fixture sets byte 8 without the transmitter's byte-2 mirror."""
    packet = bytes.fromhex("83060382000080004000008018d90002000008000a")
    command = HisenseArgCommand.__new__(HisenseArgCommand)
    ClimatePacket.__init__(command, data=packet)
    received = HisenseArgCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.state.swing_v is True
    assert received.state.mode == ClimateMode.COOL
    assert received.state.temperature == 24


@pytest.mark.parametrize(
    "packet",
    [
        pytest.param("83060462000080000000000000e600010000080009", id="power-on"),
        pytest.param("83060462000080000000000000e600000000080008", id="light"),
    ],
)
def test_button_frame_retains_cool_mode(packet: str) -> None:
    """Power and light button codes do not erase a known cool mode."""
    command = WhirlpoolCommand.__new__(WhirlpoolCommand)
    ClimatePacket.__init__(command, data=bytes.fromhex(packet))
    result = WhirlpoolCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state.mode == ClimateMode.COOL
    assert result.state.temperature == 24


def test_hisense_off_has_no_placeholder_mode() -> None:
    """The cool code in a Hisense shutdown toggle does not identify its mode."""
    sent = HisenseArgCommand(
        mode=ClimateMode.HEAT, temperature=24, power_toggle=True, off_command=True
    )
    result = HisenseArgCommand.from_raw_timings(sent.get_raw_timings())
    assert result is not None
    assert result.power_toggle
    assert result.state.mode is None
