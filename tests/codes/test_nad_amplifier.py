"""Tests for the NAD amplifier command codes."""

import pytest

from infrared_protocols.codes.nad.amplifier import (
    NAD_AMPLIFIER_ADDRESS,
    NADAmplifierCode,
)
from infrared_protocols.commands.nec import NECCommand


def test_nad_amplifier_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = NADAmplifierCode.__members__
    assert len(members) == len(set(members.values()))


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(NADAmplifierCode.ON, 0x25, id="on"),
        pytest.param(NADAmplifierCode.OFF, 0xC8, id="off"),
        pytest.param(NADAmplifierCode.VOLUME_UP, 0x88, id="volume_up"),
        pytest.param(NADAmplifierCode.MUTE, 0x94, id="mute"),
        pytest.param(NADAmplifierCode.INPUT_1, 0xC2, id="input_1"),
        pytest.param(NADAmplifierCode.TAPE_1, 0x8D, id="tape_1"),
        pytest.param(NADAmplifierCode.AUX, 0x9B, id="aux"),
    ],
)
def test_nad_amplifier_code_to_command(code: NADAmplifierCode, command: int) -> None:
    """Each code builds an extended NEC command on the NAD address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == NAD_AMPLIFIER_ADDRESS
    assert built.command == command


def test_nad_amplifier_address_byte_order() -> None:
    """The frame starts with 0x87 then 0x7C, matching NAD's 877C customer code."""
    timings = NADAmplifierCode.ON.to_command().get_raw_timings()
    decoded = NECCommand.from_raw_timings(timings)
    assert decoded is not None
    assert decoded.address & 0xFF == 0x87
    assert decoded.address >> 8 == 0x7C
