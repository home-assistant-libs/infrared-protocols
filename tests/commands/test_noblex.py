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


def test_placeholder_state_rebuild() -> None:
    """A decoded placeholder can be sent back without inventing a setpoint."""
    sent = NoblexCommand(mode=NoblexMode.AUTO)
    received = NoblexCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    state = received.state
    assert state.temperature is None
    assert state.mode is not None
    assert state.fan is not None
    rebuilt = NoblexCommand(
        mode=state.mode, temperature=state.temperature, fan=state.fan
    )
    assert rebuilt.get_raw_timings() == received.get_raw_timings()


def test_required_setpoint() -> None:
    """Cooling carries a target and cannot use the placeholder."""
    with pytest.raises(ValueError, match="temperature"):
        NoblexCommand(mode=NoblexMode.COOL)


@pytest.mark.parametrize("temperature", [0, 99])
def test_invalid_placeholder_temperature(temperature: int) -> None:
    """An omitted target is valid, but an explicitly invalid target still fails."""
    with pytest.raises(ValueError, match="temperature"):
        NoblexCommand(mode=NoblexMode.AUTO, temperature=temperature)
