"""Tests for the Onida air-conditioner IR command."""

import pytest

from infrared_protocols.commands.onida_ac import (
    OnidaAcCommand,
    OnidaAcFanSpeed,
    OnidaAcMode,
)

# Physical-layer constants are duplicated here rather than imported
# so the tests are independent
_FRAME_A_BITS = 35
_FRAME_B_BITS = 32
_BIT_ONE_SPACE = 1687
_BIT_ZERO_SPACE = 562

_ONE_THRESHOLD = (_BIT_ONE_SPACE + _BIT_ZERO_SPACE) // 2

# Each entry is the (frame A, frame B) bitstrings, MSB index 0 = first
# transmitted bit, exactly as the remote sends them.
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
}


def _bits_to_int_lsb(bits: str, start: int, width: int) -> int:
    return sum((1 if bits[start + i] == "1" else 0) << i for i in range(width))


def _extract_frames(timings: list[int]) -> tuple[str, str]:
    """Pull the frame A and frame B bitstrings back out of raw timings."""
    frame_a = "".join(
        "1" if abs(timings[3 + 2 * i]) > _ONE_THRESHOLD else "0"
        for i in range(_FRAME_A_BITS)
    )
    frame_b_start = 2 + 2 * _FRAME_A_BITS + 1 + 1
    frame_b = "".join(
        "1" if abs(timings[frame_b_start + 1 + 2 * i]) > _ONE_THRESHOLD else "0"
        for i in range(_FRAME_B_BITS)
    )
    return frame_a, frame_b


def _frame_a_space(index: int) -> int:
    """Return the timing index of the space for frame A data bit ``index``."""
    return 3 + 2 * index


def _frame_b_space(index: int) -> int:
    """Return the timing index of the space for frame B data bit ``index``."""
    frame_b_start = 2 + 2 * _FRAME_A_BITS + 1 + 1
    return frame_b_start + 1 + 2 * index


def _command_for(label: str) -> OnidaAcCommand:
    """Build the command whose state matches a captured frame."""
    a, b = _CAPTURED[label]
    return OnidaAcCommand(
        power=a[3] == "1",
        mode=OnidaAcMode(_bits_to_int_lsb(a, 0, 3)),
        temperature=_bits_to_int_lsb(a, 8, 4) + 16,
        fan=OnidaAcFanSpeed(_bits_to_int_lsb(a, 4, 2)),
        swing_v=b[0] == "1",
        swing_h=b[4] == "1",
        turbo=a[20] == "1",
        display=a[21] == "1",
        blow=a[23] == "1",
    )


def test_encode_timing_values() -> None:
    """Pin the physical layer: leader, bit mark, and the two bit spaces."""
    timings = OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=24).get_raw_timings()

    assert timings[:2] == [9000, -4500]
    assert timings[2::2].count(562) > 0
    marks = [t for t in timings if t > 0]
    assert set(marks) == {9000, 562}
    spaces = {abs(t) for t in timings if t < 0}
    assert spaces == {4500, 1687, 562, 10000}


@pytest.mark.parametrize("label", list(_CAPTURED))
def test_encode_matches_captured_frames(label: str) -> None:
    """The encoder reproduces frames captured from a physical remote, bit for bit."""
    frame_a, frame_b = _extract_frames(_command_for(label).get_raw_timings())

    assert (frame_a, frame_b) == _CAPTURED[label]


@pytest.mark.parametrize("label", list(_CAPTURED))
def test_decode_captured_frames(label: str) -> None:
    """A captured frame decodes back to the state it was sent with."""
    expected = _command_for(label)
    result = OnidaAcCommand.from_raw_timings(expected.get_raw_timings())

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
    """Frame A carries a single swing bit; frame B distinguishes v from h."""
    v_only = _extract_frames(
        OnidaAcCommand(
            mode=OnidaAcMode.COOL, temperature=24, swing_v=True
        ).get_raw_timings()
    )
    h_only = _extract_frames(
        OnidaAcCommand(
            mode=OnidaAcMode.COOL, temperature=24, swing_h=True
        ).get_raw_timings()
    )

    assert v_only[0] == h_only[0]  # frame A identical
    assert v_only[1] != h_only[1]  # frame B differs


def test_horizontal_swing_changes_checksum_vertical_does_not() -> None:
    """Only horizontal swing enters the checksum."""
    base = _extract_frames(
        OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=24).get_raw_timings()
    )[1]
    v = _extract_frames(
        OnidaAcCommand(
            mode=OnidaAcMode.COOL, temperature=24, swing_v=True
        ).get_raw_timings()
    )[1]
    h = _extract_frames(
        OnidaAcCommand(
            mode=OnidaAcMode.COOL, temperature=24, swing_h=True
        ).get_raw_timings()
    )[1]

    assert base[28:] == v[28:]
    assert base[28:] != h[28:]


@pytest.mark.parametrize(
    ("power", "mode", "temperature", "fan", "swing_v", "swing_h", "turbo", "blow"),
    [
        pytest.param(
            True,
            OnidaAcMode.COOL,
            16,
            OnidaAcFanSpeed.AUTO,
            False,
            False,
            False,
            False,
            id="cool_min",
        ),
        pytest.param(
            True,
            OnidaAcMode.DRY,
            30,
            OnidaAcFanSpeed.HIGH,
            True,
            True,
            True,
            True,
            id="dry_max_all_on",
        ),
        pytest.param(
            False,
            OnidaAcMode.FAN_ONLY,
            23,
            OnidaAcFanSpeed.MEDIUM,
            True,
            False,
            False,
            True,
            id="off_fanonly",
        ),
        pytest.param(
            True,
            OnidaAcMode.COOL,
            21,
            OnidaAcFanSpeed.LOW,
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
    mode: OnidaAcMode,
    temperature: int,
    fan: OnidaAcFanSpeed,
    swing_v: bool,
    swing_h: bool,
    turbo: bool,
    blow: bool,
) -> None:
    """Every encodable state decodes back to the settings it was built from."""
    cmd = OnidaAcCommand(
        power=power,
        mode=mode,
        temperature=temperature,
        fan=fan,
        swing_v=swing_v,
        swing_h=swing_h,
        turbo=turbo,
        blow=blow,
    )
    result = OnidaAcCommand.from_raw_timings(cmd.get_raw_timings())

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
    cmd = OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=24)

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
        OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=temperature)


def test_decode_returns_none_for_short_timings() -> None:
    """A truncated frame is rejected."""
    timings = OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=24).get_raw_timings()

    assert OnidaAcCommand.from_raw_timings(timings[:100]) is None


@pytest.mark.parametrize(
    ("index", "value"),
    [
        pytest.param(0, 3000, id="leader_mark"),
        pytest.param(1, -1650, id="leader_space"),
    ],
)
def test_decode_returns_none_for_invalid_leader(index: int, value: int) -> None:
    """A frame with a leader outside tolerance is rejected."""
    timings = OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=24).get_raw_timings()
    timings[index] = value

    assert OnidaAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_bad_checksum() -> None:
    """A frame whose checksum does not match its state is rejected."""
    timings = OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=24).get_raw_timings()
    # Bit 28 of frame B is a one here; forcing it to a zero corrupts the checksum.
    timings[_frame_b_space(28)] = -_BIT_ZERO_SPACE

    assert OnidaAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_nec_signal() -> None:
    """A standard NEC signal (no second frame) is rejected."""
    timings = [9000, -4500]
    for _ in range(32):
        timings += [562, -1687]
    timings.append(562)

    assert OnidaAcCommand.from_raw_timings(timings) is None


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
    timings = OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=24).get_raw_timings()
    timings[space_index] = space_value

    assert OnidaAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_decoded_temperature_out_of_range() -> None:
    """A temperature field that decodes above the max is rejected."""
    timings = OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=30).get_raw_timings()
    # 30 °C encodes temp field 14 (bits 8-11); setting bit 8 makes it 15 -> 31 °C.
    timings[_frame_a_space(8)] = -_BIT_ONE_SPACE

    assert OnidaAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_bad_data_bit() -> None:
    """A data bit whose mark is out of tolerance is rejected."""
    timings = OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=24).get_raw_timings()
    timings[2] = 3000  # first frame A bit mark, far from the 562 nominal

    assert OnidaAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_bad_frame_a_end_mark() -> None:
    """A frame A whose terminating mark is out of tolerance is rejected."""
    timings = OnidaAcCommand(mode=OnidaAcMode.COOL, temperature=24).get_raw_timings()
    timings[2 + 2 * _FRAME_A_BITS] = 3000

    assert OnidaAcCommand.from_raw_timings(timings) is None
