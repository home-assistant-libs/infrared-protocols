"""Tests for the NEC IR command."""

import pytest

from infrared_protocols.commands.nec1_f16 import NEC1F16Command

ADDRESS = 0xFB04
FUNCTION = 0xDB
SUBFUNCTION = 0x40

# NEC1-f16 frame for ADDRESS / FUNCTION / SUBFUNCTION.
FRAME: list[int] = [
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
    -1687,
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


def test_nec1_f16_command_get_raw_timings() -> None:
    """Test NEC1-f16 command raw timings generation."""
    command = NEC1F16Command(
        address=ADDRESS,
        function=FUNCTION,
        subfunction=SUBFUNCTION,
        repeat_count=0,
    )

    timings = command.get_raw_timings()

    assert timings == FRAME


def test_nec1_f16_command_from_raw_timings() -> None:
    """Test decoding raw timings produced by NEC1-f16 commands."""
    command = NEC1F16Command.from_raw_timings(FRAME)

    assert command is not None
    assert command.address == ADDRESS
    assert command.function == FUNCTION
    assert command.subfunction == SUBFUNCTION
    assert command.repeat_count == 0


def test_nec1_f16_command_from_raw_timings_with_repeats() -> None:
    """Test decoding raw timings that include trailing repeat codes."""
    command = NEC1F16Command.from_raw_timings([*FRAME, *TWO_REPEATS_TAIL])
    assert command is not None
    assert command.address == ADDRESS
    assert command.function == FUNCTION
    assert command.subfunction == SUBFUNCTION
    assert command.repeat_count == 2


def test_nec1_f16_command_from_raw_timings_within_tolerance() -> None:
    """Test decoding succeeds when timings deviate within the 40% tolerance."""
    # Skew every value by ~20% in alternating directions; still within tolerance.
    skewed = [
        int(t * 1.2) if i % 2 == 0 else int(t * 0.8)
        for i, t in enumerate(FRAME)
    ]
    command = NEC1F16Command.from_raw_timings(skewed)
    assert command is not None
    assert command.address == ADDRESS
    assert command.function == FUNCTION
    assert command.subfunction == SUBFUNCTION


@pytest.mark.parametrize(
    "timings",
    [
        pytest.param([], id="empty"),
        pytest.param([9000, -4500, 562], id="too_short"),
        pytest.param([1000, *FRAME[1:]], id="invalid_leader_high"),
        pytest.param([FRAME[0], -100, *FRAME[2:]], id="invalid_leader_low"),
        # First bit's space (index 3) set well outside both the 0 and 1 ranges.
        pytest.param([*FRAME[:3], -3000, *FRAME[4:]], id="invalid_bit"),
        # End pulse (index 66) too long to be a 562µs pulse.
        pytest.param([*FRAME[:66], 5000], id="invalid_end_pulse"),
    ],
)
def test_nec1_f16_command_from_raw_timings_invalid(timings: list[int]) -> None:
    """Test from_raw_timings returns None for malformed inputs."""
    assert NEC1F16Command.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    ("trailing", "expected_repeat_count"),
    [
        pytest.param([-12345], 0, id="trailing_garbage"),
        pytest.param([-41000, 9000], 0, id="incomplete_repeat"),
        pytest.param([-100, 9000, -2250, 562], 0, id="invalid_repeat_gap"),
        pytest.param([*TWO_REPEATS_TAIL, -12345], 2,
                        id="repeats_then_trailing_garbage"),
    ],
)
def test_nec1_f16_command_from_raw_timings_ignores_trailing(
    trailing: list[int], expected_repeat_count: int
) -> None:
    """Test that invalid trailing timings are ignored without dropping valid repeats."""
    command = NEC1F16Command.from_raw_timings([*FRAME, *trailing])
    assert command is not None
    assert command.address == ADDRESS
    assert command.function == FUNCTION
    assert command.subfunction == SUBFUNCTION
    assert command.repeat_count == expected_repeat_count


def test_nec1_f16_command_get_raw_timings_with_repeats() -> None:
    """Test NEC1-f16 command raw timings generation with repeats."""
    command = NEC1F16Command(
        address=ADDRESS,
        function=FUNCTION,
        subfunction=SUBFUNCTION,
        repeat_count=2,
    )

    timings = command.get_raw_timings()

    assert timings == [*FRAME, *TWO_REPEATS_TAIL]


def test_nec1_f16_command_from_raw_timings_invalid_bit_high() -> None:
    """Test decoding rejects an invalid bit high pulse."""
    timings = [*FRAME]
    timings[2] = 5000

    assert NEC1F16Command.from_raw_timings(timings) is None
