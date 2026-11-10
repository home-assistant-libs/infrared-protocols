"""Tests for the Edifier R2600 command codes."""

import pytest

from infrared_protocols.codes.edifier.r2600 import EdifierR2600Code
from infrared_protocols.commands.nec import NECCommand


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(EdifierR2600Code.VOLUME_UP, 0x01, id="volume_up"),
        pytest.param(EdifierR2600Code.VOLUME_DOWN, 0x02, id="volume_down"),
        pytest.param(EdifierR2600Code.MUTE, 0x09, id="mute"),
        pytest.param(EdifierR2600Code.PC, 0x00, id="pc"),
        pytest.param(EdifierR2600Code.AUX, 0x03, id="aux"),
    ],
)
def test_edifier_r2600_code_to_command(code: EdifierR2600Code, command: int) -> None:
    """Each code builds an NEC command on the RC31A remote address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == 0x0E78
    assert built.command == command
