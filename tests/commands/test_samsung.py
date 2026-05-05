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
