"""Tests for the NAD receiver command codes."""

import pytest

from infrared_protocols.codes.nad.receiver import (
    NAD_RECEIVER_ADDRESS,
    NADReceiverCode,
)
from infrared_protocols.commands.nec import NECCommand


def test_nad_receiver_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = NADReceiverCode.__members__
    assert len(members) == len(set(members.values()))


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(NADReceiverCode.ON, 0x25, id="on"),
        pytest.param(NADReceiverCode.OFF, 0xC8, id="off"),
        pytest.param(NADReceiverCode.VOLUME_UP, 0x88, id="volume_up"),
        pytest.param(NADReceiverCode.MUTE, 0x94, id="mute"),
        pytest.param(NADReceiverCode.INPUT_1, 0xC2, id="input_1"),
    ],
)
def test_nad_receiver_code_to_command(code: NADReceiverCode, command: int) -> None:
    """Each code builds an extended NEC command on the NAD address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == NAD_RECEIVER_ADDRESS
    assert built.command == command


def test_nad_receiver_address_byte_order() -> None:
    """The frame starts with 0x87 then 0x7C, matching NAD's 877C customer code."""
    timings = NADReceiverCode.ON.to_command().get_raw_timings()
    decoded = NECCommand.from_raw_timings(timings)
    assert decoded is not None
    assert decoded.address & 0xFF == 0x87
    assert decoded.address >> 8 == 0x7C
