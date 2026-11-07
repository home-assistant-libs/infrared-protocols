"""Tests for airton protocol behavior."""

import pytest

from infrared_protocols.commands._climate import ClimatePacket
from infrared_protocols.commands.airton import (
    AirtonCommand,
    AirtonDirection,
    AirtonFanSpeed,
    AirtonMode,
)


@pytest.mark.parametrize("direction", list(AirtonDirection))
def test_airton_features(direction: AirtonDirection) -> None:
    """Auxiliary settings remain accessible after reception."""
    sent = AirtonCommand(
        mode=AirtonMode.COOL,
        temperature=24,
        direction=direction,
        display=False,
        sleep=True,
    )
    received = AirtonCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.direction == direction
    assert received.display is False
    assert received.sleep is True
    assert received.state.swing_v == (direction == AirtonDirection.SWING)


@pytest.mark.parametrize("mode", [AirtonMode.AUTO, AirtonMode.FAN_ONLY])
def test_airton_sleep_unavailable(mode: AirtonMode) -> None:
    """The remote cannot request sleep in automatic or fan-only programs."""
    with pytest.raises(ValueError, match="sleep"):
        AirtonCommand(mode=mode, temperature=24, sleep=True)


def test_replaced_payload_updates_state() -> None:
    """Writable payload bytes and decoded settings describe the same transmission."""
    command = AirtonCommand(mode=AirtonMode.COOL, temperature=24)
    replacement = AirtonCommand(mode=AirtonMode.HEAT, temperature=26, display=False)
    command.data = replacement.data
    assert command.state.mode is AirtonMode.HEAT
    assert command.state.temperature == 26
    assert command.display is False
    assert command.get_raw_timings() == replacement.get_raw_timings()


def test_invalid_replaced_payload_rejects_state() -> None:
    """Reading state validates the replacement instead of returning stale settings."""
    command = AirtonCommand(mode=AirtonMode.COOL, temperature=24)
    command.data = command.data[:-1] + bytes([command.data[-1] ^ 1])
    with pytest.raises(ValueError, match="checksum"):
        _ = command.state


@pytest.mark.parametrize(
    "power,expected",
    [
        pytest.param(True, None, id="auto-placeholder"),
        pytest.param(False, 18, id="off-retains-target"),
    ],
)
def test_auto_temperature(power: bool, expected: int | None) -> None:
    """Only powered-on auto replaces the requested temperature with a fixed value."""
    sent = AirtonCommand(mode=AirtonMode.AUTO, temperature=18, power=power)
    received = AirtonCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.power is power
    assert received.state.temperature == expected


@pytest.mark.parametrize(
    "fan,packet",
    [
        pytest.param(AirtonFanSpeed.LEVEL_2, "d311290800c48a", id="level-2"),
        pytest.param(AirtonFanSpeed.LEVEL_4, "d311490800c4aa", id="level-4"),
    ],
)
def test_native_intermediate_fan(fan: AirtonFanSpeed, packet: str) -> None:
    """Decoding and rebuilding must preserve intermediate handheld fan levels."""
    command = AirtonCommand(mode=AirtonMode.COOL, temperature=24, fan=fan)
    assert command.data == bytes.fromhex(packet)
    received = AirtonCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    state = received.state
    assert state.fan is fan
    assert state.fan is not None
    rebuilt = AirtonCommand(mode=AirtonMode.COOL, temperature=24, fan=state.fan)
    assert rebuilt.data == received.data


@pytest.mark.parametrize(
    "packet,turbo,economy,health",
    [
        pytest.param("d311090800842a", False, False, False, id="False-False-False"),
        pytest.param("d31189080084aa", True, False, False, id="True-False-False"),
        pytest.param("d3110908008529", False, True, False, id="False-True-False"),
        pytest.param("d311090800c4ea", False, False, True, id="False-False-True"),
        pytest.param("d311890800c569", True, True, True, id="True-True-True"),
    ],
)
def test_native_auxiliary_bits(
    packet: str, turbo: bool, economy: bool, health: bool
) -> None:
    """Independent auxiliary bits remain available on received handheld packets."""
    sent = AirtonCommand.__new__(AirtonCommand)
    ClimatePacket.__init__(sent, data=bytes.fromhex(packet))
    received = AirtonCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.data == bytes.fromhex(packet)
    assert received.turbo is turbo
    assert received.economy is economy
    assert received.health is health
