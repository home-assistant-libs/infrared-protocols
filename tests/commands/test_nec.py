"""Tests for the NEC IR command."""

import pytest

from infrared_protocols.commands.nec import NECCommand

STANDARD_ADDRESS = 0x04
EXTENDED_ADDRESS = 0x04FB
COMMAND = 0x08
NEC1_F16_ADDRESS = 0xFB04
NEC1_F16_COMMAND = 0xDB
NEC1_F16_SUBFUNCTION = 0x00
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

# NEC1-f16 frame for NEC1_F16_ADDRESS / NEC1_F16_COMMAND / NEC1_F16_SUBFUNCTION.
NEC1_F16_FRAME: list[int] = [
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
    -562,
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


def test_nec1_f16_command_get_raw_timings() -> None:
    """Test NEC1-f16 command raw timings generation."""
    command = NECCommand(
        address=NEC1_F16_ADDRESS,
        command=NEC1_F16_COMMAND,
        subfunction=NEC1_F16_SUBFUNCTION,
    )

    assert command.get_raw_timings() == NEC1_F16_FRAME
    assert command.subfunction == NEC1_F16_SUBFUNCTION


@pytest.mark.parametrize(
    ("address", "command"),
    [
        pytest.param(-1, COMMAND, id="address_negative"),
        pytest.param(0x10000, COMMAND, id="address_too_large"),
        pytest.param(STANDARD_ADDRESS, -1, id="command_negative"),
        pytest.param(STANDARD_ADDRESS, 0x100, id="command_too_large"),
    ],
)
def test_nec_command_rejects_out_of_range(address: int, command: int) -> None:
    """Test that out-of-range address or command values raise ValueError."""
    with pytest.raises(ValueError, match="8-bit value|16-bit value"):
        NECCommand(address=address, command=command)


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
    assert command.subfunction is None
    assert command.repeat_count == 0
    assert command.modulation == 38000


def test_nec1_f16_command_from_raw_timings() -> None:
    """Test decoding raw timings produced by NEC1-f16 commands."""
    command = NECCommand.from_raw_timings(NEC1_F16_FRAME, decode_subfunction=True)

    assert command is not None
    assert command.address == NEC1_F16_ADDRESS
    assert command.command == NEC1_F16_COMMAND
    assert command.subfunction == NEC1_F16_SUBFUNCTION
    assert command.repeat_count == 0
    assert command.modulation == 38000


def test_nec_command_from_raw_timings_rejects_nec1_f16() -> None:
    """Test strict NEC decoding rejects an NEC1-f16 command suffix."""
    assert NECCommand.from_raw_timings(NEC1_F16_FRAME) is None


def test_nec1_f16_command_from_raw_timings_with_repeats() -> None:
    """Test NEC1-f16 decoding counts trailing repeat codes."""
    command = NECCommand.from_raw_timings(
        [*NEC1_F16_FRAME, *TWO_REPEATS_TAIL], decode_subfunction=True
    )

    assert command is not None
    assert command.repeat_count == 2


def test_nec1_f16_command_uses_supplied_16_bit_address() -> None:
    """Test NEC1-f16 does not invert an address below 0x100."""
    command = NECCommand(address=0x04, command=0xDB, subfunction=0x32)

    decoded = NECCommand.from_raw_timings(
        command.get_raw_timings(), decode_subfunction=True
    )

    assert decoded is not None
    assert decoded.address == 0x0004
    assert decoded.command == 0xDB
    assert decoded.subfunction == 0x32


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
        pytest.param(
            [*STANDARD_FRAME[:2], 5000, *STANDARD_FRAME[3:]],
            id="invalid_bit_high",
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
    ],
)
def test_nec_command_from_raw_timings_invalid(timings: list[int]) -> None:
    """Test from_raw_timings returns None for malformed inputs."""
    assert NECCommand.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    ("trailing", "expected_repeat_count"),
    [
        pytest.param([-12345], 0, id="trailing_garbage"),
        pytest.param([-41000, 9000], 0, id="incomplete_repeat"),
        pytest.param([-100, 9000, -2250, 562], 0, id="invalid_repeat_gap"),
        pytest.param(
            [*TWO_REPEATS_TAIL, -12345], 2, id="repeats_then_trailing_garbage"
        ),
    ],
)
def test_nec_command_from_raw_timings_ignores_trailing(
    trailing: list[int], expected_repeat_count: int
) -> None:
    """Test that invalid trailing timings are ignored without dropping valid repeats."""
    command = NECCommand.from_raw_timings([*STANDARD_FRAME, *trailing])
    assert command is not None
    assert command.address == STANDARD_DECODED_ADDRESS
    assert command.command == COMMAND
    assert command.repeat_count == expected_repeat_count
