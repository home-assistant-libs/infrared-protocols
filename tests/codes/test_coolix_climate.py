"""Tests for the coolix named climate codes."""

import pytest

from infrared_protocols.codes.coolix.climate import CoolixCode
from infrared_protocols.commands.coolix import CoolixCommand


@pytest.mark.parametrize("code", list(CoolixCode))
def test_coolix_buttons(code: CoolixCode) -> None:
    """Known button actions retain their complete command word."""
    command = code.to_command()
    result = CoolixCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.first == code.value


@pytest.mark.parametrize("code", list(CoolixCode))
def test_coolix_action_copies(code: CoolixCode) -> None:
    """Named actions include the protocol's second identical packet."""
    sent = code.to_command()
    assert isinstance(sent, CoolixCommand)
    assert sent.first == sent.second == code
    assert sent.get_raw_timings().count(-5600) == 1
