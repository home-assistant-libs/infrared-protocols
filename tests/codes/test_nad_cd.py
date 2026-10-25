"""Tests for the NAD CD player command codes."""

import pytest

from infrared_protocols.codes.nad.amplifier import (
    NAD_AMPLIFIER_ADDRESS,
    NADAmplifierCode,
)
from infrared_protocols.codes.nad.cd import NAD_CD_ADDRESS, NADCDCode
from infrared_protocols.commands.nec import NECCommand


def test_nad_cd_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = NADCDCode.__members__
    assert len(members) == len(set(members.values()))


def test_nad_cd_codes_do_not_overlap_amplifier() -> None:
    """All NAD components share one address, so their codes must not collide."""
    assert NAD_CD_ADDRESS == NAD_AMPLIFIER_ADDRESS
    assert not {code.value for code in NADCDCode} & {
        code.value for code in NADAmplifierCode
    }


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(NADCDCode.PLAY, 0x01, id="play"),
        pytest.param(NADCDCode.NUM_0, 0x16, id="num_0"),
        pytest.param(NADCDCode.DISC_5, 0x45, id="disc_5"),
    ],
)
def test_nad_cd_code_to_command(code: NADCDCode, command: int) -> None:
    """Each code builds an extended NEC command on the NAD address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == NAD_CD_ADDRESS
    assert built.command == command
