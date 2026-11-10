"""Tests for the Edifier S351DB command codes."""

import pytest

from infrared_protocols.codes.edifier.s351db import EdifierS351DBCode
from infrared_protocols.commands.nec import NECCommand


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(EdifierS351DBCode.POWER, 0x43, id="power"),
        pytest.param(EdifierS351DBCode.VOLUME_UP, 0x4C, id="volume_up"),
        pytest.param(EdifierS351DBCode.VOLUME_DOWN, 0x17, id="volume_down"),
        pytest.param(EdifierS351DBCode.MUTE, 0x40, id="mute"),
        pytest.param(EdifierS351DBCode.PLAY_PAUSE, 0x50, id="play_pause"),
        pytest.param(EdifierS351DBCode.NEXT, 0x13, id="next"),
        pytest.param(EdifierS351DBCode.PREVIOUS, 0x54, id="previous"),
        pytest.param(EdifierS351DBCode.BLUETOOTH, 0x16, id="bluetooth"),
        pytest.param(EdifierS351DBCode.COAX, 0x0C, id="coax"),
        pytest.param(EdifierS351DBCode.PC, 0x51, id="pc"),
        pytest.param(EdifierS351DBCode.AUX, 0x12, id="aux"),
    ],
)
def test_edifier_s351db_code_to_command(code: EdifierS351DBCode, command: int) -> None:
    """Each code builds an NEC command on the Edifier address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == 0xE710
    assert built.command == command
