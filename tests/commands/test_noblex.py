"""Tests for noblex protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.noblex import NoblexCommand


@pytest.mark.parametrize(
    "mode,expected",
    [
        pytest.param(ClimateMode.AUTO, 0x10, id="auto"),
        pytest.param(ClimateMode.COOL, 0x90, id="cool"),
        pytest.param(ClimateMode.DRY, 0x50, id="dry"),
        pytest.param(ClimateMode.FAN_ONLY, 0xD0, id="fan-only"),
        pytest.param(ClimateMode.HEAT, 0x30, id="heat"),
    ],
)
def test_noblex_mode_field(mode: ClimateMode, expected: int) -> None:
    """Mode assignment avoids the upstream cool-template OR bug."""
    command = NoblexCommand(mode=mode, temperature=24)
    assert command.state.mode == mode
    assert command.data >> 59 == expected


def test_auto_has_no_set_point() -> None:
    """The fixed 25-degree auto byte is a placeholder, not a selected target."""
    sent = NoblexCommand(mode=ClimateMode.AUTO, temperature=18)
    received = NoblexCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode is ClimateMode.AUTO
    assert received.state.temperature is None
