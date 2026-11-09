"""Tests for the Edifier RC80B command codes."""

import pytest

from infrared_protocols.codes.edifier.rc80b import EdifierRC80BCode
from infrared_protocols.commands.nec import NECCommand


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(EdifierRC80BCode.POWER, 0x46, id="power"),
        pytest.param(EdifierRC80BCode.VOLUME_UP, 0x06, id="volume_up"),
        pytest.param(EdifierRC80BCode.VOLUME_DOWN, 0x47, id="volume_down"),
        pytest.param(EdifierRC80BCode.MUTE, 0x41, id="mute"),
        pytest.param(EdifierRC80BCode.PLAY_PAUSE, 0x5F, id="play_pause"),
        pytest.param(EdifierRC80BCode.FORWARD, 0x5D, id="forward"),
        pytest.param(EdifierRC80BCode.BACK, 0x44, id="back"),
        pytest.param(EdifierRC80BCode.FX_ON, 0x1A, id="fx_on"),
        pytest.param(EdifierRC80BCode.FX_OFF, 0x1B, id="fx_off"),
        pytest.param(EdifierRC80BCode.LINE_1_2, 0x15, id="line_1_2"),
        pytest.param(EdifierRC80BCode.OPT_COAX, 0x0D, id="opt_coax"),
        pytest.param(EdifierRC80BCode.BLUETOOTH, 0x5C, id="bluetooth"),
    ],
)
def test_edifier_rc80b_code_to_command(code: EdifierRC80BCode, command: int) -> None:
    """Each code builds an NEC command on the Edifier address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == 0xE710
    assert built.command == command
