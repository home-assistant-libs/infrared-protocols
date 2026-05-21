"""Tests for the Kaseikyo format IR command."""

from infrared_protocols.commands.kaseikyo import KaseikyoCommand


def test_kaseikyo_command_get_raw_timings() -> None:
    """Test Kaseikyo command raw timings."""
    # Kaseikyo format frame for address=0x1234, data=[0x5, 0x67], no error correction
    # T = 421μs (base unit for 38kHz with burst pulse of 16)
    expected_raw_timings = [
        # Leader
        3368,
        -1684,
        # Address low: 0x34 (LSB first: 0,0,1,0,1,1,0,0)
        421,
        -421,
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        421,
        -1263,
        421,
        -1263,
        421,
        -421,
        421,
        -421,
        # Address high: 0x12 (LSB first: 0,1,0,0,1,0,0,0)
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        421,
        -421,
        421,
        -421,
        # Parity (Address XORed per 4 bits): 0x1^0x2^0x3^0x4 = 0x4 (LSB first: 0,0,1,0)
        421,
        -421,
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        # Data 0: 0x5 (LSB first: 1,0,1,0)
        421,
        -1263,
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        # Data 1: 0x67 (LSB first: 1,1,1,0,0,1,1,0)
        421,
        -1263,
        421,
        -1263,
        421,
        -1263,
        421,
        -421,
        421,
        -421,
        421,
        -1263,
        421,
        -1263,
        421,
        -421,
        # End pulse
        421,
    ]
    command = KaseikyoCommand(address=0x1234, data=bytes([0x50, 0x67]))
    timings = command.get_raw_timings()
    assert timings == expected_raw_timings
    assert command.modulation == 38000

    # Frame duration: 3368 + 1684 + 32*421 + 13*1263 + 19*421 + 421 = 43363
    #   Gap = 130000 - 43363 = 86637
    # Repeat code duration: 3368 + 3368 + 421 = 7157
    #   Gap = 130000 - 7157 = 122843
    command_with_repeats = KaseikyoCommand(
        address=command.address,
        data=command.data,
        repeat_count=2,
    )
    timings_with_repeats = command_with_repeats.get_raw_timings()
    expected_repeat_code_raw_timings = [
        # Leader
        3368,
        -3368,
        # End pulse
        421,
    ]
    assert timings_with_repeats == [
        *expected_raw_timings,
        -86637,
        *expected_repeat_code_raw_timings,
        -122843,
        *expected_repeat_code_raw_timings,
    ]
