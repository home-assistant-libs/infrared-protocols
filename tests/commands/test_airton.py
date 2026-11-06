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
