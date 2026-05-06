"""Tests for the Samsung32 IR command encoder."""

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
