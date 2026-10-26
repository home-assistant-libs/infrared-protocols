"""Tests for the Croma TV command codes."""

import pytest

from infrared_protocols.codes.croma.tv import CROMA_ADDRESS, CromaTVCode
from infrared_protocols.commands.nec import NECCommand


def test_croma_tv_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = CromaTVCode.__members__
    assert len(members) == len(set(members.values()))


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(CromaTVCode.POWER, 0x12, id="power"),
        pytest.param(CromaTVCode.MUTE, 0x10, id="mute"),
        pytest.param(CromaTVCode.OK, 0x0A, id="ok"),
        pytest.param(CromaTVCode.LIVE_TV, 0x8C, id="live_tv"),
    ],
)
def test_croma_tv_code_to_command(code: CromaTVCode, command: int) -> None:
    """Each code builds an NEC command on the Croma address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == CROMA_ADDRESS
    assert built.command == command
