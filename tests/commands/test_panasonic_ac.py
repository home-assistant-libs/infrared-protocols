"""Tests for the generic Panasonic A/C IR protocol."""

from infrared_protocols.commands.panasonic_ac import (
    MODULATION_HZ,
    PanasonicAcCommand,
    checksum,
    state_to_timings,
)

# A minimal two-section state: 8-byte section 1 + 4-byte section 2.
SAMPLE_STATE: list[int] = [
    0x02,
    0x20,
    0xE0,
    0x04,
    0x00,
    0x00,
    0x00,
    0x06,
    0x02,
    0x20,
    0xE0,
    0x04,
]


def test_checksum_sum_mod_256() -> None:
    """Test checksum sums the inclusive byte range modulo 256."""
    state = [0x00, 0xFF, 0x01, 0x05]
    assert checksum(state, 1, 3) == (0xFF + 0x01 + 0x05) & 0xFF


def test_state_to_timings_leader() -> None:
    """Test encoding starts with the Panasonic leader."""
    timings = state_to_timings(SAMPLE_STATE)
    assert timings[:2] == [3456, -1728]


def test_state_to_timings_section_split() -> None:
    """Test both sections are encoded with their own leader and gap.

    Each byte is 8 bits (2 timings/bit); each section adds a leader pair and a
    trailing mark/gap pair. The first section gap is the inter-section gap and
    the final gap is the message gap.
    """
    timings = state_to_timings(SAMPLE_STATE)
    bits_per_section1 = 8 * 8 * 2
    section1_len = 2 + bits_per_section1 + 2
    # Section 1 trailing gap is the inter-section gap.
    assert timings[section1_len - 1] == -10000
    # Section 2 leader follows immediately.
    assert timings[section1_len : section1_len + 2] == [3456, -1728]
    # Final timing is the message gap.
    assert timings[-1] == -100000


def test_command_get_raw_timings_matches_helper() -> None:
    """Test the command wrapper returns the same timings as the helper."""
    command = PanasonicAcCommand(state=SAMPLE_STATE)
    assert command.modulation == MODULATION_HZ
    assert command.repeat_count == 0
    assert command.get_raw_timings() == state_to_timings(SAMPLE_STATE)
