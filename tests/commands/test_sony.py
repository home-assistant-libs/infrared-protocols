"""Tests for the SONY SIRC IR command encoder."""

import json
from itertools import product
from pathlib import Path

import pytest

from infrared_protocols.commands.sony import SonyCommand


def test_sony_command_get_raw_timings_12_bit_standard() -> None:
    """Test SONY SIRC 12-bit timings for a 7-bit command + 5-bit address."""
    # command=0x15 -> bits (LSB first): 1,0,1,0,1,0,0
    # address=0x01 -> bits (LSB first): 1,0,0,0,0
    expected_raw_timings = [
        2400,
        -600,
        1200,
        -600,
        600,
        -600,
        1200,
        -600,
        600,
        -600,
        1200,
        -600,
        600,
        -600,
        600,
        -600,
        1200,
        -600,
        600,
        -600,
        600,
        -600,
        600,
        -600,
        600,
        -25800,
    ]
    command = SonyCommand(address=0x01, address_bits=5, command=0x15)
    timings = command.get_raw_timings()
    assert timings == expected_raw_timings
    assert command.modulation == 40000


def test_sony_command_get_raw_timings_15_bit() -> None:
    """Test SONY SIRC 15-bit framing for an 8-bit address."""
    command = SonyCommand(address=0xA8, address_bits=8, command=0x02)
    timings = command.get_raw_timings()

    # 15-bit frame: leader high + 15 low/high pairs + trailer low
    assert len(timings) == 2 + (15 * 2)
    assert timings[0] == 2400
    assert timings[-1] == -22200


def test_sony_command_get_raw_timings_20_bit() -> None:
    """Test SONY SIRC 20-bit framing for a 13-bit address."""
    command = SonyCommand(address=0x1ABC, address_bits=13, command=0x34)
    timings = command.get_raw_timings()

    # 20-bit frame: leader high + 20 low/high pairs + trailer low
    assert len(timings) == 2 + (20 * 2)
    assert timings[0] == 2400
    assert timings[-1] == -12000


@pytest.mark.parametrize(
    ("address", "address_bits", "command"),
    [
        (-1, 5, 0x00),
        (0x20, 5, 0x00),
        (0x100, 8, 0x00),
        (0x2000, 13, 0x00),
        (0x00, 4, 0x00),
        (0x00, 6, 0x00),
        (0x00, 5, -1),
        (0x00, 5, 0x80),
    ],
)
def test_sony_command_rejects_out_of_range(
    address: int, address_bits: int, command: int
) -> None:
    """SONY SIRC fields must fit address<=13 bits and command<=7 bits."""
    with pytest.raises(ValueError):
        SonyCommand(address=address, address_bits=address_bits, command=command)


_CAPTURES = json.loads(
    (Path(__file__).parents[1] / "fixtures/receiver_captures.json").read_text()
)["captures"]

_DECODE_CASES = [
    pytest.param(command, id=type(command).__name__ + "-" + str(vars(command)))
    for command in [
        *[
            SonyCommand(address=(1 << b) - 1, address_bits=b, command=c)
            for b, c in product((5, 8, 13), (0, 127))
        ]
    ]
]


def test_sony_physical_capture() -> None:
    """Decode a recorded Sony20 signal with stretched marks and short spaces."""
    capture = next(c for c in _CAPTURES if c["protocol"] == "sony")
    received = SonyCommand.from_raw_timings(capture["timings"])
    assert received is not None
    assert (received.address_bits, received.address, received.command) == (13, 0x4B9, 7)


def test_sony_held_key() -> None:
    """SIRC repeats a full frame on a 45-ms period."""
    sent = SonyCommand(address=0x4B9, address_bits=13, command=7, repeat_count=2)
    received = SonyCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert (received.address, received.command, received.repeat_count) == (0x4B9, 7, 2)


@pytest.mark.parametrize("command", _DECODE_CASES)
def test_decoder_round_trip_fields(command: SonyCommand) -> None:
    """Decode edge-valued fields and preserve their protocol meaning."""
    raw = command.get_raw_timings()
    result = type(command).from_raw_timings(raw)
    assert result is not None
    assert result.get_raw_timings() == raw
    assert result.address == command.address
    assert result.address_bits == command.address_bits
    assert result.command == command.command
    assert result.repeat_count == command.repeat_count


@pytest.mark.parametrize("command", _DECODE_CASES)
@pytest.mark.parametrize("prefix", [0, 1, 5])
def test_decoder_truncated(command: SonyCommand, prefix: int) -> None:
    """A partial leader or payload cannot be a complete command."""
    assert type(command).from_raw_timings(command.get_raw_timings()[:prefix]) is None
