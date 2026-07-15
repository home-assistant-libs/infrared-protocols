"""Tests for the LG air-conditioner IR command."""

import pytest

from infrared_protocols.commands.lg_ac import (
    LgAcCommand,
    LgAcFanSpeed,
    LgAcMode,
)

# Physical-layer constants are duplicated here rather than imported
# so the tests are independent
_BITS = 28
_BIT_MARK = 550
_BIT_ONE_SPACE = 1600
_BIT_ZERO_SPACE = 550

_HDR = (3200, 9900)
_ALT_HDR = (8500, 4250)

# Power-on frames: settings bit clear. The encoder emits these.
_COOL_26_MEDIUM = 0x8800B2D
_COOL_24_MEDIUM_LOW = 0x8800992
_COOL_24_MEDIUM_HIGH = 0x88009A3
_OFF = 0x88C0051

# Settings frames: settings bit set. Decode-only.
_SET_COOL_24_AUTO = 0x8808956
_SET_COOL_16_MEDIUM_HIGH = 0x88081A3
_SET_COOL_30_MEDIUM_HIGH = 0x8808FA1
_SET_DRY_24_LOW = 0x8809902
_SET_FAN_ONLY_24_HIGH = 0x880A947


_ONE_THRESHOLD = (_BIT_ONE_SPACE + _BIT_ZERO_SPACE) // 2


def _extract_frame(timings: list[int]) -> int:
    """Extract the frame integer from raw timings, one bit per mark/space pair."""
    frame = 0
    for i in range(2, 2 + 2 * _BITS, 2):
        frame = (frame << 1) | (1 if abs(timings[i + 1]) > _ONE_THRESHOLD else 0)
    return frame


def _build_timings(frame: int, header: tuple[int, int] = _HDR) -> list[int]:
    """Build raw timings for a frame without going through the encoder."""
    timings = [header[0], -header[1]]
    for i in reversed(range(_BITS)):
        one = (frame >> i) & 1
        timings += [_BIT_MARK, -(_BIT_ONE_SPACE if one else _BIT_ZERO_SPACE)]
    timings.append(_BIT_MARK)
    return timings


def test_encode_timing_values() -> None:
    """Pin the physical layer: LG2 header, bit mark, and the two bit spaces."""
    timings = LgAcCommand(mode=LgAcMode.COOL, temperature=24).get_raw_timings()

    assert timings[:2] == [3200, -9900]
    assert len(timings) == 2 + 2 * 28 + 1
    assert all(mark == 550 for mark in timings[2::2])
    assert {abs(space) for space in timings[3::2]} == {550, 1600}


@pytest.mark.parametrize(
    ("mode", "temperature", "fan", "expected_frame"),
    [
        pytest.param(
            LgAcMode.COOL,
            26,
            LgAcFanSpeed.MEDIUM,
            _COOL_26_MEDIUM,
            id="cool_26_medium",
        ),
        pytest.param(
            LgAcMode.COOL,
            24,
            LgAcFanSpeed.MEDIUM_LOW,
            _COOL_24_MEDIUM_LOW,
            id="cool_24_medium_low",
        ),
        pytest.param(
            LgAcMode.COOL,
            24,
            LgAcFanSpeed.MEDIUM_HIGH,
            _COOL_24_MEDIUM_HIGH,
            id="cool_24_medium_high",
        ),
        pytest.param(LgAcMode.OFF, None, LgAcFanSpeed.AUTO, _OFF, id="off"),
    ],
)
def test_encode_matches_captured_frame(
    mode: LgAcMode,
    temperature: int | None,
    fan: LgAcFanSpeed,
    expected_frame: int,
) -> None:
    """Encoder output must equal the frame the remote sends."""
    cmd = LgAcCommand(mode=mode, temperature=temperature, fan=fan)
    assert _extract_frame(cmd.get_raw_timings()) == expected_frame


@pytest.mark.parametrize(
    "fan",
    [
        pytest.param(LgAcFanSpeed.LOW, id="low"),
        pytest.param(LgAcFanSpeed.HIGH, id="high"),
        pytest.param(LgAcFanSpeed.MEDIUM_HIGH, id="medium_high"),
    ],
)
def test_encode_off_ignores_fan(fan: LgAcFanSpeed) -> None:
    """Power-off is a fixed frame; the fan argument must not reach it."""
    cmd = LgAcCommand(mode=LgAcMode.OFF, fan=fan)
    assert _extract_frame(cmd.get_raw_timings()) == _OFF


def test_encode_dry_pins_temperature() -> None:
    """Dry encodes 24 °C whatever the caller asks for."""
    dry = LgAcCommand(mode=LgAcMode.DRY, temperature=20, fan=LgAcFanSpeed.LOW)
    cool_24 = LgAcCommand(mode=LgAcMode.COOL, temperature=24, fan=LgAcFanSpeed.LOW)

    dry_temp_nibble = (_extract_frame(dry.get_raw_timings()) >> 8) & 0xF
    cool_temp_nibble = (_extract_frame(cool_24.get_raw_timings()) >> 8) & 0xF
    assert dry_temp_nibble == cool_temp_nibble


@pytest.mark.parametrize(
    "mode",
    [
        pytest.param(LgAcMode.OFF, id="off"),
        pytest.param(LgAcMode.DRY, id="dry"),
        pytest.param(LgAcMode.FAN_ONLY, id="fan_only"),
    ],
)
def test_temperature_dropped_for_modes_that_ignore_it(mode: LgAcMode) -> None:
    """A temperature the frame cannot carry must not be stored."""
    assert LgAcCommand(mode=mode, temperature=25).temperature is None


def test_fan_dropped_for_off() -> None:
    """OFF is a fixed frame; a fan the caller passes must not be stored."""
    assert LgAcCommand(mode=LgAcMode.OFF, fan=LgAcFanSpeed.HIGH).fan is None


def test_default_modulation() -> None:
    """Default modulation must be 38 kHz."""
    cmd = LgAcCommand(mode=LgAcMode.OFF)
    assert cmd.modulation == 38000
    assert cmd.repeat_count == 0


@pytest.mark.parametrize(
    "mode",
    [
        pytest.param(LgAcMode.COOL, id="cool"),
        pytest.param(LgAcMode.HEAT, id="heat"),
    ],
)
def test_temperature_required_for_cool_heat(mode: LgAcMode) -> None:
    """COOL and HEAT modes must raise when temperature is omitted."""
    with pytest.raises(ValueError, match="temperature is required"):
        LgAcCommand(mode=mode)


@pytest.mark.parametrize(
    ("temp", "mode"),
    [
        pytest.param(15, LgAcMode.COOL, id="below_min_cool"),
        pytest.param(31, LgAcMode.COOL, id="above_max_cool"),
        pytest.param(15, LgAcMode.HEAT, id="below_min_heat"),
        pytest.param(31, LgAcMode.HEAT, id="above_max_heat"),
    ],
)
def test_temperature_out_of_range(temp: int, mode: LgAcMode) -> None:
    """Out-of-range temperatures must raise ValueError."""
    with pytest.raises(ValueError, match="out of range"):
        LgAcCommand(mode=mode, temperature=temp)


@pytest.mark.parametrize(
    ("frame", "mode", "temperature", "fan"),
    [
        pytest.param(
            _SET_COOL_24_AUTO, LgAcMode.COOL, 24, LgAcFanSpeed.AUTO, id="cool_24_auto"
        ),
        pytest.param(
            _SET_COOL_16_MEDIUM_HIGH,
            LgAcMode.COOL,
            16,
            LgAcFanSpeed.MEDIUM_HIGH,
            id="cool_16_medium_high",
        ),
        pytest.param(
            _SET_COOL_30_MEDIUM_HIGH,
            LgAcMode.COOL,
            30,
            LgAcFanSpeed.MEDIUM_HIGH,
            id="cool_30_medium_high",
        ),
        pytest.param(
            _SET_DRY_24_LOW, LgAcMode.DRY, None, LgAcFanSpeed.LOW, id="dry_low"
        ),
        pytest.param(
            _SET_FAN_ONLY_24_HIGH,
            LgAcMode.FAN_ONLY,
            None,
            LgAcFanSpeed.HIGH,
            id="fan_only_high",
        ),
        pytest.param(_OFF, LgAcMode.OFF, None, None, id="off"),
        pytest.param(
            _COOL_26_MEDIUM, LgAcMode.COOL, 26, LgAcFanSpeed.MEDIUM, id="cool_26_medium"
        ),
    ],
)
def test_decode_captured_frame(
    frame: int, mode: LgAcMode, temperature: int | None, fan: LgAcFanSpeed | None
) -> None:
    """Settings frames and power-on frames must decode to the same state."""
    result = LgAcCommand.from_raw_timings(_build_timings(frame))
    assert result is not None
    assert result.mode == mode
    assert result.temperature == temperature
    assert result.fan == fan


@pytest.mark.parametrize(
    ("mode", "temperature", "fan"),
    [
        pytest.param(LgAcMode.COOL, 22, LgAcFanSpeed.QUIET, id="cool_22_quiet"),
        pytest.param(LgAcMode.HEAT, 26, LgAcFanSpeed.MEDIUM, id="heat_26_medium"),
        pytest.param(LgAcMode.HEAT, 20, LgAcFanSpeed.LOW, id="heat_20_low"),
        pytest.param(LgAcMode.FAN_ONLY, None, LgAcFanSpeed.AUTO, id="fan_only_auto"),
    ],
)
def test_roundtrip(mode: LgAcMode, temperature: int | None, fan: LgAcFanSpeed) -> None:
    """Roundtrip encode-decode must preserve mode, fan, and temperature."""
    cmd = LgAcCommand(mode=mode, temperature=temperature, fan=fan)
    result = LgAcCommand.from_raw_timings(cmd.get_raw_timings())
    assert result is not None
    assert result.mode == mode
    assert result.temperature == temperature
    assert result.fan == fan


def test_decode_accepts_stretched_header_mark() -> None:
    """Receivers stretch marks; a 3200 µs header mark can arrive as 5121 µs."""
    result = LgAcCommand.from_raw_timings(
        _build_timings(_SET_COOL_24_AUTO, (5121, 9900))
    )
    assert result is not None
    assert result.mode == LgAcMode.COOL


def test_decode_accepts_alternate_header() -> None:
    """Some LG units use the longer 8500/4250 header with an identical payload."""
    result = LgAcCommand.from_raw_timings(_build_timings(_SET_COOL_24_AUTO, _ALT_HDR))
    assert result is not None
    assert result.mode == LgAcMode.COOL
    assert result.temperature == 24


def test_decode_returns_none_for_short_timings() -> None:
    """from_raw_timings must return None for incomplete signals."""
    assert LgAcCommand.from_raw_timings([500, -400]) is None


def test_decode_returns_none_without_trailing_mark() -> None:
    """A frame truncated before its trailing mark must not decode as valid."""
    timings = _build_timings(_SET_COOL_24_AUTO)
    assert LgAcCommand.from_raw_timings(timings[:-1]) is None


def test_decode_returns_none_for_invalid_header() -> None:
    """from_raw_timings must return None when the header space matches no LG variant."""
    timings = _build_timings(_SET_COOL_24_AUTO, (3200, 500))
    assert LgAcCommand.from_raw_timings(timings) is None


def test_decode_returns_none_for_nec_signal() -> None:
    """A NEC leader is close enough to the alternate LG header to pass the header gate.

    The signature is what rejects it, so it must keep doing so.
    """
    junk = [9000, -4500] + [560, -1690] * 32 + [560]
    assert LgAcCommand.from_raw_timings(junk) is None


def test_decode_returns_none_for_out_of_tolerance_bit() -> None:
    """A space matching neither a zero nor a one must reject the frame."""
    timings = _build_timings(_SET_COOL_24_AUTO)
    timings[3] = -1000  # between the zero (550) and one (1600) spaces
    assert LgAcCommand.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    "frame",
    [
        # Valid signature and mode, checksum nibble 0x1 where 0x0 is correct.
        pytest.param(0x8800001, id="bad_checksum"),
        # Mode byte 0xFF maps to no LgAcMode; checksum 0xE is correct.
        pytest.param(0x88FF00E, id="unknown_mode"),
        # Fan nibble 0xF maps to no LgAcFanSpeed; checksum 0x0 is correct.
        pytest.param(0x88089F0, id="unknown_fan"),
        # COOL with temp nibble 0x0 decodes to 15 °C, below MIN_TEMP.
        pytest.param(0x8800055, id="temp_below_min"),
        # Display toggle: shares the 0xC0 mode byte with power-off but is not it.
        pytest.param(0x88C00A6, id="display_toggle"),
    ],
)
def test_decode_returns_none_for_invalid_frame(frame: int) -> None:
    """from_raw_timings must reject frames that fail validation."""
    assert LgAcCommand.from_raw_timings(_build_timings(frame)) is None
