"""Tests for the BenQ projector command codes."""

import pytest

from infrared_protocols.codes.benq.projector import (
    BENQ_PROJECTOR_ADDRESS,
    BenQProjectorCode,
)
from infrared_protocols.commands.nec import NECCommand


def test_benq_projector_address() -> None:
    """BenQ's custom code 0x30 is the high byte; captures show "00 30" on the wire."""
    assert BENQ_PROJECTOR_ADDRESS & 0xFF == 0x00
    assert BENQ_PROJECTOR_ADDRESS >> 8 == 0x30


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(BenQProjectorCode.POWER_ON, 0x4F, id="power_on"),
        pytest.param(BenQProjectorCode.POWER_OFF, 0x4E, id="power_off"),
        pytest.param(BenQProjectorCode.SOURCE, 0x04, id="source"),
        pytest.param(BenQProjectorCode.HDMI_1, 0x58, id="hdmi_1"),
        pytest.param(BenQProjectorCode.MUTE, 0x14, id="mute"),
        pytest.param(BenQProjectorCode.VOLUME_UP, 0x82, id="volume_up"),
        pytest.param(BenQProjectorCode.PICTURE_MODE, 0x10, id="picture_mode"),
        pytest.param(BenQProjectorCode.PLAY, 0xA9, id="play"),
    ],
)
def test_benq_projector_code_to_command(code: BenQProjectorCode, command: int) -> None:
    """Each code builds an extended NEC command on the BenQ address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == BENQ_PROJECTOR_ADDRESS
    assert built.command == command


def test_benq_projector_digits_are_contiguous() -> None:
    """Digits 1 through 9 occupy consecutive codes, with 0 just past them."""
    digits = [
        BenQProjectorCode.NUM_1,
        BenQProjectorCode.NUM_2,
        BenQProjectorCode.NUM_3,
        BenQProjectorCode.NUM_4,
        BenQProjectorCode.NUM_5,
        BenQProjectorCode.NUM_6,
        BenQProjectorCode.NUM_7,
        BenQProjectorCode.NUM_8,
        BenQProjectorCode.NUM_9,
    ]
    assert [code.value for code in digits] == list(range(0x31, 0x3A))
    assert BenQProjectorCode.NUM_0 == 0x3A
