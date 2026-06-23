"""Tests for the LG air-conditioner IR command and decoder."""

import pytest

from infrared_protocols.commands.lg_ac import (
    LgAcCommand,
    LgAcFanSpeed,
    LgAcMode,
    LgAcState,
    MIN_TEMP,
    _OFF_HDR_MARK,
    _OFF_HDR_SPACE,
    _HDR_MARK,
    _HDR_SPACE,
    _checksum,
    _encode_frame,
    decode,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_frame(timings: list[int]) -> int:
    """Extract the 28-bit frame integer from raw timings."""
    frame = 0
    i = 2
    bits_read = 0
    while i + 1 < len(timings) and bits_read < 28:
        frame = (frame << 1) | (1 if abs(timings[i + 1]) > 1000 else 0)
        i += 2
        bits_read += 1
    return frame


# ── Encoder: known-good frame values (verified against hardware captures) ────


def test_encode_off_frame() -> None:
    """Power-off must produce frame 0x88C0051 with LG2-short header."""
    cmd = LgAcCommand(mode=LgAcMode.OFF)
    timings = cmd.get_raw_timings()
    assert timings[0] == _OFF_HDR_MARK
    assert abs(timings[1]) == _OFF_HDR_SPACE
    assert _extract_frame(timings) == 0x88C0051


def test_encode_cool_24_auto_frame() -> None:
    """Cool 24 °C / auto fan must produce frame 0x880095E."""
    cmd = LgAcCommand(mode=LgAcMode.COOL, temperature=24, fan=LgAcFanSpeed.AUTO)
    assert cmd.get_raw_timings()[0] == _HDR_MARK
    assert _extract_frame(cmd.get_raw_timings()) == 0x880095E


def test_encode_dry_auto_frame() -> None:
    """Dry / auto fan must produce frame 0x880195F."""
    cmd = LgAcCommand(mode=LgAcMode.DRY, fan=LgAcFanSpeed.AUTO)
    assert _extract_frame(cmd.get_raw_timings()) == 0x880195F


@pytest.mark.parametrize(
    ("temp", "fan", "expected_hex"),
    [
        pytest.param(18, LgAcFanSpeed.AUTO, 0x8800358, id="18_auto"),
        pytest.param(30, LgAcFanSpeed.AUTO, 0x8800F54, id="30_auto"),
        pytest.param(24, LgAcFanSpeed.LOW, 0x8800909, id="24_low"),
        pytest.param(24, LgAcFanSpeed.MEDIUM, 0x880092B, id="24_medium"),
        pytest.param(24, LgAcFanSpeed.HIGH, 0x880094D, id="24_high"),
    ],
)
def test_encode_cool_frames(temp: int, fan: LgAcFanSpeed, expected_hex: int) -> None:
    """Verify cool encoder against known-good frames."""
    cmd = LgAcCommand(mode=LgAcMode.COOL, temperature=temp, fan=fan)
    assert _extract_frame(cmd.get_raw_timings()) == expected_hex


# ── Encoder: modulation and repeat defaults ───────────────────────────────────


def test_default_modulation() -> None:
    """Default modulation must be 38 kHz."""
    cmd = LgAcCommand(mode=LgAcMode.OFF)
    assert cmd.modulation == 38000
    assert cmd.repeat_count == 0


# ── Encoder: validation ───────────────────────────────────────────────────────


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


# ── Decoder: roundtrips ───────────────────────────────────────────────────────


def test_decode_roundtrip_cool() -> None:
    """Decoded cool frame must reconstruct mode, fan, and temperature."""
    cmd = LgAcCommand(mode=LgAcMode.COOL, temperature=22, fan=LgAcFanSpeed.HIGH)
    result = decode(cmd.get_raw_timings())
    assert result == LgAcState(mode=LgAcMode.COOL, fan=LgAcFanSpeed.HIGH, temp_c=22)


def test_decode_roundtrip_off() -> None:
    """Decoded off frame must return LgAcMode.OFF."""
    result = decode(LgAcCommand(mode=LgAcMode.OFF).get_raw_timings())
    assert result is not None
    assert result.mode == LgAcMode.OFF


def test_decode_roundtrip_dry() -> None:
    """Decoded dry frame must return DRY mode with correct fan."""
    result = decode(LgAcCommand(mode=LgAcMode.DRY, fan=LgAcFanSpeed.LOW).get_raw_timings())
    assert result is not None
    assert result.mode == LgAcMode.DRY
    assert result.fan == LgAcFanSpeed.LOW


def test_decode_roundtrip_heat() -> None:
    """Decoded heat frame must reconstruct mode, fan, and temperature."""
    result = decode(
        LgAcCommand(mode=LgAcMode.HEAT, temperature=26, fan=LgAcFanSpeed.MEDIUM).get_raw_timings()
    )
    assert result == LgAcState(mode=LgAcMode.HEAT, fan=LgAcFanSpeed.MEDIUM, temp_c=26)


def test_decode_roundtrip_fan_only() -> None:
    """Decoded fan-only frame must return FAN_ONLY with correct fan speed."""
    result = decode(LgAcCommand(mode=LgAcMode.FAN_ONLY, fan=LgAcFanSpeed.HIGH).get_raw_timings())
    assert result is not None
    assert result.mode == LgAcMode.FAN_ONLY
    assert result.fan == LgAcFanSpeed.HIGH


@pytest.mark.parametrize(
    ("mode", "temp", "fan"),
    [
        pytest.param(LgAcMode.COOL, 24, LgAcFanSpeed.AUTO, id="cool_24_auto"),
        pytest.param(LgAcMode.COOL, 18, LgAcFanSpeed.LOW, id="cool_18_low"),
        pytest.param(LgAcMode.COOL, 30, LgAcFanSpeed.HIGH, id="cool_30_high"),
        pytest.param(LgAcMode.HEAT, 20, LgAcFanSpeed.MEDIUM, id="heat_20_medium"),
        pytest.param(LgAcMode.HEAT, 28, LgAcFanSpeed.QUIET, id="heat_28_quiet"),
    ],
)
def test_decode_roundtrip_parametrized(
    mode: LgAcMode, temp: int, fan: LgAcFanSpeed
) -> None:
    """Roundtrip encode→decode must preserve mode, fan, and temperature."""
    cmd = LgAcCommand(mode=mode, temperature=temp, fan=fan)
    result = decode(cmd.get_raw_timings())
    assert result == LgAcState(mode=mode, fan=fan, temp_c=temp)


# ── Decoder: rejection cases ──────────────────────────────────────────────────


def test_decode_returns_none_for_short_timings() -> None:
    """decode must return None for incomplete signals."""
    assert decode([500, -400]) is None


def test_decode_returns_none_for_non_lg_ac() -> None:
    """decode must return None for frames with wrong signature."""
    # NEC-style header (9000/4500) with wrong signature
    junk = [9000, -4500] + [550, -1600] * 32
    assert decode(junk) is None


def test_decode_returns_none_for_invalid_header() -> None:
    """decode must return None when header matches neither LG standard nor LG2."""
    timings = [500, -500] + [550, -550] * 28
    assert decode(timings) is None


def test_decode_returns_none_for_bad_checksum() -> None:
    """decode must return None when the checksum nibble is wrong."""
    # 0x8800001: valid 0x88 signature but checksum nibble is 1, not 0
    timings = _encode_frame(0x8800001, _HDR_MARK, _HDR_SPACE)
    assert decode(timings) is None


def test_decode_returns_none_for_unknown_mode() -> None:
    """decode must return None when mode nibbles have no mapping."""
    # (nibs[4], nibs[3]) = (0xF, 0xF) is not in _CMD_NIBS_TO_MODE
    frame = _checksum(0x88FF000)
    timings = _encode_frame(frame, _HDR_MARK, _HDR_SPACE)
    assert decode(timings) is None
