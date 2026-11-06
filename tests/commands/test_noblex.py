"""Tests for noblex protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.noblex import NoblexCommand


@pytest.mark.parametrize("mode", list(ClimateMode))
def test_noblex_mode_field(mode: ClimateMode) -> None:
    """Mode assignment avoids the upstream cool-template OR bug."""
    command = NoblexCommand(mode=mode, temperature=24)
    assert command.state.mode == mode
