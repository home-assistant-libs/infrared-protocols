"""Tests for emmeti protocol behavior."""

import pytest

from infrared_protocols.commands.emmeti import (
    EmmetiBlade,
    EmmetiCommand,
    EmmetiMode,
    EmmetiState,
)


@pytest.mark.parametrize("blade", list(EmmetiBlade))
@pytest.mark.parametrize("temperature", [16, 22, 30])
def test_emmeti_blades(blade: EmmetiBlade, temperature: int) -> None:
    """Every supported vane position and range is readable from a decoded command."""
    sent = EmmetiCommand(mode=EmmetiMode.COOL, temperature=temperature, blade=blade)
    received = EmmetiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.blade == blade
    assert received.state.temperature == temperature


def test_emmeti_other_off_state() -> None:
    """Power-off is identified by the power bit, beyond the fixed off packet."""
    sent = EmmetiCommand(mode=EmmetiMode.COOL, temperature=22)
    sent.data &= ~(1 << 63)
    received = EmmetiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state == EmmetiState(power=False)
