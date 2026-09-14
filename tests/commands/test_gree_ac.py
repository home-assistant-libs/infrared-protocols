"""Tests for the Gree air-conditioner IR command."""

import pytest

from infrared_protocols.commands.gree_ac import (
    GreeAcAir,
    GreeAcCommand,
    GreeAcFanSpeed,
    GreeAcMode,
)

# Physical-layer constants are duplicated here rather than imported
# so the tests are independent
_FRAME_A_BITS = 35
_FRAME_B_BITS = 32
_LEADER_MARK = 9000
_LEADER_SPACE = 4500
_BIT_MARK = 562
_BIT_ONE_SPACE = 1687
_BIT_ZERO_SPACE = 562
_FRAME_GAP = 20100
_CHECKSUM_BASE = 10

_ONE_THRESHOLD = (_BIT_ONE_SPACE + _BIT_ZERO_SPACE) // 2

# Leader (2) + block A bit pairs + block A end mark.
_MID_GAP_INDEX = 2 + 2 * _FRAME_A_BITS + 1
_FRAME_B_START = _MID_GAP_INDEX + 1
_FRAME_B_END_MARK_INDEX = _FRAME_B_START + 2 * _FRAME_B_BITS

# Each entry is the (block A, block B) bitstrings in transmission order:
# index 0 is the first bit on the wire, exactly as the remote sends them.
_CAPTURED = {
    "cool_24_baseline": (
        "10010000000100000000010000001010010",
        "00000000000001000000000000001011",
    ),
    "cool_16_swing_both": (
        "10010010000000000000010000001010010",
        "10001000000001000000000000000110",
    ),
    "cool_30_swing_both": (
        "10010010011100000000010000001010010",
        "10001000000001000000000000000010",
    ),
    "dry_24": (
        "01011000000100000000010000001010010",
        "00000000000001000000000000000111",
    ),
    "heat_25": (
        "00110000100100000000010000001010010",
        "00000000000001000000000000001000",
    ),
    "auto_25": (
        "00010000100100000000010000001010010",
        "00000000000001000000000000001011",
    ),
    "power_off_swing_both": (
        "10000010000100000000010000001010010",
        "10001000000001000000000000000110",
    ),
    "cool_25_hswing": (
        "10010010100100000000010000001010010",
        "00001000000001000000000000001111",
    ),
    "cool_25_vswing": (
        "10010010100100000000010000001010010",
        "10000000000001000000000000000111",
    ),
    "cool_24_fan_low": (
        "10011000000100000000010000001010010",
        "00000000000001000000000000001011",
    ),
    "cool_24_fan_medium_swing_both": (
        "10010110000100000000010000001010010",
        "10001000000001000000000000000111",
    ),
    "cool_24_fan_high_swing_both": (
        "10011110000100000000010000001010010",
        "10001000000001000000000000000111",
    ),
}


def _bits_to_int_lsb(bits: str, start: int, width: int) -> int:
    return sum((1 if bits[start + i] == "1" else 0) << i for i in range(width))


def _extract_frames(timings: list[int]) -> tuple[str, str]:
    """Pull the block A and block B bitstrings back out of raw timings."""
    frame_a = "".join(
        "1" if abs(timings[3 + 2 * i]) > _ONE_THRESHOLD else "0"
        for i in range(_FRAME_A_BITS)
    )
    frame_b = "".join(
        "1" if abs(timings[_FRAME_B_START + 1 + 2 * i]) > _ONE_THRESHOLD else "0"
        for i in range(_FRAME_B_BITS)
    )
    return frame_a, frame_b


def _build_timings(frame_a: str, frame_b: str) -> list[int]:
    """Build raw timings from two bitstrings without going through the encoder."""
    timings = [_LEADER_MARK, -_LEADER_SPACE]
    for bit in frame_a:
        timings += [_BIT_MARK, -(_BIT_ONE_SPACE if bit == "1" else _BIT_ZERO_SPACE)]
    timings += [_BIT_MARK, -_FRAME_GAP]
    for bit in frame_b:
        timings += [_BIT_MARK, -(_BIT_ONE_SPACE if bit == "1" else _BIT_ZERO_SPACE)]
    timings += [_BIT_MARK, -_FRAME_GAP]
    return timings


def _frame_a_space(index: int) -> int:
    """Return the timing index of the space for block A data bit ``index``."""
    return 3 + 2 * index


def _frame_b_space(index: int) -> int:
    """Return the timing index of the space for block B data bit ``index``."""
    return _FRAME_B_START + 1 + 2 * index


def _command_for(label: str) -> GreeAcCommand:
    """Build the command whose state matches a captured frame."""
    a, b = _CAPTURED[label]
    return GreeAcCommand(
        power=a[3] == "1",
        mode=GreeAcMode(_bits_to_int_lsb(a, 0, 3)),
        temperature=_bits_to_int_lsb(a, 8, 4) + 16,
        fan=GreeAcFanSpeed(_bits_to_int_lsb(a, 4, 2)),
        swing_v=b[0] == "1",
        swing_h=b[4] == "1",
        turbo=a[20] == "1",
        display=a[21] == "1",
        blow=a[23] == "1",
    )


def test_encode_timing_values() -> None:
    """Pin the physical layer: leader, bit mark, and the two bit spaces."""
    timings = GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()

    assert timings[:2] == [9000, -4500]
    assert timings[2::2].count(562) > 0
    marks = [t for t in timings if t > 0]
    assert set(marks) == {9000, 562}
    spaces = {abs(t) for t in timings if t < 0}
    assert spaces == {4500, 1687, 562, 20100}


def _retime_to_variant(timings: list[int]) -> list[int]:
    """Re-render these timings at the other pulse lengths Gree remotes emit."""
    marks = {562: 620}
    spaces = {1687: 1600, 562: 540, 20100: 19980}
    return [
        marks.get(value, value) if value > 0 else -spaces.get(-value, -value)
        for value in timings
    ]


@pytest.mark.parametrize("label", list(_CAPTURED))
def test_decode_accepts_variant_pulse_lengths(label: str) -> None:
    """Decode a frame whose pulses sit at the far end of the bit window."""
    expected = _command_for(label)
    timings = _retime_to_variant(expected.get_raw_timings())

    result = GreeAcCommand.from_raw_timings(timings)

    assert result is not None
    assert result.mode == expected.mode
    assert result.temperature == expected.temperature
    assert result.power == expected.power
    assert result.fan == expected.fan


@pytest.mark.parametrize("label", list(_CAPTURED))
def test_encode_matches_captured_frames(label: str) -> None:
    """The encoder reproduces frames captured from a physical remote, bit for bit."""
    frame_a, frame_b = _extract_frames(_command_for(label).get_raw_timings())

    assert (frame_a, frame_b) == _CAPTURED[label]


@pytest.mark.parametrize("label", list(_CAPTURED))
def test_decode_captured_frames(label: str) -> None:
    """A captured frame decodes back to the state it was sent with."""
    expected = _command_for(label)
    result = GreeAcCommand.from_raw_timings(expected.get_raw_timings())

    assert result is not None
    assert result.power is expected.power
    assert result.mode is expected.mode
    assert result.temperature == expected.temperature
    assert result.fan is expected.fan
    assert result.swing_v is expected.swing_v
    assert result.swing_h is expected.swing_h
    assert result.turbo is expected.turbo
    assert result.display is expected.display
    assert result.blow is expected.blow


def test_swing_v_and_h_share_frame_a_bit() -> None:
    """Block A carries a single swing bit; block B distinguishes v from h."""
    v_only = _extract_frames(
        GreeAcCommand(
            mode=GreeAcMode.COOL, temperature=24, swing_v=True
        ).get_raw_timings()
    )
    h_only = _extract_frames(
        GreeAcCommand(
            mode=GreeAcMode.COOL, temperature=24, swing_h=True
        ).get_raw_timings()
    )

    assert v_only[0] == h_only[0]  # block A identical
    assert v_only[1] != h_only[1]  # block B differs


def test_horizontal_swing_changes_checksum_vertical_does_not() -> None:
    """Only horizontal swing enters the checksum."""
    base = _extract_frames(
        GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    )[1]
    v = _extract_frames(
        GreeAcCommand(
            mode=GreeAcMode.COOL, temperature=24, swing_v=True
        ).get_raw_timings()
    )[1]
    h = _extract_frames(
        GreeAcCommand(
            mode=GreeAcMode.COOL, temperature=24, swing_h=True
        ).get_raw_timings()
    )[1]

    assert base[28:] == v[28:]
    assert base[28:] != h[28:]


@pytest.mark.parametrize(
    ("power", "mode", "temperature", "fan", "swing_v", "swing_h", "turbo", "blow"),
    [
        pytest.param(
            True,
            GreeAcMode.COOL,
            16,
            GreeAcFanSpeed.AUTO,
            False,
            False,
            False,
            False,
            id="cool_min",
        ),
        pytest.param(
            True,
            GreeAcMode.DRY,
            30,
            GreeAcFanSpeed.HIGH,
            True,
            True,
            True,
            True,
            id="dry_max_all_on",
        ),
        pytest.param(
            False,
            GreeAcMode.FAN_ONLY,
            23,
            GreeAcFanSpeed.MEDIUM,
            True,
            False,
            False,
            True,
            id="off_fanonly",
        ),
        pytest.param(
            True,
            GreeAcMode.COOL,
            21,
            GreeAcFanSpeed.LOW,
            False,
            True,
            True,
            False,
            id="cool_hswing_turbo",
        ),
    ],
)
def test_roundtrip(
    power: bool,
    mode: GreeAcMode,
    temperature: int,
    fan: GreeAcFanSpeed,
    swing_v: bool,
    swing_h: bool,
    turbo: bool,
    blow: bool,
) -> None:
    """Every encodable state decodes back to the settings it was built from."""
    cmd = GreeAcCommand(
        power=power,
        mode=mode,
        temperature=temperature,
        fan=fan,
        swing_v=swing_v,
        swing_h=swing_h,
        turbo=turbo,
        blow=blow,
    )
    result = GreeAcCommand.from_raw_timings(cmd.get_raw_timings())

    assert result is not None
    assert result.power is power
    assert result.mode is mode
    assert result.temperature == temperature
    assert result.fan is fan
    assert result.swing_v is swing_v
    assert result.swing_h is swing_h
    assert result.turbo is turbo
    assert result.blow is blow


def test_default_modulation() -> None:
    """The command defaults to 38 kHz and sends a single command."""
    cmd = GreeAcCommand(mode=GreeAcMode.COOL, temperature=24)

    assert cmd.modulation == 38000
    assert cmd.repeat_count == 0


@pytest.mark.parametrize(
    "temperature",
    [
        pytest.param(15, id="below_min"),
        pytest.param(31, id="above_max"),
        pytest.param(0, id="zero"),
    ],
)
def test_temperature_out_of_range(temperature: int) -> None:
    """A temperature outside 16..30 is rejected."""
    with pytest.raises(ValueError, match="out of range"):
        GreeAcCommand(mode=GreeAcMode.COOL, temperature=temperature)


def test_decode_returns_none_for_short_timings() -> None:
    """A truncated frame is rejected."""
    timings = GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()

    assert GreeAcCommand.from_raw_timings(timings[:100]) is None


@pytest.mark.parametrize(
    ("index", "value"),
    [
        pytest.param(0, 3000, id="leader_mark"),
        pytest.param(1, -1650, id="leader_space"),
    ],
)
def test_decode_returns_none_for_invalid_leader(index: int, value: int) -> None:
    """A frame with a leader outside tolerance is rejected."""
    timings = GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    timings[index] = value

    assert GreeAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_bad_checksum() -> None:
    """A frame whose checksum does not match its state is rejected."""
    timings = GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    # Bit 28 of block B is a one here; forcing it to a zero corrupts the checksum.
    timings[_frame_b_space(28)] = -_BIT_ZERO_SPACE

    assert GreeAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_nec_signal() -> None:
    """A standard NEC signal (no second frame) is rejected."""
    timings = [9000, -4500]
    for _ in range(32):
        timings += [562, -1687]
    timings.append(562)

    assert GreeAcCommand.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    ("space_index", "space_value"),
    [
        pytest.param(_frame_a_space(28), -_BIT_ZERO_SPACE, id="trailer_bit_28_cleared"),
        pytest.param(_frame_a_space(30), -_BIT_ZERO_SPACE, id="trailer_bit_30_cleared"),
        pytest.param(_frame_a_space(33), -_BIT_ZERO_SPACE, id="trailer_bit_33_cleared"),
        pytest.param(_frame_b_space(13), -_BIT_ZERO_SPACE, id="signature_cleared"),
        pytest.param(_frame_a_space(2), -_BIT_ONE_SPACE, id="mode_field_undefined"),
    ],
)
def test_decode_returns_none_for_corrupted_bit(
    space_index: int, space_value: int
) -> None:
    """A cleared marker bit or an out-of-range mode field is rejected."""
    timings = GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    timings[space_index] = space_value

    assert GreeAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_decoded_temperature_out_of_range() -> None:
    """A temperature field that decodes above the max is rejected."""
    timings = GreeAcCommand(mode=GreeAcMode.COOL, temperature=30).get_raw_timings()
    # 30 °C encodes temp field 14 (bits 8-11); setting bit 8 makes it 15 -> 31 °C.
    timings[_frame_a_space(8)] = -_BIT_ONE_SPACE

    assert GreeAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_bad_data_bit() -> None:
    """A data bit whose mark is out of tolerance is rejected."""
    timings = GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    timings[2] = 3000  # first block A bit mark, far from the 562 nominal

    assert GreeAcCommand.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    "index",
    [
        pytest.param(2 + 2 * _FRAME_A_BITS, id="block_a"),
        pytest.param(_FRAME_B_END_MARK_INDEX, id="block_b"),
    ],
)
def test_decode_returns_none_for_bad_end_mark(index: int) -> None:
    """A block whose terminating mark is out of tolerance is rejected."""
    timings = GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    timings[index] = 3000

    assert GreeAcCommand.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    "gap",
    [
        pytest.param(-_BIT_ONE_SPACE, id="too_short"),
        pytest.param(-60000, id="too_long"),
        pytest.param(20100, id="mark_not_space"),
    ],
)
def test_decode_returns_none_for_bad_mid_frame_gap(gap: int) -> None:
    """A frame whose mid-frame gap is not the expected long space is rejected."""
    timings = GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    timings[_MID_GAP_INDEX] = gap

    assert GreeAcCommand.from_raw_timings(timings) is None


# Captured by switching one axis off while both were swinging. Block A's swing bit is
# clear while block B still carries the other axis, so these cannot be produced by the
# encoder and are decode-only.
_CAPTURED_LATCHED_SWING = {
    "v_off_from_both": (
        "10010000000100000000010000001010010",
        "00001000000001000000000000000111",
    ),
    "h_off_from_both": (
        "10010000000100000000010000001010010",
        "10000000000001000000000000001011",
    ),
}


@pytest.mark.parametrize("label", list(_CAPTURED_LATCHED_SWING))
def test_decode_latched_swing_bits_read_as_off(label: str) -> None:
    """Block B's swing bits only count while block A says something is swinging."""
    frame_a, frame_b = _CAPTURED_LATCHED_SWING[label]
    result = GreeAcCommand.from_raw_timings(_build_timings(frame_a, frame_b))

    assert result is not None
    assert result.swing_v is False
    assert result.swing_h is False


def _checksum(frame_a: str, frame_b: str) -> int:
    """Recompute the checksum nibble here rather than importing the module's."""
    total = _CHECKSUM_BASE
    total += sum(_bits_to_int_lsb(frame_a, 8 * i, 4) for i in range(4))
    total += sum(_bits_to_int_lsb(frame_b, 8 * i + 4, 4) for i in range(3))
    return total & 0xF


def _set_bits(frame: str, start: int, width: int, value: int) -> str:
    """Return the bitstring with a LSB-first field overwritten."""
    bits = list(frame)
    for i in range(width):
        bits[start + i] = "1" if (value >> i) & 1 else "0"
    return "".join(bits)


def _timings_with_block_a_field(start: int, width: int, value: int) -> list[int]:
    """Build a cool/24 frame with one block A field overwritten and a valid checksum.

    Fixing the checksum keeps these frames rejected for the field under test rather
    than for the checksum that overwriting it would otherwise break.
    """
    frame_a, frame_b = _extract_frames(
        GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    )
    frame_a = _set_bits(frame_a, start, width, value)
    frame_b = _set_bits(frame_b, 28, 4, _checksum(frame_a, frame_b))
    return _build_timings(frame_a, frame_b)


@pytest.mark.parametrize(
    ("sleep", "timer_hours", "anion", "air"),
    [
        pytest.param(False, None, False, GreeAcAir.OFF, id="all_off"),
        pytest.param(True, 0.5, True, GreeAcAir.LEVEL_1, id="half_hour_all_on"),
        pytest.param(False, 0, True, GreeAcAir.LEVEL_2, id="zero_hour_timer"),
        pytest.param(True, 10.5, False, GreeAcAir.OFF, id="two_digit_timer"),
        pytest.param(False, 24, True, GreeAcAir.LEVEL_1, id="max_timer"),
    ],
)
def test_roundtrip_sleep_timer_anion_and_air(
    sleep: bool, timer_hours: float | None, anion: bool, air: GreeAcAir
) -> None:
    """The fields the Onida captures leave at zero round-trip on their own bits."""
    cmd = GreeAcCommand(
        mode=GreeAcMode.COOL,
        temperature=24,
        sleep=sleep,
        timer_hours=timer_hours,
        anion=anion,
        air=air,
    )
    result = GreeAcCommand.from_raw_timings(cmd.get_raw_timings())

    assert result is not None
    assert result.sleep is sleep
    assert result.timer_hours == timer_hours
    assert result.anion is anion
    assert result.air is air


def test_timer_splits_the_hour_into_decimal_digits() -> None:
    """The hour is two decimal digits in separate fields, not a binary hour count."""
    frame_a, _ = _extract_frames(
        GreeAcCommand(
            mode=GreeAcMode.COOL, temperature=24, timer_hours=10.5
        ).get_raw_timings()
    )

    assert frame_a[12] == "1"
    assert _bits_to_int_lsb(frame_a, 13, 2) == 1
    assert frame_a[15] == "1"
    assert _bits_to_int_lsb(frame_a, 16, 4) == 0


def test_timer_off_zeroes_the_whole_field() -> None:
    """An off timer leaves bits 12-19 clear, as the remote sends them."""
    frame_a, _ = _extract_frames(
        GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    )

    assert frame_a[12:20] == "0" * 8


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            GreeAcCommand(mode=GreeAcMode.COOL, temperature=24, timer_hours=3),
            id="timer_hour_units",
        ),
        pytest.param(
            GreeAcCommand(mode=GreeAcMode.COOL, temperature=24, air=GreeAcAir.LEVEL_1),
            id="air",
        ),
    ],
)
def test_fields_inside_the_checksum_nibbles_change_it(command: GreeAcCommand) -> None:
    """The timer hour units and air sit in nibbles the checksum sums."""
    base = _extract_frames(
        GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    )[1]

    assert _extract_frames(command.get_raw_timings())[1][28:] != base[28:]


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            GreeAcCommand(mode=GreeAcMode.COOL, temperature=24, sleep=True),
            id="sleep",
        ),
        pytest.param(
            GreeAcCommand(mode=GreeAcMode.COOL, temperature=24, anion=True),
            id="anion",
        ),
        pytest.param(
            GreeAcCommand(mode=GreeAcMode.COOL, temperature=24, timer_hours=10),
            id="timer_half_tens_and_enabled",
        ),
    ],
)
def test_fields_outside_the_checksum_nibbles_leave_it_alone(
    command: GreeAcCommand,
) -> None:
    """Sleep, anion and the timer bits above the hour units stay out of the sum."""
    base = _extract_frames(
        GreeAcCommand(mode=GreeAcMode.COOL, temperature=24).get_raw_timings()
    )[1]

    assert _extract_frames(command.get_raw_timings())[1][28:] == base[28:]


@pytest.mark.parametrize(
    ("start", "width", "value", "air", "timer_hours"),
    [
        pytest.param(24, 2, 0b10, GreeAcAir.LEVEL_2, None, id="air_level_2"),
        pytest.param(12, 8, 0b0010_1_00_1, GreeAcAir.OFF, 2.5, id="timer_2_5_hours"),
    ],
)
def test_overwritten_block_a_field_decodes_when_the_value_is_defined(
    start: int, width: int, value: int, air: GreeAcAir, timer_hours: float | None
) -> None:
    """Pin that the rejection cases below fail on the field, not on the checksum."""
    result = GreeAcCommand.from_raw_timings(
        _timings_with_block_a_field(start, width, value)
    )

    assert result is not None
    assert result.air is air
    assert result.timer_hours == timer_hours


@pytest.mark.parametrize(
    ("start", "width", "value"),
    [
        pytest.param(24, 2, 0b11, id="air_undefined_value"),
        pytest.param(12, 8, 0b0000_0_00_1, id="timer_half_set_while_off"),
        pytest.param(12, 8, 0b0001_0_00_0, id="timer_units_set_while_off"),
        pytest.param(12, 8, 0b0000_0_01_0, id="timer_tens_set_while_off"),
        pytest.param(12, 8, 0b1010_1_00_0, id="timer_units_digit_above_nine"),
        pytest.param(12, 8, 0b0000_1_11_0, id="timer_hours_above_max"),
    ],
)
def test_decode_returns_none_for_undefined_field_value(
    start: int, width: int, value: int
) -> None:
    """A field carrying a value no remote produces is rejected, checksum aside."""
    assert (
        GreeAcCommand.from_raw_timings(_timings_with_block_a_field(start, width, value))
        is None
    )


@pytest.mark.parametrize(
    ("timer_hours", "match"),
    [
        pytest.param(-0.5, "out of range", id="negative"),
        pytest.param(24.5, "out of range", id="above_max"),
        pytest.param(1.25, "not a multiple", id="quarter_hour"),
    ],
)
def test_timer_hours_out_of_range(timer_hours: float, match: str) -> None:
    """A timer the remote cannot set is rejected at construction."""
    with pytest.raises(ValueError, match=match):
        GreeAcCommand(mode=GreeAcMode.COOL, temperature=24, timer_hours=timer_hours)
