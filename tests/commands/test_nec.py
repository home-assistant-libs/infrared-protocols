"""Tests for the NEC IR command."""

import pytest

from infrared_protocols.commands.nec import NECCommand

STANDARD_ADDRESS = 0x04
EXTENDED_ADDRESS = 0x04FB
COMMAND = 0x08
# Standard NEC has no extended-vs-standard distinction in the raw timings, so
# from_raw_timings always returns the 16-bit form: low byte = address,
# high byte = ~address. For STANDARD_ADDRESS (0x04) that is 0xFB04.
STANDARD_DECODED_ADDRESS = STANDARD_ADDRESS | ((~STANDARD_ADDRESS & 0xFF) << 8)

# NEC frame for STANDARD_ADDRESS / COMMAND (standard 8-bit address).
STANDARD_FRAME: list[int] = [
    9000,
    -4500,
    562,
    -562,
    562,
    -562,
    562,
    -1687,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -1687,
    562,
    -1687,
    562,
    -562,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -1687,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -562,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
]

# NEC frame for EXTENDED_ADDRESS / COMMAND (extended 16-bit address).
EXTENDED_FRAME: list[int] = [
    9000,
    -4500,
    562,
    -1687,
    562,
    -1687,
    562,
    -562,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -562,
    562,
    -562,
    562,
    -1687,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -1687,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -562,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
]

# Trailing repeat codes for two repeats: initial 41ms gap, then standard 96ms gaps.
TWO_REPEATS_TAIL: list[int] = [
    -41000,
    9000,
    -2250,
    562,
    -96000,
    9000,
    -2250,
    562,
]


@pytest.mark.parametrize(
    ("address", "expected_frame"),
    [
        pytest.param(STANDARD_ADDRESS, STANDARD_FRAME, id="standard"),
        pytest.param(EXTENDED_ADDRESS, EXTENDED_FRAME, id="extended"),
    ],
)
def test_nec_command_get_raw_timings(address: int, expected_frame: list[int]) -> None:
    """Test NEC command raw timings generation."""
    command = NECCommand(address=address, command=COMMAND, repeat_count=0)
    timings = command.get_raw_timings()
    assert timings == expected_frame
    assert command.modulation == 38000

    # Same command now with 2 repeats
    command_with_repeats = NECCommand(
        address=command.address,
        command=command.command,
        modulation=command.modulation,
        repeat_count=2,
    )
    timings_with_repeats = command_with_repeats.get_raw_timings()
    assert timings_with_repeats == [*expected_frame, *TWO_REPEATS_TAIL]


@pytest.mark.parametrize(
    ("frame", "expected_address"),
    [
        pytest.param(STANDARD_FRAME, STANDARD_DECODED_ADDRESS, id="standard"),
        pytest.param(EXTENDED_FRAME, EXTENDED_ADDRESS, id="extended"),
    ],
)
def test_nec_command_from_raw_timings(frame: list[int], expected_address: int) -> None:
    """Test decoding raw timings produced by NEC commands."""
    command = NECCommand.from_raw_timings(frame)
    assert command is not None
    assert command.address == expected_address
    assert command.command == COMMAND
    assert command.repeat_count == 0
    assert command.modulation == 38000


def test_nec_command_from_raw_timings_with_repeats() -> None:
    """Test decoding raw timings that include trailing repeat codes."""
    command = NECCommand.from_raw_timings([*STANDARD_FRAME, *TWO_REPEATS_TAIL])
    assert command is not None
    assert command.address == STANDARD_DECODED_ADDRESS
    assert command.command == COMMAND
    assert command.repeat_count == 2


def test_nec_command_from_raw_timings_within_tolerance() -> None:
    """Test decoding succeeds when timings deviate within the 40% tolerance."""
    # Skew every value by ~20% in alternating directions; still within tolerance.
    skewed = [
        int(t * 1.2) if i % 2 == 0 else int(t * 0.8)
        for i, t in enumerate(STANDARD_FRAME)
    ]
    command = NECCommand.from_raw_timings(skewed)
    assert command is not None
    assert command.address == STANDARD_DECODED_ADDRESS
    assert command.command == COMMAND


@pytest.mark.parametrize(
    "timings",
    [
        pytest.param([], id="empty"),
        pytest.param([9000, -4500, 562], id="too_short"),
        pytest.param([1000, *STANDARD_FRAME[1:]], id="invalid_leader_high"),
        pytest.param(
            [STANDARD_FRAME[0], -100, *STANDARD_FRAME[2:]], id="invalid_leader_low"
        ),
        # First bit's space (index 3) set well outside both the 0 and 1 ranges.
        pytest.param(
            [*STANDARD_FRAME[:3], -3000, *STANDARD_FRAME[4:]], id="invalid_bit"
        ),
        # End pulse (index 66) too long to be a 562µs pulse.
        pytest.param([*STANDARD_FRAME[:66], 5000], id="invalid_end_pulse"),
        # Indices 64/65 carry the most-significant bit of command_inverted (bit 31,
        # transmitted last). Flipping it breaks the command ^ ~command == 0xFF check.
        # STANDARD_FRAME[65] is -1687 (bit=1); flipping to -562 makes bit=0.
        pytest.param(
            [*STANDARD_FRAME[:65], -562, *STANDARD_FRAME[66:]], id="invalid_checksum"
        ),
        pytest.param([*STANDARD_FRAME, -12345], id="trailing_garbage"),
        pytest.param([*STANDARD_FRAME, -41000, 9000], id="incomplete_repeat"),
        pytest.param(
            [*STANDARD_FRAME, -100, 9000, -2250, 562], id="invalid_repeat_gap"
        ),
    ],
)
def test_nec_command_from_raw_timings_invalid(timings: list[int]) -> None:
    """Test from_raw_timings returns None for malformed inputs."""
    assert NECCommand.from_raw_timings(timings) is None
