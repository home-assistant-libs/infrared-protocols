"""Tests for the NAD cassette deck command codes."""

import pytest

from infrared_protocols.codes.nad.amplifier import (
    NAD_AMPLIFIER_ADDRESS,
    NADAmplifierCode,
)
from infrared_protocols.codes.nad.tape import NAD_TAPE_ADDRESS, NADTapeCode
from infrared_protocols.commands.nec import NECCommand


def test_nad_tape_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = NADTapeCode.__members__
    assert len(members) == len(set(members.values()))


def test_nad_tape_codes_do_not_overlap_amplifier() -> None:
    """All NAD components share one address, so their codes must not collide."""
    assert NAD_TAPE_ADDRESS == NAD_AMPLIFIER_ADDRESS
    assert not {code.value for code in NADTapeCode} & {
        code.value for code in NADAmplifierCode
    }


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(NADTapeCode.DECK_A_PLAY, 0x53, id="deck_a_play"),
        pytest.param(NADTapeCode.DECK_B_STOP, 0x9F, id="deck_b_stop"),
        pytest.param(NADTapeCode.DECK_B_REVERSE_PLAY, 0xDE, id="deck_b_reverse_play"),
    ],
)
def test_nad_tape_code_to_command(code: NADTapeCode, command: int) -> None:
    """Each code builds an extended NEC command on the NAD address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == NAD_TAPE_ADDRESS
    assert built.command == command
