"""Tests for the Samsung AC Variant 1 IR command encoder."""

from infrared_protocols.codes.samsung.ac import SamsungACVariant1StateBuilder


def test_samsung_variant1_ac_command_get_raw_timings() -> None:
    """Test standard 21-byte environment state payloads compilation."""
    cool_cases = [
        ("cool", 24, "auto", [
            0x2A, 0x20, 0xF9, 0x00, 0x00, 0x00, 0x00,
            0xDF, 0x00, 0xE9, 0x07, 0x00, 0x00, 0x00,
            0x80, 0x06, 0x88, 0xFB, 0xC7, 0x01, 0x46
        ]),
        ("heat", 24, "auto", [
            0x2A, 0x20, 0xF9, 0x00, 0x00, 0x00, 0x00,
            0xDF, 0x00, 0xE9, 0x07, 0x00, 0x00, 0x00,
            0x80, 0x06, 0x88, 0xFB, 0xC7, 0x01, 0x06
        ]),
    ]

    leader_high, leader_low = 3000, 3000
    bit_high, zero_low, one_low, gap_low = 600, 400, 1400, 4000

    for mode, temp, fan, expected_payload in cool_cases:
        expected_timings = _compile_timings(expected_payload, leader_high, leader_low, bit_high, one_low, zero_low, gap_low)
        builder = SamsungACVariant1StateBuilder(hvac_mode=mode, target_temperature=temp, fan_mode=fan)
        assert builder.to_command().get_raw_timings() == expected_timings


def test_samsung_variant1_special_functions_timings() -> None:
    """Test short toggle command generation containing structural padding."""
    special_cases = [
        ("turbo", SamsungACVariant1StateBuilder(hvac_mode="cool", target_temperature=24, fan_mode="auto", turbo=True), [
            0x2A, 0x20, 0xF9, 0x00, 0x00, 0x00, 0x00, 0xDF, 0x00, 0x61, 0xFF, 0x3B, 0xC0, 0x08, 0x78,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ]),
        ("swing", SamsungACVariant1StateBuilder(hvac_mode="cool", target_temperature=24, fan_mode="auto", swing=True), [
            0x14, 0x90, 0x7C, 0x00, 0x00, 0x00, 0x80, 0x6F, 0x80, 0xC0, 0x6B, 0x1C, 0x60, 0x04, 0x3C,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ]),
        ("smart_saver", SamsungACVariant1StateBuilder(hvac_mode="cool", target_temperature=24, fan_mode="auto", smart_saver=True), [
            0x28, 0x20, 0xF9, 0x00, 0x00, 0x00, 0x00, 0xDF, 0x00, 0x69, 0xD7, 0x3F, 0xC0, 0x08, 0x78,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ]),
    ]

    leader_high, leader_low = 3000, 3000
    bit_high, zero_low, one_low, gap_low = 600, 400, 1400, 4000

    for name, builder, expected_payload in special_cases:
        expected_timings = _compile_timings(expected_payload, leader_high, leader_low, bit_high, one_low, zero_low, gap_low)
        assert builder.to_command().get_raw_timings() == expected_timings, f"Failed length check for special function: {name}"


def _compile_timings(payload, leader_high, leader_low, bit_high, one_low, zero_low, gap_low) -> list[int]:
    """Helper method replicating the hardware IR modulation sequence."""
    timings = []
    num_packets = (len(payload) + 6) // 7
    
    for packet_idx in range(num_packets):
        timings.append(leader_high)
        timings.append(-leader_low)
        start_byte = packet_idx * 7
        packet_bytes = payload[start_byte : start_byte + 7]
        for byte in packet_bytes:
            for _ in range(8):
                bit = byte & 1
                timings.append(bit_high)
                timings.append(-one_low if bit else -zero_low)
                byte >>= 1
        if packet_idx < num_packets - 1:
            timings.append(bit_high)
            timings.append(-gap_low)
    timings.append(bit_high)
    return timings