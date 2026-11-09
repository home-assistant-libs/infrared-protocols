"""Tests for the Edifier R2600 command codes."""

import pytest

from infrared_protocols.codes.edifier.models import (
    MODEL_TO_COMMAND_SET,
    EdifierCommandSet,
    EdifierModel,
)
from infrared_protocols.codes.edifier.r2600 import EdifierR2600Code
from infrared_protocols.commands.nec import NECCommand


def test_edifier_r2600_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = EdifierR2600Code.__members__
    assert len(members) == len(set(members.values()))


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


@pytest.mark.parametrize(
    "model",
    [
        pytest.param(EdifierModel.R2600, id="r2600"),
        pytest.param(EdifierModel.RC31A, id="rc31a"),
    ],
)
def test_edifier_r2600_model_mapping(model: EdifierModel) -> None:
    """The RC31A remote belongs to the R2600, not the S360DB."""
    assert MODEL_TO_COMMAND_SET[model] is EdifierCommandSet.R2600
