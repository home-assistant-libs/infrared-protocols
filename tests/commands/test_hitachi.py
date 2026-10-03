"""Tests for the Hitachi AC344 IR command."""

from collections.abc import Callable

import pytest

from infrared_protocols.commands.hitachi import (
    HitachiAc344Command,
    HitachiAcButton,
    HitachiAcDisplay,
    HitachiAcFanSpeed,
    HitachiAcMode,
    HitachiAcMoldDuration,
    HitachiAcSomatosensory,
    HitachiAcSwingH,
)

# Target hex strings for validation
_COOL_26_HIGH_ON_HEX = (
    "01 10 00 40 BF FF 00 CC 33 A5 5A 13 EC 68 97 00 "
    "FF 00 FF 00 FF 00 FF 00 FF 43 BC F1 0E 00 FF 00 "
    "FF 80 7F 03 FC 04 FB 20 DF 00 FF"
)


def _parse_hex(hex_str: str) -> list[int]:
    """Parse space-separated hex bytes into list of ints."""
    return [int(x, 16) for x in hex_str.split()]


def _extract_bytes(timings: list[int]) -> list[int]:
    """Extract payload bytes from raw timings."""
    if len(timings) < 691:
        return []
    payload: list[int] = []
    for byte_idx in range(43):
        byte_val = 0
        for bit_idx in range(8):
            t_idx = 2 + 2 * (byte_idx * 8 + bit_idx)
            space = abs(timings[t_idx + 1])
            bit = 1 if space > 800 else 0
            byte_val |= bit << bit_idx
        payload.append(byte_val)
    return payload


def _build_timings(
    payload: list[int],
    header_mark: int = 3300,
    header_space: int = 1600,
    bit_mark: int = 400,
    bit_zero_space: int = 400,
    bit_one_space: int = 1200,
    footer_mark: int = 400,
) -> list[int]:
    """Build raw timings from payload bytes."""
    timings = [header_mark, -header_space]
    for byte_val in payload:
        for bit_idx in range(8):
            bit = (byte_val >> bit_idx) & 1
            timings.append(bit_mark)
            timings.append(-bit_one_space if bit else -bit_zero_space)
    timings.append(footer_mark)
    return timings


def test_encode_timing_values() -> None:
    """Pin the physical layer: header, bit mark, bit spaces, and footer."""
    cmd = HitachiAc344Command(
        mode=HitachiAcMode.COOL,
        temperature=26,
        fan=HitachiAcFanSpeed.HIGH,
        power=True,
    )
    timings = cmd.get_raw_timings()

    assert timings[0] == 3300
    assert timings[1] == -1600
    assert len(timings) == 691
    assert all(mark == 400 for mark in timings[2::2])
    assert {abs(space) for space in timings[3::2]} == {400, 1200}
    assert timings[-1] == 400


def test_encode_cool_26_high_on() -> None:
    """Encoder output for 26C COOL HIGH POWER-ON must equal the target hex sequence."""
    cmd = HitachiAc344Command(
        mode=HitachiAcMode.COOL,
        temperature=26,
        fan=HitachiAcFanSpeed.HIGH,
        power=True,
        swing_v=True,
        button=HitachiAcButton.POWER,
    )
    expected_bytes = _parse_hex(_COOL_26_HIGH_ON_HEX)
    actual_bytes = _extract_bytes(cmd.get_raw_timings())
    assert actual_bytes == expected_bytes


def test_encode_power_off() -> None:
    """Power-off must correctly adjust power byte and its checksum."""
    cmd = HitachiAc344Command(
        mode=HitachiAcMode.COOL,
        temperature=26,
        fan=HitachiAcFanSpeed.HIGH,
        power=False,
    )
    actual_bytes = _extract_bytes(cmd.get_raw_timings())
    assert actual_bytes[27] == 0xE1
    assert actual_bytes[28] == 0x1E


@pytest.mark.parametrize(
    (
        "mode",
        "temperature",
        "fan",
        "power",
        "swing_v",
        "swing_h",
        "eco",
        "display",
        "somatosensory",
        "off_timer_mins",
        "on_timer_mins",
        "timer_daily",
        "mold_prevention",
        "mold_duration",
        "button",
    ),
    [
        pytest.param(
            HitachiAcMode.COOL,
            26,
            HitachiAcFanSpeed.HIGH,
            True,
            False,
            HitachiAcSwingH.MIDDLE,
            False,
            HitachiAcDisplay.BRIGHT,
            HitachiAcSomatosensory.COMFORT,
            None,
            None,
            False,
            False,
            HitachiAcMoldDuration.MINS_30,
            HitachiAcButton.POWER,
            id="cool_26_high_on_power",
        ),
        pytest.param(
            HitachiAcMode.HEAT,
            20,
            HitachiAcFanSpeed.LOW,
            True,
            True,
            HitachiAcSwingH.RIGHT_MAX,
            True,
            HitachiAcDisplay.MEDIUM,
            HitachiAcSomatosensory.MOISTURIZING,
            180,
            None,
            False,
            False,
            HitachiAcMoldDuration.MINS_30,
            HitachiAcButton.TEMPERATURE,
            id="heat_20_low_on_swing_off_timer",
        ),
        pytest.param(
            HitachiAcMode.DRY,
            24,
            HitachiAcFanSpeed.SILENT,
            False,
            False,
            HitachiAcSwingH.LEFT,
            False,
            HitachiAcDisplay.DIM,
            HitachiAcSomatosensory.COMFORT,
            None,
            120,
            True,
            True,
            HitachiAcMoldDuration.MINS_10,
            HitachiAcButton.CLEAN,
            id="dry_24_on_timer_mold_clean",
        ),
        pytest.param(
            HitachiAcMode.AUTO,
            3,
            HitachiAcFanSpeed.HIGH,
            True,
            True,
            HitachiAcSwingH.MIDDLE,
            False,
            HitachiAcDisplay.OFF,
            HitachiAcSomatosensory.MOISTURIZING,
            1440,
            1440,
            True,
            True,
            HitachiAcMoldDuration.MINS_60,
            HitachiAcButton.MOLD,
            id="auto_both_timers_mold_60_daily",
        ),
        pytest.param(
            HitachiAcMode.AUTO,
            -3,
            HitachiAcFanSpeed.SILENT,
            True,
            False,
            HitachiAcSwingH.LEFT_MAX,
            False,
            HitachiAcDisplay.BRIGHT,
            HitachiAcSomatosensory.COMFORT,
            60,
            None,
            False,
            True,
            HitachiAcMoldDuration.MINS_20,
            HitachiAcButton.MOLD_TIME,
            id="mold_20_mins_setup",
        ),
        pytest.param(
            HitachiAcMode.COOL,
            28,
            HitachiAcFanSpeed.MEDIUM,
            True,
            False,
            HitachiAcSwingH.RIGHT,
            False,
            HitachiAcDisplay.DIM,
            HitachiAcSomatosensory.COMFORT,
            None,
            None,
            False,
            True,
            HitachiAcMoldDuration.MINS_45,
            HitachiAcButton.PM25,
            id="pm25_display_mold_45",
        ),
        pytest.param(
            HitachiAcMode.COOL,
            26,
            HitachiAcFanSpeed.AUTO,
            True,
            False,
            HitachiAcSwingH.MIDDLE,
            False,
            HitachiAcDisplay.BRIGHT,
            HitachiAcSomatosensory.COMFORT,
            60,
            None,
            False,
            False,
            HitachiAcMoldDuration.MINS_30,
            HitachiAcButton.OFF_TIMER,
            id="off_timer_1_hour",
        ),
        pytest.param(
            HitachiAcMode.COOL,
            26,
            HitachiAcFanSpeed.AUTO,
            True,
            False,
            HitachiAcSwingH.MIDDLE,
            False,
            HitachiAcDisplay.BRIGHT,
            HitachiAcSomatosensory.COMFORT,
            120,
            None,
            False,
            False,
            HitachiAcMoldDuration.MINS_30,
            HitachiAcButton.OFF_TIMER,
            id="off_timer_2_hours",
        ),
        pytest.param(
            HitachiAcMode.COOL,
            26,
            HitachiAcFanSpeed.AUTO,
            True,
            False,
            HitachiAcSwingH.MIDDLE,
            False,
            HitachiAcDisplay.BRIGHT,
            HitachiAcSomatosensory.COMFORT,
            None,
            None,
            False,
            False,
            HitachiAcMoldDuration.MINS_30,
            HitachiAcButton.CANCEL_TIMER,
            id="cancel_timer_button",
        ),
    ],
)
def test_roundtrip(
    mode: HitachiAcMode,
    temperature: int,
    fan: HitachiAcFanSpeed,
    power: bool,
    swing_v: bool,
    swing_h: HitachiAcSwingH,
    eco: bool,
    display: HitachiAcDisplay,
    somatosensory: HitachiAcSomatosensory,
    off_timer_mins: int | None,
    on_timer_mins: int | None,
    timer_daily: bool,
    mold_prevention: bool,
    mold_duration: HitachiAcMoldDuration,
    button: HitachiAcButton,
) -> None:
    """Roundtrip encode-decode must preserve all Hitachi AC344 protocol fields."""
    cmd = HitachiAc344Command(
        mode=mode,
        temperature=temperature,
        fan=fan,
        power=power,
        swing_v=swing_v,
        swing_h=swing_h,
        eco=eco,
        display=display,
        somatosensory=somatosensory,
        off_timer_mins=off_timer_mins,
        on_timer_mins=on_timer_mins,
        timer_daily=timer_daily,
        mold_prevention=mold_prevention,
        mold_duration=mold_duration,
        button=button,
    )
    decoded = HitachiAc344Command.from_raw_timings(cmd.get_raw_timings())
    assert decoded is not None
    assert decoded.mode == mode
    assert decoded.temperature == temperature
    assert decoded.fan == fan
    assert decoded.power == power
    assert decoded.swing_v == (False if mold_prevention else swing_v)
    assert decoded.swing_h == swing_h
    assert decoded.eco == eco
    assert decoded.display == display
    assert decoded.somatosensory == somatosensory
    assert decoded.off_timer_mins == off_timer_mins
    assert decoded.on_timer_mins == on_timer_mins
    assert decoded.timer_daily == timer_daily
    assert decoded.mold_prevention == mold_prevention
    if mold_prevention:
        assert decoded.mold_duration == mold_duration
    assert decoded.button == button


@pytest.mark.parametrize(
    ("temp", "msg"),
    [
        pytest.param(15, "out of range", id="temp_below_min"),
        pytest.param(33, "out of range", id="temp_above_max"),
    ],
)
def test_invalid_temperature_range(temp: int, msg: str) -> None:
    """Out-of-range temperatures in non-AUTO mode must raise ValueError."""
    with pytest.raises(ValueError, match=msg):
        HitachiAc344Command(mode=HitachiAcMode.COOL, temperature=temp)


@pytest.mark.parametrize(
    ("temp", "msg"),
    [
        pytest.param(-4, "out of range", id="auto_temp_below_min"),
        pytest.param(4, "out of range", id="auto_temp_above_max"),
    ],
)
def test_invalid_auto_temperature_range(temp: int, msg: str) -> None:
    """Out-of-range temperatures in AUTO mode must raise ValueError."""
    with pytest.raises(ValueError, match=msg):
        HitachiAc344Command(mode=HitachiAcMode.AUTO, temperature=temp)


@pytest.mark.parametrize(
    ("mins", "msg"),
    [
        pytest.param(59, "out of range", id="off_timer_below_min"),
        pytest.param(1441, "out of range", id="off_timer_above_max"),
    ],
)
def test_invalid_off_timer_range(mins: int, msg: str) -> None:
    """Out-of-range timer durations must raise ValueError."""
    with pytest.raises(ValueError, match=msg):
        HitachiAc344Command(
            mode=HitachiAcMode.COOL,
            temperature=26,
            off_timer_mins=mins,
        )


@pytest.mark.parametrize(
    ("mins", "msg"),
    [
        pytest.param(59, "out of range", id="on_timer_below_min"),
        pytest.param(1441, "out of range", id="on_timer_above_max"),
        pytest.param(121, "must be a multiple of 2", id="on_timer_not_even"),
    ],
)
def test_invalid_on_timer_range(mins: int, msg: str) -> None:
    """Out-of-range or odd timer durations must raise ValueError."""
    with pytest.raises(ValueError, match=msg):
        HitachiAc344Command(
            mode=HitachiAcMode.COOL,
            temperature=26,
            on_timer_mins=mins,
        )


@pytest.mark.parametrize(
    "payload_modifier",
    [
        pytest.param(lambda p: p.__setitem__(0, 0x02), id="bad_prefix"),
        pytest.param(lambda p: p.__setitem__(9, 0x00), id="bad_checksum_9_10"),
        pytest.param(lambda p: p.__setitem__(13, 0x69), id="temp_not_div_4"),
        pytest.param(lambda p: p.__setitem__(27, 0x00), id="bad_power_val"),
    ],
)
def test_decode_returns_none_for_corrupted_payload(
    payload_modifier: Callable[[list[int]], None],
) -> None:
    """Decoded command must be None if the packet payload fields are corrupted."""
    base_payload = _parse_hex(_COOL_26_HIGH_ON_HEX)
    payload_modifier(base_payload)
    timings = _build_timings(base_payload)
    assert HitachiAc344Command.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    "timings_modifier",
    [
        pytest.param(lambda t: t.pop(), id="truncated_timings"),
        pytest.param(lambda t: t.__setitem__(0, 1000), id="bad_header_mark"),
        pytest.param(lambda t: t.__setitem__(1, -500), id="bad_header_space"),
        pytest.param(lambda t: t.__setitem__(690, 1000), id="bad_footer_mark"),
    ],
)
def test_decode_returns_none_for_corrupted_timings(
    timings_modifier: Callable[[list[int]], None],
) -> None:
    """Decoded command must be None if physical-layer timings are corrupted."""
    cmd = HitachiAc344Command(
        mode=HitachiAcMode.COOL,
        temperature=26,
        fan=HitachiAcFanSpeed.HIGH,
        power=True,
    )
    timings = list(cmd.get_raw_timings())
    timings_modifier(timings)
    assert HitachiAc344Command.from_raw_timings(timings) is None
