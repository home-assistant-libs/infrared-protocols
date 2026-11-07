"""Tests for noblex protocol behavior."""

import pytest

from infrared_protocols.commands.noblex import NoblexCommand, NoblexMode


@pytest.mark.parametrize(
    "mode,expected",
    [
        pytest.param(NoblexMode.AUTO, 0x10, id="auto"),
        pytest.param(NoblexMode.COOL, 0x90, id="cool"),
        pytest.param(NoblexMode.DRY, 0x50, id="dry"),
        pytest.param(NoblexMode.FAN_ONLY, 0xD0, id="fan-only"),
        pytest.param(NoblexMode.HEAT, 0x30, id="heat"),
    ],
)
def test_noblex_mode_field(mode: NoblexMode, expected: int) -> None:
    """Mode assignment avoids the upstream cool-template OR bug."""
    command = NoblexCommand(mode=mode, temperature=24)
    assert command.state.mode == mode
    assert command.data >> 59 == expected


def test_auto_has_no_set_point() -> None:
    """The fixed 25-degree auto byte is a placeholder, not a selected target."""
    sent = NoblexCommand(mode=NoblexMode.AUTO, temperature=18)
    received = NoblexCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode is NoblexMode.AUTO
    assert received.state.temperature is None
