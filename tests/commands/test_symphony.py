"""Tests for the Symphony IR command encoder and decoder."""

import pytest

from infrared_protocols.commands.symphony import FOOTER_GAP_US, SymphonyCommand

# Real captures from a Dreo DR-HAF004S fan remote, released as a CC0 corpus.
# Signed microseconds, mark positive and space negative, as the receiver
# reported them: the pulse widths carry the jitter of a real capture and the
# inter-frame gaps are the transmitter's footer gap, not a nominal value.
DREO_POWER: list[int] = [
    1288, -421, 1288, -421, 473, -1210, 1315, -421, 1341, -368, 473, -1236, 473,
    -1236, 447, -1236, 447, -1262, 473, -1210, 473, -1210, 1341, -7205, 1262, -447,
    1288, -421, 473, -1210, 1341, -394, 1315, -394, 473, -1236, 473, -1210, 447,
    -1236, 421, -1288, 473, -1236, 473, -1210, 1341, -8309, 1236, -473, 1315, -394,
    473, -1236, 1341, -368, 1315, -394, 447, -1236, 473, -1210, 500, -1210, 394,
    -1315, 473, -1236, 473, -1210, 1341, -7205, 1236, -473, 1315, -394, 473, -1236,
    1315, -394, 1315, -368, 473, -1236, 473, -1210, 447, -1236, 447, -1262, 473,
    -1236, 473, -1210, 1341, -8309, 1288, -447, 1315, -394, 473, -1210, 1341, -394,
    1315, -394, 447, -1236, 473, -1210, 473, -1236, 421, -1288, 473, -1236, 473,
    -1210, 1341, -7205, 1367, -368, 1288, -421, 500, -1183, 1315, -421, 1341, -368,
    500, -1183, 500, -1183, 447, -1262, 500, -1183, 473, -1210, 500, -1210, 1315,
    -8336, 1341, -394, 1236, -447, 447, -1262, 1262, -447, 1315, -421, 473, -1210,
    473, -1236, 473, -1236, 473, -1236, 473, -1210, 473, -1236, 1262, -7310, 1341,
    -394, 1315, -368, 421, -1288, 1341, -368, 1262, -447, 473, -1236, 473, -1236,
    473, -1210, 473, -1210, 473, -1236, 447, -1262, 1341, -66265,
]  # fmt: skip

DREO_SPEED_UP: list[int] = [
    1262, -421, 1288, -421, 447, -1236, 1288, -421, 1288, -421, 447, -1236, 473,
    -1183, 447, -1236, 447, -1236, 447, -1236, 1288, -421, 447, -7994, 1288, -421,
    1288, -421, 447, -1236, 1288, -421, 1288, -421, 447, -1236, 447, -1236, 447,
    -1236, 447, -1236, 447, -1236, 1288, -421, 447, -9177, 1288, -421, 1288, -421,
    447, -1236, 1288, -421, 1288, -421, 447, -1236, 447, -1236, 447, -1236, 447,
    -1236, 447, -1236, 1288, -421, 447, -7994, 1288, -421, 1288, -421, 447, -1236,
    1288, -421, 1288, -421, 447, -1236, 447, -1236, 447, -1236, 447, -1236, 447,
    -1236, 1288, -421, 447, -9177, 1288, -421, 1288, -421, 447, -1236, 1288, -421,
    1288, -394, 447, -1210, 447, -1236, 447, -1236, 447, -1236, 473, -1210, 1315,
    -394, 447, -7994, 1288, -394, 1288, -421, 447, -1236, 1315, -394, 1315, -394,
    421, -1236, 473, -1210, 447, -1236, 473, -1210, 447, -1236, 1288, -421, 447,
    -65503,
]  # fmt: skip

DREO_SPEED_DOWN: list[int] = [
    1210, -473, 500, -184, 289, -736, 342, -1499, 999, -605, 447, -131, 447, -657,
    263, -1341, 368, -1394, 1104, -473, 394, -1341, 316, -1315, 1210, -579, 263,
    -8099, 1210, -605, 999, -631, 237, -1367, 1210, -552, 1104, -526, 368, -1394,
    263, -1315, 1210, -500, 342, -1315, 342, -1394, 1131, -579, 263, -9204, 1210,
    -552, 999, -763, 237, -1288, 1131, -552, 1288, -526, 263, -1341, 368, -1288,
    1236, -526, 263, -1341, 394, -1288, 1210, -500, 368, -8047, 1210, -500, 1210,
    -473, 368, -1288, 1157, -657, 1078, -631, 263, -1288, 394, -1288, 1236, -473,
    289, -1341, 394, -1341, 552, -500, 131, -500, 263, -65503,
]  # fmt: skip

DREO_OSCILLATE_HORIZONTAL: list[int] = [
    1210, -473, 1183, -2209, 1157, -631, 1104, -500, 316, -1446, 316, -1262, 1210,
    -500, 368, -1341, 342, -1288, 394, -1341, 316, -8099, 1078, -657, 789, -841,
    368, -1341, 1210, -763, 789, -657, 289, -1288, 394, -1315, 868, -789, 368,
    -1341, 316, -1367, 368, -1341, 368, -9098, 1183, -526, 1210, -579, 263, -1315,
    1210, -500, 473, -289, 421, -2156, 368, -1315, 1236, -500, 263, -1499, 237,
    -1315, 394, -1288, 368, -8073, 815, -894, 1236, -579, 158, -1394, 1183, -473,
    1210, -605, 158, -1394, 368, -1315, 1236, -526, 316, -1341, 289, -1394, 342,
    -1315, 368, -9125, 1210, -473, 1210, -605, 263, -1288, 1210, -473, 631, -1236,
    184, -1367, 342, -1341, 1157, -552, 316, -1367, 316, -1341, 342, -1341, 368,
    -8047, 1236, -447, 1236, -473, 368, -1341, 1026, -631, 1131, -657, 263, -1341,
    342, -1288, 1183, -526, 342, -1315, 368, -1341, 368, -1341, 316, -65503,
]  # fmt: skip

DREO_OSCILLATE_VERTICAL: list[int] = [
    1288, -394, 1288, -421, 421, -1236, 1288, -421, 1288, -421, 447, -1210, 1315,
    -394, 447, -1236, 447, -1236, 473, -1210, 447, -1236, 447, -7994, 1288, -421,
    1288, -394, 447, -1210, 1288, -421, 1288, -421, 421, -1236, 1288, -394, 473,
    -1210, 447, -1236, 447, -1236, 473, -1210, 473, -9230, 1288, -394, 1288, -394,
    473, -1210, 1288, -421, 1288, -421, 447, -1236, 1315, -368, 447, -1236, 447,
    -1236, 473, -1210, 473, -1210, 447, -7994, 1288, -421, 1288, -421, 447, -1236,
    1288, -394, 1288, -394, 447, -1236, 1288, -421, 447, -1210, 473, -1210, 447,
    -1236, 447, -1236, 447, -9256, 1288, -421, 1288, -421, 447, -1236, 1288, -421,
    1288, -394, 447, -1236, 1288, -394, 473, -1210, 447, -1236, 447, -1210, 447,
    -1236, 447, -7994, 1288, -394, 1315, -368, 447, -1236, 1288, -394, 1288, -394,
    447, -1236, 1288, -421, 447, -1236, 447, -1236, 447, -1236, 447, -1236, 447,
    -65503,
]  # fmt: skip

DREO_TIMER: list[int] = [
    1262, -421, 1288, -421, 421, -1262, 1288, -394, 1288, -421, 421, -1262, 421,
    -1236, 447, -1236, 1315, -394, 421, -1262, 447, -1236, 447, -7994, 1262, -421,
    1288, -421, 421, -1262, 1262, -421, 1288, -421, 421, -1262, 447, -1236, 421,
    -1262, 1288, -421, 421, -1262, 421, -1262, 447, -9335, 1262, -421, 1288, -394,
    447, -1262, 1262, -421, 1288, -421, 421, -1262, 447, -1236, 447, -1236, 1288,
    -421, 421, -1262, 447, -1236, 447, -7994, 1262, -421, 1315, -368, 473, -1236,
    1262, -421, 1288, -421, 421, -1262, 447, -1236, 447, -1236, 1262, -421, 421,
    -1262, 447, -1236, 447, -9309, 1262, -421, 1288, -394, 421, -1262, 1288, -394,
    1288, -421, 447, -1236, 447, -1236, 447, -1236, 1288, -394, 447, -1236, 447,
    -1236, 447, -7994, 1262, -421, 1288, -421, 447, -1236, 1262, -421, 1288, -421,
    421, -1262, 421, -1262, 447, -1236, 1288, -394, 447, -1236, 421, -1262, 421,
    -9335, 1262, -421, 1262, -421, 421, -1262, 1288, -394, 1288, -394, 421, -1262,
    447, -1236, 447, -1236, 1288, -394, 447, -1236, 447, -1236, 447, -7994, 1262,
    -421, 1288, -394, 421, -1262, 1288, -394, 1288, -394, 447, -1236, 447, -1236,
    447, -1236, 1288, -421, 447, -1236, 447, -1236, 447, -65503,
]  # fmt: skip

DREO_MODE: list[int] = [
    1262, -421, 1262, -421, 421, -1262, 1262, -421, 1262, -421, 421, -1262, 447,
    -1236, 421, -1262, 447, -1236, 1262, -421, 421, -1262, 421, -8020, 1262, -421,
    1288, -421, 421, -1262, 1262, -421, 1288, -394, 421, -1262, 421, -1262, 421,
    -1262, 447, -1236, 1262, -421, 421, -1262, 421, -9098, 1262, -421, 1262, -421,
    421, -1262, 1262, -421, 1262, -421, 421, -1262, 421, -1262, 421, -1262, 447,
    -1236, 1288, -394, 421, -1262, 421, -8020, 1262, -421, 1262, -421, 421, -1262,
    1262, -421, 1262, -421, 421, -1262, 447, -1236, 421, -1262, 421, -1236, 1262,
    -421, 421, -1262, 447, -9072, 1262, -421, 1262, -421, 421, -1262, 1262, -421,
    1288, -394, 421, -1262, 421, -1262, 421, -1262, 421, -1262, 1262, -421, 447,
    -1236, 421, -8020, 1262, -421, 1262, -421, 421, -1262, 1262, -421, 1262, -421,
    421, -1262, 447, -1236, 421, -1262, 421, -1262, 1262, -421, 421, -1262, 421,
    -9072, 1262, -421, 1262, -421, 447, -1236, 1262, -421, 1262, -421, 421, -1262,
    421, -1262, 447, -1236, 421, -1262, 1262, -421, 447, -1236, 447, -7994, 1262,
    -421, 1288, -394, 421, -1262, 1288, -394, 1262, -421, 421, -1262, 421, -1262,
    447, -1236, 421, -1262, 1288, -394, 421, -1262, 421, -9072, 1288, -421, 1236,
    -421, 447, -1262, 1236, -447, 1262, -421, 394, -1262, 447, -1262, 421, -1236,
    447, -1236, 1262, -447, 421, -1236, 421, -8020, 1288, -421, 1262, -421, 394,
    -1288, 1236, -447, 1262, -421, 421, -1262, 394, -1288, 394, -1288, 394, -1288,
    1262, -421, 421, -1262, 421, -65503,
]  # fmt: skip

# The value, bit count and frame count each Dreo capture decodes to.
DREO_DECODED = [
    pytest.param(DREO_POWER, 0xD81, 7, id="power"),
    pytest.param(DREO_SPEED_UP, 0xD82, 5, id="speed_up"),
    pytest.param(DREO_SPEED_DOWN, 0xD92, 1, id="speed_down"),
    pytest.param(DREO_OSCILLATE_VERTICAL, 0xDA0, 5, id="oscillate_vertical"),
    pytest.param(DREO_TIMER, 0xD88, 7, id="timer"),
    pytest.param(DREO_MODE, 0xD84, 9, id="mode"),
]


def _scale_pulses(timings: list[int], delta_us: int) -> list[int]:
    """Grow or shrink every pulse in a capture by delta_us.

    Receivers report marks and spaces a little longer or shorter than they
    were transmitted. The decoded identity must not move with them.
    """
    scaled: list[int] = []
    for value in timings:
        if value > 0:
            scaled.append(value + delta_us)
        else:
            scaled.append(min(-1, value - delta_us))
    return scaled


def test_symphony_command_get_raw_timings() -> None:
    """Test Symphony timings for a 12-bit frame, most significant bit first.

    0xC00 is two set bits followed by ten clear ones, so the frame opens
    with two long marks and closes with ten short ones.
    """
    expected_raw_timings = [
        1260, -460, 1260, -460, 460, -1260, 460, -1260, 460, -1260,
        460, -1260, 460, -1260, 460, -1260, 460, -1260, 460, -1260,
        460, -1260, 460, -1260, -6880,
    ]  # fmt: skip
    command = SymphonyCommand(data=0xC00, nbits=12)
    assert command.get_raw_timings() == expected_raw_timings
    assert command.modulation == 38000


def test_symphony_command_repeat_count_retransmits_the_frame() -> None:
    """Each repeat is the same frame again, closed by the footer gap."""
    single = SymphonyCommand(data=0xC00, nbits=12).get_raw_timings()
    repeated = SymphonyCommand(data=0xC00, nbits=12, repeat_count=2).get_raw_timings()
    assert repeated == single * 3
    assert repeated.count(-FOOTER_GAP_US) == 3


@pytest.mark.parametrize(
    ("data", "nbits"),
    [
        pytest.param(0x00, 8, id="8_bit_min"),
        pytest.param(0xFF, 8, id="8_bit_max"),
        pytest.param(0xC00, 12, id="12_bit"),
        pytest.param(0xFFF, 12, id="12_bit_max"),
        pytest.param(0x0000, 16, id="16_bit_min"),
        pytest.param(0xBEEF, 16, id="16_bit"),
    ],
)
def test_symphony_command_round_trips(data: int, nbits: int) -> None:
    """Every frame width must decode back to the value that produced it."""
    encoded = SymphonyCommand(data=data, nbits=nbits, repeat_count=3).get_raw_timings()
    decoded = SymphonyCommand.from_raw_timings(encoded)
    assert decoded is not None
    assert (decoded.data, decoded.nbits, decoded.repeat_count) == (data, nbits, 3)


def test_symphony_command_rejects_a_single_frame() -> None:
    """One frame is not enough evidence when the protocol has no checksum."""
    encoded = SymphonyCommand(data=0xC00, nbits=12).get_raw_timings()
    assert SymphonyCommand.from_raw_timings(encoded) is None


def test_symphony_command_discards_vendor_preamble_frames() -> None:
    """An all-zeros and an all-ones frame ahead of the button code lose the vote.

    This is the capture shape reported by mvdwetering on a public issue for
    a Silvercrest fan remote, which is what motivated the majority vote.
    """
    capture = (
        SymphonyCommand(data=0x000, nbits=12).get_raw_timings()
        + SymphonyCommand(data=0xFFF, nbits=12).get_raw_timings()
        + SymphonyCommand(data=0xC00, nbits=12, repeat_count=4).get_raw_timings()
    )
    decoded = SymphonyCommand.from_raw_timings(capture)
    assert decoded is not None
    assert (decoded.data, decoded.nbits, decoded.repeat_count) == (0xC00, 12, 4)


@pytest.mark.parametrize("delta_us", [-100, -50, 50, 100, 200])
def test_symphony_command_decodes_through_pulse_drift(delta_us: int) -> None:
    """Identity must survive a receiver that reports every pulse off by delta_us."""
    clean = SymphonyCommand(data=0xC00, nbits=12, repeat_count=3).get_raw_timings()
    decoded = SymphonyCommand.from_raw_timings(_scale_pulses(clean, delta_us))
    assert decoded is not None
    assert (decoded.data, decoded.nbits) == (0xC00, 12)


def test_symphony_command_variable_frame_counts_decode_alike() -> None:
    """Captures of one button press that caught different frame counts agree.

    A capture window opens and closes independently of the transmission, so
    the same press arrives with a different number of frames each time. Only
    repeat_count may differ.
    """
    identities = set()
    for repeats in (7, 8, 9):
        capture = (
            SymphonyCommand(data=0x000, nbits=12).get_raw_timings()
            + SymphonyCommand(data=0xFFF, nbits=12).get_raw_timings()
            + SymphonyCommand(
                data=0xC00, nbits=12, repeat_count=repeats
            ).get_raw_timings()
        )
        decoded = SymphonyCommand.from_raw_timings(capture)
        assert decoded is not None
        identities.add((decoded.data, decoded.nbits))
    assert identities == {(0xC00, 12)}


@pytest.mark.parametrize(
    ("data", "nbits"),
    [
        pytest.param(0x00, 10, id="unsupported_frame_width"),
        pytest.param(0x00, 0, id="zero_frame_width"),
        pytest.param(-1, 12, id="negative_data"),
        pytest.param(0x1000, 12, id="data_too_wide"),
        pytest.param(0x100, 8, id="data_too_wide_for_8_bit"),
    ],
)
def test_symphony_command_rejects_out_of_range(data: int, nbits: int) -> None:
    """Frames are 8, 12 or 16 bits and the value has to fit inside them."""
    with pytest.raises(ValueError):
        SymphonyCommand(data=data, nbits=nbits)


@pytest.mark.parametrize(("capture", "data", "repeat_count"), DREO_DECODED)
def test_symphony_command_decodes_dreo_capture(
    capture: list[int], data: int, repeat_count: int
) -> None:
    """Every readable capture in the corpus decodes to its recorded identity."""
    decoded = SymphonyCommand.from_raw_timings(capture)
    assert decoded is not None
    assert (decoded.data, decoded.nbits, decoded.repeat_count) == (
        data,
        12,
        repeat_count,
    )


@pytest.mark.parametrize(("capture", "data", "repeat_count"), DREO_DECODED)
def test_symphony_command_re_encodes_dreo_capture(
    capture: list[int], data: int, repeat_count: int
) -> None:
    """A decoded capture re-encodes to timings that decode back to itself."""
    decoded = SymphonyCommand.from_raw_timings(capture)
    assert decoded is not None
    round_tripped = SymphonyCommand.from_raw_timings(decoded.get_raw_timings())
    assert round_tripped is not None
    assert (round_tripped.data, round_tripped.nbits) == (data, 12)
    assert round_tripped.repeat_count == repeat_count


def test_symphony_command_refuses_a_capture_whose_frames_disagree() -> None:
    """The two-frame rule refuses a real capture rather than guessing at it.

    Four of the six frames in this Dreo capture are too distorted to read at
    all, and the two that do read disagree with each other. With no checksum
    to fall back on there is no evidence for either reading, so the capture
    is refused instead of one of them being picked.
    """
    assert SymphonyCommand.from_raw_timings(DREO_OSCILLATE_HORIZONTAL) is None
