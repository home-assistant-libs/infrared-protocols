"""Tests for the SONY SIRC IR command encoder."""

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
    command = SonyCommand(address=0x01, address_bits=5, command=0x15, repeat_count=0)
    timings = command.get_raw_timings()
    assert timings == expected_raw_timings
    assert command.modulation == 40000

    # Trailer low = 45000 - (2400 + (4*1800) + (8*1200)) = 25800
    command_with_repeats = SonyCommand(
        address=command.address,
        address_bits=command.address_bits,
        command=command.command,
        repeat_count=2,
    )
    timings_with_repeats = command_with_repeats.get_raw_timings()
    assert timings_with_repeats == [
        *expected_raw_timings,
        *expected_raw_timings,
        *expected_raw_timings,
    ]


def test_sony_command_get_raw_timings_15_bit() -> None:
    """Test SONY SIRC 15-bit framing for an 8-bit address."""
    command = SonyCommand(address=0xA8, address_bits=8, command=0x02, repeat_count=0)
    timings = command.get_raw_timings()

    # 15-bit frame: leader high + 15 low/high pairs + trailer low
    assert len(timings) == 2 + (15 * 2)
    assert timings[0] == 2400
    assert timings[-1] == -22200


def test_sony_command_get_raw_timings_20_bit() -> None:
    """Test SONY SIRC 20-bit framing for a 13-bit address."""
    command = SonyCommand(address=0x1ABC, address_bits=13, command=0x34, repeat_count=0)
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
