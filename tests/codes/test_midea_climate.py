"""Tests for the midea named climate codes."""

import pytest

from infrared_protocols.codes.midea.climate import MideaSpecialCode
from infrared_protocols.commands.midea import MideaCommand


@pytest.mark.parametrize("code", list(MideaSpecialCode))
def test_midea_buttons(code: MideaSpecialCode) -> None:
    """Button packets never masquerade as an absolute climate state."""
    command = code.to_command()
    result = MideaCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state is None
    assert isinstance(command, MideaCommand)
    assert result.data == command.data
