"""Tests for the RC-6 IR command encoder."""

import json
from itertools import product
from pathlib import Path

import pytest

from infrared_protocols.commands.rc6 import RC6Command

# A Philips TV play press: address 0x00, command 0x2C, toggle set. Verified
# against a real capture of a Philips universal remote, which agrees on every
# edge to within receiver jitter.
#
# Frame layout, in order: leader, start bit (1), three mode bits (000), the
# double-width trailer bit carrying the toggle, then address and command, both
# 8 bits MSB first. Field boundaries do not line up with entry boundaries,
# because adjacent Manchester halves of equal sign merge into one entry.
PHILIPS_PLAY_TIMINGS: list[int] = [
    2664, -888, 444, -888, 444, -444, 444, -444, 1332, -1332,
    444, -444, 444, -444, 444, -444, 444, -444, 444, -444,
    444, -444, 444, -444, 444, -444, 444, -444, 888, -888,
    888, -444, 444, -888, 444, -444, 444,
]  # fmt: skip

# Every RC-6 mode 0 frame occupies the same 23088µs regardless of its payload.
RC6_FRAME_DURATION_US = 23088
# A frame whose last bit is logic '1' ends on a space half-bit, which is dropped
# because the signal-free time that follows swallows it.
RC6_TRAILING_SPACE_US = 444


def test_rc6_command_get_raw_timings_philips_play() -> None:
    """Test RC-6 timings for a Philips TV play press.

    Philips televisions use RC-6 mode 0 with address 0x00. Command 0x2C is
    play, and this frame was cross-checked against a real remote capture.
    """
    command = RC6Command(address=0x00, command=0x2C, toggle=1, repeat_count=0)
    assert command.get_raw_timings() == PHILIPS_PLAY_TIMINGS
    assert command.modulation == 36000


def test_rc6_command_get_raw_timings_philips_play_with_repeat() -> None:
    """Test that a repeated frame is spaced on the 107ms RC-6 period.

    The captured remote sends two frames per press, separated by ~84ms, which
    is the 107ms period minus the 23088µs frame.
    """
    command = RC6Command(address=0x00, command=0x2C, toggle=1, repeat_count=1)
    assert command.get_raw_timings() == [
        *PHILIPS_PLAY_TIMINGS,
        -83912,
        *PHILIPS_PLAY_TIMINGS,
    ]


def test_rc6_command_get_raw_timings_zero_address_zero_command() -> None:
    """Test RC-6 timings for the all-zero address/command edge case.

    With every payload bit zero, each bit contributes a space then a burst, so
    the frame is a long run of merged 444µs halves.
    """
    expected_raw_timings = [
        2664, -888, 444, -888, 444, -444, 444, -444, 444, -888,
        888, -444, 444, -444, 444, -444, 444, -444, 444, -444,
        444, -444, 444, -444, 444, -444, 444, -444, 444, -444,
        444, -444, 444, -444, 444, -444, 444, -444, 444, -444,
        444, -444, 444,
    ]  # fmt: skip
    command = RC6Command(address=0x00, command=0x00, toggle=0, repeat_count=0)
    assert command.get_raw_timings() == expected_raw_timings


@pytest.mark.parametrize(
    ("toggle", "expected_trailer"),
    [
        pytest.param(0, [-888, 888], id="toggle_clear"),
        pytest.param(1, [-1332, 444], id="toggle_set"),
    ],
)
def test_rc6_command_trailer_bit_is_double_width(
    toggle: int, expected_trailer: list[int]
) -> None:
    """The trailer bit spans four units, twice a normal bit.

    A set toggle puts its burst first, so it merges with the preceding mode
    bit's burst into 1332µs (444 + 888). A clear toggle puts its space first,
    giving an 888µs space followed by an 888µs burst.
    """
    timings = RC6Command(address=0x00, command=0x00, toggle=toggle).get_raw_timings()
    assert timings[9:11] == expected_trailer


@pytest.mark.parametrize(
    ("address", "command", "expected_duration"),
    [
        pytest.param(0x00, 0x00, RC6_FRAME_DURATION_US, id="last_bit_clear"),
        pytest.param(0x00, 0x2C, RC6_FRAME_DURATION_US, id="last_bit_clear_mixed"),
        pytest.param(
            0xFF,
            0xFF,
            RC6_FRAME_DURATION_US - RC6_TRAILING_SPACE_US,
            id="last_bit_set_all_ones",
        ),
        pytest.param(
            0x00,
            0x0F,
            RC6_FRAME_DURATION_US - RC6_TRAILING_SPACE_US,
            id="last_bit_set",
        ),
    ],
)
def test_rc6_command_frame_duration(
    address: int, command: int, expected_duration: int
) -> None:
    """A frame always spans 23088µs, less the dropped trailing space if any."""
    timings = RC6Command(address=address, command=command).get_raw_timings()
    assert sum(abs(t) for t in timings) == expected_duration


def test_rc6_command_toggle_changes_frame_but_not_duration() -> None:
    """Flipping the toggle must change the frame while preserving its length."""
    toggle_clear = RC6Command(address=0x04, command=0x0C, toggle=0).get_raw_timings()
    toggle_set = RC6Command(address=0x04, command=0x0C, toggle=1).get_raw_timings()
    assert toggle_clear != toggle_set
    assert sum(abs(t) for t in toggle_clear) == sum(abs(t) for t in toggle_set)


def test_rc6_command_address_and_command_are_distinct_fields() -> None:
    """Swapping address and command must produce a different frame."""
    assert (
        RC6Command(address=0x12, command=0x34).get_raw_timings()
        != RC6Command(address=0x34, command=0x12).get_raw_timings()
    )


@pytest.mark.parametrize(
    ("address", "command"),
    [
        (-1, 0x00),
        (0x100, 0x00),
        (0x00, -1),
        (0x00, 0x100),
    ],
)
def test_rc6_command_rejects_out_of_range(address: int, command: int) -> None:
    """RC-6 mode 0 fields are both 8-bit — anything else is invalid."""
    with pytest.raises(ValueError):
        RC6Command(address=address, command=command, toggle=0)


_CAPTURES = json.loads(
    (Path(__file__).parents[1] / "fixtures/receiver_captures.json").read_text()
)["captures"]

_DECODE_CASES = [
    pytest.param(
        RC6Command(address=a, command=c, toggle=t, repeat_count=r, mode=m),
        id=f"{a:#04x}-{c:#04x}-t{t}-r{r}-m{m}",
    )
    for a, c, t, r, m in product((0, 255), (0, 255), (0, 1), (0, 2), (0, 1, 6, 7))
]


def test_rc6_nonzero_mode_order() -> None:
    """Mode 6 transmits its bits in the documented MSB-first mode field."""
    raw = RC6Command(mode=6, address=0, command=0, toggle=0).get_raw_timings()
    assert raw[:11] == [2664, -888, 444, -444, 444, -444, 444, -888, 444, -888, 888]


def test_rc6_half_clock_rejected() -> None:
    """Half-unit noise cannot supply a valid clock or cause division by zero."""
    assert RC6Command.from_raw_timings([2664, -888, *([222, -222] * 22)]) is None


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(c["timings"], id=f"rc6a-{i}")
        for i, c in enumerate(_CAPTURES)
        if c["protocol"] == "rc6a"
    ],
)
def test_unsupported_rc6a(raw: list[int]) -> None:
    """The fixed 20-bit RC6 decoder cannot silently truncate a longer RC6A word."""
    assert RC6Command.from_raw_timings(raw) is None


@pytest.mark.parametrize(
    "raw,address,command,toggle,mode",
    [
        pytest.param(
            c["timings"],
            c["address"],
            c["command"],
            c["toggle"],
            c["mode"],
            id=f"{c['address']:x}-{c['command']:x}",
        )
        for c in _CAPTURES
        if c["protocol"] == "rc6"
    ],
)
def test_recorded_rc6(
    raw: list[int], address: int, command: int, toggle: int, mode: int
) -> None:
    """Recover independent recorded fields and the toggle bit."""
    result = RC6Command.from_raw_timings(raw)
    assert result is not None
    assert (result.address, result.command, result.toggle) == (address, command, toggle)
    assert result.mode == mode


@pytest.mark.parametrize("command", _DECODE_CASES)
def test_decoder_round_trip_fields(command: RC6Command) -> None:
    """Decode edge-valued fields and preserve their protocol meaning."""
    raw = command.get_raw_timings()
    result = RC6Command.from_raw_timings(raw)
    assert result is not None
    assert result.get_raw_timings() == raw
    assert result.address == command.address
    assert result.command == command.command
    assert result.toggle == command.toggle
    assert result.mode == command.mode
    assert result.repeat_count == command.repeat_count


@pytest.mark.parametrize("command", _DECODE_CASES)
@pytest.mark.parametrize("prefix", [0, 1, 5])
def test_decoder_truncated(command: RC6Command, prefix: int) -> None:
    """A partial leader or payload cannot be a complete command."""
    assert RC6Command.from_raw_timings(command.get_raw_timings()[:prefix]) is None


@pytest.mark.parametrize(
    "mode", [pytest.param(-1, id="negative"), pytest.param(8, id="too-large")]
)
def test_invalid_mode(mode: int) -> None:
    """The selected mode must fit its three wire bits."""
    with pytest.raises(ValueError, match="mode"):
        RC6Command(address=0, command=0, mode=mode)
