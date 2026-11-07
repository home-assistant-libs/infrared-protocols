"""Tests for tcl112 protocol behavior."""

import pytest

from infrared_protocols.commands.tcl112 import Tcl112Command, Tcl112FanSpeed, Tcl112Mode


@pytest.mark.parametrize("temperature", [16, 16.5, 24.5, 30.5, 31])
def test_tcl_half_degree(temperature: float) -> None:
    """The half-degree bit and quiet fan code are independent fields."""
    sent = Tcl112Command(
        mode=Tcl112Mode.COOL, temperature=temperature, fan=Tcl112FanSpeed.QUIET
    )
    received = Tcl112Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == temperature
    assert received.state.fan == Tcl112FanSpeed.QUIET


@pytest.mark.parametrize(
    "temperature",
    [
        pytest.param(15.5, id="too-low"),
        pytest.param(31.5, id="too-high"),
        pytest.param(24.25, id="quarter-degree"),
    ],
)
def test_fractional_temperature_limits(temperature: float) -> None:
    """Reject half-degree inputs outside the range and unsupported quarter degrees."""
    with pytest.raises(ValueError, match="temperature"):
        Tcl112Command(mode=Tcl112Mode.COOL, temperature=temperature)


def test_half_degree_quiet_wire_bytes() -> None:
    """Independent bytes pin the half-degree position and native quiet fan code."""
    command = Tcl112Command(
        mode=Tcl112Mode.COOL, temperature=24.5, fan=Tcl112FanSpeed.QUIET
    )
    assert command.data == bytes.fromhex("23cb2601002403074100000020a4")


def test_recorded_quiet_packet() -> None:
    """The remote capture's quiet code is accepted without requiring the fixed tail."""
    command = Tcl112Command(mode=Tcl112Mode.COOL, temperature=24)
    command.data = bytes.fromhex("23cb260100240307410000000084")
    received = Tcl112Command.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.state.temperature == 24
    assert received.state.fan is Tcl112FanSpeed.QUIET
