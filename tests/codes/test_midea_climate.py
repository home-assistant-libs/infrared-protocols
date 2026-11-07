"""Tests for the midea named climate codes."""

import pytest

from infrared_protocols.codes.midea.climate import MideaSpecialCode
from infrared_protocols.commands.midea import MideaCommand


def test_codes_are_unique() -> None:
    """Named buttons must not silently become aliases."""
    members = MideaSpecialCode.__members__
    assert len(members) == len(set(members.values()))


@pytest.mark.parametrize("code", list(MideaSpecialCode))
def test_midea_buttons(code: MideaSpecialCode) -> None:
    """Button packets never masquerade as an absolute climate state."""
    command = code.to_command()
    result = MideaCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state is None
    assert isinstance(command, MideaCommand)
    assert result.data == command.data
