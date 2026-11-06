"""Tests for haier protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.haier import HaierCommand
from infrared_protocols.commands.haier_tundra import (
    HaierButton,
    HaierTundraCommand,
    HaierUnit,
)


@pytest.mark.parametrize("button", list(HaierButton))
@pytest.mark.parametrize("unit", list(HaierUnit))
def test_haier_buttons(button: HaierButton, unit: HaierUnit) -> None:
    """Each known action has a readable button and valid transport checksum."""
    sent = HaierTundraCommand(
        mode=ClimateMode.COOL,
        temperature=23,
        button=button,
        unit=unit,
        health=True,
        quiet=True,
    )
    received = HaierTundraCommand.from_raw_timings(sent.get_raw_timings())
    raw_packet = HaierCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert raw_packet is not None
    assert raw_packet.data == sent.data[:-1]
    assert (received.button, received.unit) == (button, unit)
    assert received.health is True
    assert received.quiet is True


def test_haier_turbo() -> None:
    """Turbo's auxiliary flag differs from quiet, and the two are exclusive."""
    sent = HaierTundraCommand(mode=ClimateMode.COOL, temperature=24, turbo=True)
    received = HaierTundraCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.turbo is True
    with pytest.raises(ValueError, match="exclusive"):
        HaierTundraCommand(
            mode=ClimateMode.COOL, temperature=24, turbo=True, quiet=True
        )


@pytest.mark.parametrize("quiet,turbo", [(False, False), (True, False), (False, True)])
def test_haier_auxiliary_state(quiet: bool, turbo: bool) -> None:
    """Expose feature settings without requiring callers to inspect payload bits."""
    sent = HaierTundraCommand(
        mode=ClimateMode.COOL, temperature=24, health=True, quiet=quiet, turbo=turbo
    )
    received = HaierTundraCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.health is True
    assert received.quiet == quiet
    assert received.turbo == turbo


def test_unknown_button_rejected() -> None:
    """An unsupported button cannot be encoded."""
    with pytest.raises(ValueError):
        HaierTundraCommand(mode=ClimateMode.COOL, temperature=24, button=255)  # type: ignore[arg-type]


def test_unknown_received_button() -> None:
    """A valid checksum cannot legitimize an unsupported action identifier."""
    sent = HaierTundraCommand(mode=ClimateMode.COOL, temperature=24)
    sent.data = bytes.fromhex("a682000040a0002000000000143c")
    assert HaierTundraCommand.from_raw_timings(sent.get_raw_timings()) is None
