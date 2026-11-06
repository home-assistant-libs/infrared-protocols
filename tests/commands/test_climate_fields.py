"""Tests for climate fields protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.pd_pioneer_climate import PdPioneerClimateCommand
from infrared_protocols.commands.tcl112 import Tcl112Command


@pytest.mark.parametrize("temperature", [15.5, 31.5, 24.25])
@pytest.mark.parametrize("cls", [Tcl112Command, PdPioneerClimateCommand])
def test_fractional_temperature_limits(
    cls: type[Tcl112Command] | type[PdPioneerClimateCommand], temperature: float
) -> None:
    """Reject half-degree inputs outside the range and unsupported quarter degrees."""
    with pytest.raises(ValueError, match="temperature"):
        cls(mode=ClimateMode.COOL, temperature=temperature)
