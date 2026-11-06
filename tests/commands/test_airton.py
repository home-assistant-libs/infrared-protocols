"""Tests for airton protocol behavior."""

import pytest

from infrared_protocols.commands.airton import AirtonCommand, AirtonDirection
from infrared_protocols.commands.climate import ClimateMode


@pytest.mark.parametrize("direction", list(AirtonDirection))
def test_airton_features(direction: AirtonDirection) -> None:
    """Auxiliary settings remain accessible after reception."""
    sent = AirtonCommand(
        mode=ClimateMode.COOL,
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


@pytest.mark.parametrize("mode", [ClimateMode.AUTO, ClimateMode.FAN_ONLY])
def test_airton_sleep_unavailable(mode: ClimateMode) -> None:
    """The remote cannot request sleep in automatic or fan-only programs."""
    with pytest.raises(ValueError, match="sleep"):
        AirtonCommand(mode=mode, temperature=24, sleep=True)


def test_replaced_payload_updates_state() -> None:
    """Writable payload bytes and decoded settings describe the same transmission."""
    command = AirtonCommand(mode=ClimateMode.COOL, temperature=24)
    replacement = AirtonCommand(mode=ClimateMode.HEAT, temperature=26, display=False)
    command.data = replacement.data
    assert command.state.mode is ClimateMode.HEAT
    assert command.state.temperature == 26
    assert command.display is False
    assert command.get_raw_timings() == replacement.get_raw_timings()


def test_invalid_replaced_payload_rejects_state() -> None:
    """Reading state validates the replacement instead of returning stale settings."""
    command = AirtonCommand(mode=ClimateMode.COOL, temperature=24)
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
    sent = AirtonCommand(mode=ClimateMode.AUTO, temperature=18, power=power)
    received = AirtonCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.power is power
    assert received.state.temperature == expected
