"""Tests for the Samsung32 IR command encoder."""

from itertools import product

import pytest

from infrared_protocols.commands._timing import PulseTiming, byte_bits
from infrared_protocols.commands.samsung import Samsung32Command


def test_samsung32_command_get_raw_timings_standard() -> None:
    """Test Samsung32 command raw timings for standard 8-bit address."""
    # Samsung32 Power: address=0x07, command=0x02
    # Data: 0x07 (addr) + 0x07 (addr) + 0x02 (cmd) + 0xFD (~cmd), LSB first
    expected_raw_timings = [
        # Leader
        4500,
        -4500,
        # Address low: 0x07 (LSB first: 1,1,1,0,0,0,0,0)
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        # Address high: 0x07 (LSB first: 1,1,1,0,0,0,0,0)
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        # Command: 0x02 (LSB first: 0,1,0,0,0,0,0,0)
        560,
        -560,
        560,
        -1690,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        # ~Command: 0xFD (LSB first: 1,0,1,1,1,1,1,1)
        560,
        -1690,
        560,
        -560,
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        # End pulse
        560,
    ]
    command = Samsung32Command(address=0x07, command=0x02, repeat_count=0)
    timings = command.get_raw_timings()
    assert timings == expected_raw_timings
    assert command.modulation == 38000

    # Frame duration: 4500+4500 + 32*560 + 14*1690 + 18*560 + 560 = 61220
    # Gap = 108000 - 61220 = 46780
    command_with_repeats = Samsung32Command(
        address=command.address,
        command=command.command,
        repeat_count=2,
    )
    timings_with_repeats = command_with_repeats.get_raw_timings()
    assert timings_with_repeats == [
        *expected_raw_timings,
        -46780,
        *expected_raw_timings,
        -46780,
        *expected_raw_timings,
    ]


def test_samsung32_command_get_raw_timings_extended() -> None:
    """Test Samsung32 command raw timings for extended 16-bit address."""
    # Extended Samsung32: address=0x04FB, command=0x08
    # Data: 0xFB (addr_low) + 0x04 (addr_high) + 0x08 (cmd) + 0xF7 (~cmd),
    # LSB first
    expected_raw_timings = [
        # Leader
        4500,
        -4500,
        # Address low: 0xFB (LSB first: 1,1,0,1,1,1,1,1)
        560,
        -1690,
        560,
        -1690,
        560,
        -560,
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        # Address high: 0x04 (LSB first: 0,0,1,0,0,0,0,0)
        560,
        -560,
        560,
        -560,
        560,
        -1690,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        # Command: 0x08 (LSB first: 0,0,0,1,0,0,0,0)
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -1690,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        560,
        -560,
        # ~Command: 0xF7 (LSB first: 1,1,1,0,1,1,1,1)
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        560,
        -560,
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        560,
        -1690,
        # End pulse
        560,
    ]
    command = Samsung32Command(address=0x04FB, command=0x08, repeat_count=0)
    timings = command.get_raw_timings()
    assert timings == expected_raw_timings

    # Frame duration: 4500+4500 + 32*560 + 16*1690 + 16*560 + 560 = 63480
    # Gap = 108000 - 63480 = 44520
    command_with_repeats = Samsung32Command(
        address=command.address,
        command=command.command,
        repeat_count=2,
    )
    timings_with_repeats = command_with_repeats.get_raw_timings()
    assert timings_with_repeats == [
        *expected_raw_timings,
        -44520,
        *expected_raw_timings,
        -44520,
        *expected_raw_timings,
    ]


_DECODE_CASES = [
    pytest.param(
        command,
        {65535: 255, 257: 1}.get(command.address, command.address),
        id=type(command).__name__ + "-" + str(vars(command)),
    )
    for command in [
        *[
            Samsung32Command(address=a, command=c, repeat_count=r)
            for a, c, r in product((0, 255, 256, 257, 65535), (0, 255), (0, 2))
        ]
    ]
]


@pytest.mark.parametrize("scale", [0.7, 1.3])
def test_samsung_scaled_and_partial_repeat(scale: float) -> None:
    """A complete command survives a clipped final held-key repeat."""
    raw = Samsung32Command(address=7, command=2, repeat_count=1).get_raw_timings()[:-10]
    received = Samsung32Command.from_raw_timings([round(t * scale) for t in raw])
    assert received is not None
    assert (received.address, received.command, received.repeat_count) == (7, 2, 0)


@pytest.mark.parametrize("command,expected_address", _DECODE_CASES)
def test_decoder_round_trip_fields(
    command: Samsung32Command, expected_address: int
) -> None:
    """Decode edge-valued fields and preserve their protocol meaning."""
    raw = command.get_raw_timings()
    result = type(command).from_raw_timings(raw)
    assert result is not None
    assert result.get_raw_timings() == raw
    assert result.command == command.command
    assert result.repeat_count == command.repeat_count
    assert result.address == expected_address


@pytest.mark.parametrize(
    "command", [pytest.param(c.values[0], id=c.id) for c in _DECODE_CASES]
)
@pytest.mark.parametrize("prefix", [0, 1, 5])
def test_decoder_truncated(command: Samsung32Command, prefix: int) -> None:
    """A partial leader or payload cannot be a complete command."""
    assert type(command).from_raw_timings(command.get_raw_timings()[:prefix]) is None


def test_extended_zero_high_byte_cannot_change_address() -> None:
    """Reject an extended address that the public encoder would normalize away."""
    raw = [
        4500,
        -4500,
        *PulseTiming(560, 560, 1690).encode(byte_bits(bytes([0x12, 0, 0x34, 0xCB]))),
        560,
    ]
    assert Samsung32Command.from_raw_timings(raw) is None
