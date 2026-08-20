"""Tests for the NEC display command codes."""

import pytest

from infrared_protocols.codes.nec.display import (
    NEC_DISPLAY_ADDRESS,
    NECDisplayCode,
)
from infrared_protocols.commands.proton import ProtonCommand


def test_nec_display_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = NECDisplayCode.__members__
    assert len(members) == len(set(members.values()))


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(NECDisplayCode.POWER, 0x52, id="power"),
        pytest.param(NECDisplayCode.STANDBY, 0x4E, id="standby"),
        pytest.param(NECDisplayCode.MUTE, 0x1B, id="mute"),
        pytest.param(NECDisplayCode.INPUT_HDMI_1, 0x64, id="input_hdmi_1"),
    ],
)
def test_nec_display_code_to_command(code: NECDisplayCode, command: int) -> None:
    """Each code builds a Proton command on the NEC display address."""
    built = code.to_command()
    assert isinstance(built, ProtonCommand)
    assert built.address == NEC_DISPLAY_ADDRESS
    assert built.command == command
    assert built.get_raw_timings() == (
        ProtonCommand(address=NEC_DISPLAY_ADDRESS, command=command).get_raw_timings()
    )


def test_nec_display_digits_are_contiguous() -> None:
    """Digits 1 through 9 occupy consecutive codes, with 0 just past them.

    This is what confirmed the protocol sends its bits least significant first:
    decoded the other way round, the digit keys scatter.
    """
    digits = [
        NECDisplayCode.NUM_1,
        NECDisplayCode.NUM_2,
        NECDisplayCode.NUM_3,
        NECDisplayCode.NUM_4,
        NECDisplayCode.NUM_5,
        NECDisplayCode.NUM_6,
        NECDisplayCode.NUM_7,
        NECDisplayCode.NUM_8,
        NECDisplayCode.NUM_9,
    ]
    assert [code.value for code in digits] == list(range(0x08, 0x11))
    assert NECDisplayCode.NUM_0 == 0x12


def test_nec_display_code_round_trips_through_the_decoder() -> None:
    """Every code must decode back to itself from its own timings."""
    for code in NECDisplayCode:
        decoded = ProtonCommand.from_raw_timings(code.to_command().get_raw_timings())
        assert decoded is not None
        assert decoded.address == NEC_DISPLAY_ADDRESS
        assert decoded.command == code.value
