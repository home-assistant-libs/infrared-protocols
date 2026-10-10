"""Tests for the Symphony IR command encoder and decoder."""

import itertools

import pytest

from infrared_protocols.commands.symphony import (
    FOOTER_GAP_US,
    FRAME_PERIOD_US,
    SymphonyCommand,
    SymphonyKey,
)

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


# The fields and frame count each Dreo capture decodes to. The remote uses
# frame head 110 and custom code 11.
DREO_DECODED = [
    pytest.param(DREO_POWER, 0x01, 7, id="power"),
    pytest.param(DREO_SPEED_UP, 0x02, 5, id="speed_up"),
    pytest.param(DREO_SPEED_DOWN, 0x12, 1, id="speed_down"),
    pytest.param(DREO_OSCILLATE_VERTICAL, 0x20, 5, id="oscillate_vertical"),
    pytest.param(DREO_TIMER, 0x08, 7, id="timer"),
    pytest.param(DREO_MODE, 0x04, 9, id="mode"),
]


# IRremoteESP8266 issue 1105: an SM5021 remote sent four 0xC20 frames and
# then four 0x00 control word frames after the key was released.
_C20_FRAME = SymphonyCommand(
    custom_code=0, control_word=0x20, repeat_count=0
).get_raw_timings()
_C00_FRAME = SymphonyCommand(
    custom_code=0, control_word=0x20, start_frames=True
).get_raw_timings()[:24]
RELEASE_CAPTURE = [_C20_FRAME] * 4 + [_C00_FRAME] * 4
RELEASE_WINDOWS_DECODED = [
    pytest.param(start, end, min(end, 4) - start - 1, id=f"frames_{start}_to_{end}")
    for start in range(8)
    for end in range(start + 1, 9)
    if min(end, 4) - start >= 2
]
RELEASE_WINDOWS_REFUSED = [
    pytest.param(start, end, id=f"frames_{start}_to_{end}")
    for start in range(8)
    for end in range(start + 1, 9)
    if min(end, 4) - start < 2
]

# Fifteen bits of Symphony-shaped pulses, as some other fan remotes send.
FIFTEEN_BIT_FRAME = [
    1260, -460, 460, -1260, 1260, -460, 460, -1260, 460, -1260,
    1260, -460, 1260, -460, 460, -1260, 1260, -460, 460, -1260,
    1260, -460, 460, -1260, 460, -1260, 460, -1260, 460, -1260 - 6880,
]  # fmt: skip


def _skew_pulses(timings: list[int], delta_us: int) -> list[int]:
    """Lengthen every mark by delta_us and shorten every space to match.

    IR receivers report marks longer or shorter than they were sent and
    the following space shifts the other way, so the bit period holds.
    """
    return [value + delta_us for value in timings]


def _stretch_pulses(timings: list[int], percent: int) -> list[int]:
    """Scale every mark and space, as a transmitter clock running off would."""
    return [round(value * percent / 100) for value in timings]


def _fields(command: SymphonyCommand) -> tuple[int, int, int, bool, int]:
    """Return everything a decode reports, for one comparison per test."""
    return (
        command.frame_head,
        command.custom_code,
        command.control_word,
        command.start_frames,
        command.repeat_count,
    )


# One 0xC01 frame: frame head 110, custom code 00 and control word K1, so it
# opens with two long marks and closes on a long mark whose short space
# carries the footer gap.
C01_FRAME = [
    1265, -420, 1265, -420, 420, -1265, 420, -1265, 420, -1265,
    420, -1265, 420, -1265, 420, -1265, 420, -1265, 420, -1265,
    420, -1265, 1265, -420 - 6740,
]  # fmt: skip


def test_symphony_command_get_raw_timings() -> None:
    """Test Symphony timings for one frame, most significant bit first."""
    command = SymphonyCommand(
        custom_code=0b00, control_word=SymphonyKey.K1, repeat_count=0
    )
    assert command.get_raw_timings() == C01_FRAME
    assert sum(abs(value) for value in C01_FRAME) == FRAME_PERIOD_US
    assert command.modulation == 38000


def test_symphony_command_default_send_is_three_frames() -> None:
    """A default send is three frames, the fewest any captured remote sends."""
    command = SymphonyCommand(custom_code=0b00, control_word=SymphonyKey.K1)
    assert command.get_raw_timings() == C01_FRAME * 3


def test_symphony_command_default_send_decodes() -> None:
    """A default send carries the two agreeing frames the decoder needs."""
    command = SymphonyCommand(custom_code=0b11, control_word=SymphonyKey.K5)
    decoded = SymphonyCommand.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert _fields(decoded) == _fields(command)


def test_symphony_command_repeat_count_retransmits_the_frame() -> None:
    """Each repeat is the same frame again, closed by the footer gap."""
    single = SymphonyCommand(
        custom_code=0, control_word=0x01, repeat_count=0
    ).get_raw_timings()
    repeated = SymphonyCommand(
        custom_code=0, control_word=0x01, repeat_count=4
    ).get_raw_timings()
    assert repeated == single * 5
    assert repeated.count(-(420 + FOOTER_GAP_US)) == 5


def test_symphony_command_start_frames() -> None:
    """Start frames are control words 0x00 then 0x7F ahead of the button.

    They keep the frame head and custom code of the button frames, so with
    custom code 00 they read 0xC00 and 0xC7F.
    """
    expected_start_frames = [
        1265, -420, 1265, -420, 420, -1265, 420, -1265, 420, -1265,
        420, -1265, 420, -1265, 420, -1265, 420, -1265, 420, -1265,
        420, -1265, 420, -1265 - 6740,
        1265, -420, 1265, -420, 420, -1265, 420, -1265, 420, -1265,
        1265, -420, 1265, -420, 1265, -420, 1265, -420, 1265, -420,
        1265, -420, 1265, -420 - 6740,
    ]  # fmt: skip
    button = SymphonyCommand(custom_code=0, control_word=0x20, repeat_count=2)
    with_start = SymphonyCommand(
        custom_code=0, control_word=0x20, start_frames=True, repeat_count=2
    )
    timings = with_start.get_raw_timings()
    assert timings[:48] == expected_start_frames
    assert timings[48:] == button.get_raw_timings()


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(SymphonyCommand(custom_code=0, control_word=0x20), id="zero"),
        pytest.param(SymphonyCommand(custom_code=0, control_word=0x01), id="one"),
        pytest.param(
            SymphonyCommand(custom_code=3, control_word=0x01, repeat_count=4),
            id="repeated",
        ),
        pytest.param(
            SymphonyCommand(custom_code=0, control_word=0x20, start_frames=True),
            id="start_frames_last_bit_zero",
        ),
        pytest.param(
            SymphonyCommand(
                custom_code=0, control_word=0x01, start_frames=True, repeat_count=2
            ),
            id="start_frames_last_bit_one",
        ),
    ],
)
def test_symphony_command_timings_alternate(command: SymphonyCommand) -> None:
    """Timings open on a mark, close on a space and never repeat a sign.

    Emitters that take absolute durations, such as Broadlink, assume strict
    mark and space alternation, so a second space in a row would play as a
    mark and swap every pulse after it.
    """
    timings = command.get_raw_timings()
    assert timings[0] > 0
    assert timings[-1] < 0
    assert all((a > 0) != (b > 0) for a, b in itertools.pairwise(timings))


@pytest.mark.parametrize(
    ("frame_head", "custom_code", "control_word"),
    [
        pytest.param(0b110, 0b00, SymphonyKey.K1, id="xin_hui"),
        pytest.param(0b110, 0b11, SymphonyKey.K8, id="sm5021"),
        pytest.param(0b010, 0b11, SymphonyKey.K3, id="head_010"),
        pytest.param(0b000, 0b00, 0x01, id="lowest"),
        pytest.param(0b111, 0b11, 0x7E, id="highest"),
    ],
)
def test_symphony_command_round_trips(
    frame_head: int, custom_code: int, control_word: int
) -> None:
    """The three fields decode back to the values that produced them."""
    command = SymphonyCommand(
        frame_head=frame_head,
        custom_code=custom_code,
        control_word=control_word,
        repeat_count=3,
    )
    decoded = SymphonyCommand.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert _fields(decoded) == (frame_head, custom_code, control_word, False, 3)


@pytest.mark.parametrize(
    ("code", "frame_head", "custom_code", "control_word"),
    [
        pytest.param(0xC01, 0b110, 0b00, 0x01, id="xin_hui"),
        pytest.param(0xD81, 0b110, 0b11, 0x01, id="sm5021"),
        pytest.param(0x5C6, 0b010, 0b11, 0x46, id="head_010"),
        # Remotes outside the SM5021 layout still carry one 12-bit value.
        pytest.param(0x1DA, 0b000, 0b11, 0x5A, id="non_sm5021_layout"),
    ],
)
def test_symphony_command_from_code(
    code: int, frame_head: int, custom_code: int, control_word: int
) -> None:
    """from_code() splits the 12-bit value and code joins it again."""
    command = SymphonyCommand.from_code(code)
    assert (command.frame_head, command.custom_code, command.control_word) == (
        frame_head,
        custom_code,
        control_word,
    )
    assert command.code == code


@pytest.mark.parametrize(
    ("frame_head", "custom_code", "control_word", "message"),
    [
        pytest.param(-1, 0, 0x01, "frame_head", id="frame_head_negative"),
        pytest.param(8, 0, 0x01, "frame_head", id="frame_head_too_wide"),
        pytest.param(6, -1, 0x01, "custom_code", id="custom_code_negative"),
        pytest.param(6, 4, 0x01, "custom_code", id="custom_code_too_wide"),
        pytest.param(6, 0, -1, "control_word", id="control_word_negative"),
        pytest.param(6, 0, 0x80, "control_word", id="control_word_too_wide"),
        pytest.param(6, 0, 0x00, "reserved", id="control_word_0x00"),
        pytest.param(6, 0, 0x7F, "reserved", id="control_word_0x7f"),
    ],
)
def test_symphony_command_rejects_out_of_range(
    frame_head: int, custom_code: int, control_word: int, message: str
) -> None:
    """Each field must fit its width, and reserved control words are refused."""
    with pytest.raises(ValueError, match=message):
        SymphonyCommand(
            frame_head=frame_head, custom_code=custom_code, control_word=control_word
        )


@pytest.mark.parametrize(
    ("code", "message"),
    [
        pytest.param(-1, "code", id="negative"),
        pytest.param(0x1000, "code", id="too_wide"),
        pytest.param(0xC00, "reserved", id="start_frame_0x00"),
        pytest.param(0xC7F, "reserved", id="start_frame_0x7f"),
    ],
)
def test_symphony_command_from_code_rejects(code: int, message: str) -> None:
    """from_code() refuses values outside 12 bits and reserved control words."""
    with pytest.raises(ValueError, match=message):
        SymphonyCommand.from_code(code)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        pytest.param(SymphonyKey.K1, 0b0000001, id="K1"),
        pytest.param(SymphonyKey.K2, 0b0000010, id="K2"),
        pytest.param(SymphonyKey.K3, 0b0000100, id="K3"),
        pytest.param(SymphonyKey.K4, 0b0001000, id="K4"),
        pytest.param(SymphonyKey.K5, 0b0010000, id="K5"),
        pytest.param(SymphonyKey.K6, 0b0100000, id="K6"),
        pytest.param(SymphonyKey.K7, 0b1000011, id="K7"),
        pytest.param(SymphonyKey.K8, 0b1000110, id="K8"),
    ],
)
def test_symphony_key_matches_the_datasheet(key: SymphonyKey, value: int) -> None:
    """Key codes equal the SM5021 datasheet control words."""
    assert key == value


def test_symphony_command_rejects_a_single_frame() -> None:
    """One frame is not enough evidence when the protocol has no checksum."""
    encoded = SymphonyCommand(
        custom_code=0, control_word=0x01, repeat_count=0
    ).get_raw_timings()
    assert SymphonyCommand.from_raw_timings(encoded) is None


def test_symphony_command_discards_start_frames() -> None:
    """XIN HUI start frames are left out of the vote and never reported."""
    command = SymphonyCommand(
        custom_code=0, control_word=0x20, start_frames=True, repeat_count=4
    )
    decoded = SymphonyCommand.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert _fields(decoded) == (0b110, 0b00, 0x20, False, 4)


def test_symphony_command_refuses_a_tie() -> None:
    """A tie between two readings is refused rather than broken by order."""
    capture = (
        SymphonyCommand(
            custom_code=0, control_word=0x01, repeat_count=1
        ).get_raw_timings()
        + SymphonyCommand(
            custom_code=0, control_word=0x02, repeat_count=1
        ).get_raw_timings()
    )
    assert SymphonyCommand.from_raw_timings(capture) is None


@pytest.mark.parametrize(("start", "end", "repeat_count"), RELEASE_WINDOWS_DECODED)
def test_symphony_command_release_frames_never_win(
    start: int, end: int, repeat_count: int
) -> None:
    """Release frames after the button frames never become the result.

    Before reserved control words were left out of the vote, a capture
    window holding more release frames than button frames read as 0xC00.
    """
    capture = [value for frame in RELEASE_CAPTURE[start:end] for value in frame]
    decoded = SymphonyCommand.from_raw_timings(capture)
    assert decoded is not None
    assert (decoded.code, decoded.repeat_count) == (0xC20, repeat_count)


@pytest.mark.parametrize(("start", "end"), RELEASE_WINDOWS_REFUSED)
def test_symphony_command_release_frames_alone_are_refused(
    start: int, end: int
) -> None:
    """A window with fewer than two button frames is refused, not read as 0xC00."""
    capture = [value for frame in RELEASE_CAPTURE[start:end] for value in frame]
    assert SymphonyCommand.from_raw_timings(capture) is None


def test_symphony_command_refuses_other_frame_lengths() -> None:
    """Symphony-shaped pulses in a frame of another length are not Symphony."""
    assert SymphonyCommand.from_raw_timings(FIFTEEN_BIT_FRAME * 3) is None


@pytest.mark.parametrize(
    "percent",
    [pytest.param(80, id="too_short"), pytest.param(125, id="too_long")],
)
def test_symphony_command_refuses_a_foreign_bit_period(percent: int) -> None:
    """Twelve well-formed bits are still refused when the bit period is wrong.

    The marks and spaces still read as short and long, so only the bit
    period tells this apart from Symphony.
    """
    clean = SymphonyCommand(
        custom_code=0, control_word=0x20, repeat_count=3
    ).get_raw_timings()
    assert SymphonyCommand.from_raw_timings(_stretch_pulses(clean, percent)) is None


@pytest.mark.parametrize("delta_us", [-200, -100, 100, 200])
def test_symphony_command_decodes_through_pulse_skew(delta_us: int) -> None:
    """Identity must survive a receiver that skews every mark by delta_us."""
    clean = SymphonyCommand(
        custom_code=0, control_word=0x20, repeat_count=3
    ).get_raw_timings()
    decoded = SymphonyCommand.from_raw_timings(_skew_pulses(clean, delta_us))
    assert decoded is not None
    assert decoded.code == 0xC20


@pytest.mark.parametrize("percent", [90, 95, 105, 110])
def test_symphony_command_decodes_through_clock_drift(percent: int) -> None:
    """Identity must survive a transmitter clock that runs a little off."""
    clean = SymphonyCommand(
        custom_code=0, control_word=0x20, repeat_count=3
    ).get_raw_timings()
    decoded = SymphonyCommand.from_raw_timings(_stretch_pulses(clean, percent))
    assert decoded is not None
    assert decoded.code == 0xC20


@pytest.mark.parametrize("repeat_count", [1, 7, 8, 9])
def test_symphony_command_variable_frame_counts_decode_alike(
    repeat_count: int,
) -> None:
    """Captures of one button press that caught different frame counts agree.

    A capture window opens and closes independently of the transmission, so
    the same press arrives with a different number of frames each time. Only
    repeat_count may differ.
    """
    capture = SymphonyCommand(
        custom_code=0, control_word=0x20, start_frames=True, repeat_count=repeat_count
    ).get_raw_timings()
    decoded = SymphonyCommand.from_raw_timings(capture)
    assert decoded is not None
    assert _fields(decoded) == (0b110, 0b00, 0x20, False, repeat_count)


@pytest.mark.parametrize(("capture", "control_word", "repeat_count"), DREO_DECODED)
def test_symphony_command_decodes_dreo_capture(
    capture: list[int], control_word: int, repeat_count: int
) -> None:
    """Every readable capture in the corpus decodes to its recorded fields."""
    decoded = SymphonyCommand.from_raw_timings(capture)
    assert decoded is not None
    assert _fields(decoded) == (0b110, 0b11, control_word, False, repeat_count)


@pytest.mark.parametrize(("capture", "control_word", "repeat_count"), DREO_DECODED)
def test_symphony_command_re_encodes_dreo_capture(
    capture: list[int], control_word: int, repeat_count: int
) -> None:
    """A decoded capture re-encodes to timings that decode back to itself."""
    decoded = SymphonyCommand.from_raw_timings(capture)
    assert decoded is not None
    round_tripped = SymphonyCommand.from_raw_timings(decoded.get_raw_timings())
    assert round_tripped is not None
    assert _fields(round_tripped) == (0b110, 0b11, control_word, False, repeat_count)


def test_symphony_command_refuses_a_capture_whose_frames_disagree() -> None:
    """The two-frame rule refuses a real capture rather than guessing at it.

    Four of the six frames in this Dreo capture are too distorted to read at
    all, and the two that do read disagree with each other (0xD10 and 0xD90).
    With no checksum to fall back on there is no evidence for either reading,
    so the capture is refused instead of one of them being picked.
    """
    assert SymphonyCommand.from_raw_timings(DREO_OSCILLATE_HORIZONTAL) is None
