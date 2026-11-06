"""Tests for tcl112 protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateFan, ClimateMode
from infrared_protocols.commands.tcl112 import Tcl112Command


@pytest.mark.parametrize("temperature", [16, 16.5, 24.5, 30.5, 31])
def test_tcl_half_degree(temperature: float) -> None:
    """The half-degree bit and quiet fan code are independent fields."""
    sent = Tcl112Command(
        mode=ClimateMode.COOL, temperature=temperature, fan=ClimateFan.QUIET
    )
    received = Tcl112Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == temperature
    assert received.state.fan == ClimateFan.QUIET
