"""Tests for the Daikin air-conditioner IR command."""

from calendar import Day
from dataclasses import replace
from datetime import time
from typing import Any

import pytest

from infrared_protocols.commands.daikin_ac import (
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    DaikinAcBrightness,
    DaikinAcClock,
    DaikinAcComfort,
    DaikinAcCommand,
    DaikinAcFanSpeed,
    DaikinAcMode,
    DaikinAcState,
)

# Physical-layer constants are duplicated here rather than imported
# so the tests are independent
_LEADER_MARK = 3400
_LEADER_SPACE = 1700
_BIT_MARK = 425
_ZERO_SPACE = 425
_ONE_SPACE = 1275
_GAP = 32300
_MIN_GAP = 4000

_WAKE_UP = [425, -425] * 5 + [425, -32300]

_UNSET_CLOCK = "11 da 27 00 42 00 10 64"
_COMFORT_BRIGHTNESS_OFF = "11 da 27 00 c5 30 00 07"
_COOL_25 = DaikinAcState(mode=DaikinAcMode.COOL, temperature=25)
# The comfort and clock frames a remote sends out of the box
_BRIGHT = DaikinAcComfort()
_CLOCK_UNSET = DaikinAcClock()
_DISPLAY_OFF = DaikinAcComfort(brightness=DaikinAcBrightness.OFF)
_COOL_32 = DaikinAcState(mode=DaikinAcMode.COOL, temperature=32)
_THURSDAY_0407 = DaikinAcClock(time_of_day=time(4, 7), weekday=Day.THURSDAY)
_SATURDAY_0009 = DaikinAcClock(time_of_day=time(0, 9), weekday=Day.SATURDAY)
_AUTO_25_FAN_1 = DaikinAcState(
    mode=DaikinAcMode.AUTO, temperature=25, fan=DaikinAcFanSpeed.LEVEL_1
)

# Each entry is the (comfort, clock, state) frames captured from a physical remote,
# and the command the remote sent them for.
_CAPTURED: dict[str, tuple[tuple[str, str, str], DaikinAcCommand]] = {
    "cool_24_bright": (
        (
            "11 da 27 00 c5 10 00 e7",
            _UNSET_CLOCK,
            "11 da 27 00 00 39 30 00 a0 00 00 06 60 00 00 c1 80 00 c2",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.COOL, temperature=24),
            comfort=_BRIGHT,
            clock=_CLOCK_UNSET,
        ),
    ),
    "off_cool_23": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 38 2e 00 a0 00 00 06 60 00 00 c1 80 00 bf",
        ),
        DaikinAcCommand(
            state=DaikinAcState(power=False, mode=DaikinAcMode.COOL, temperature=23),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "off_cool_23_dim": (
        (
            "11 da 27 00 c5 20 00 f7",
            _UNSET_CLOCK,
            "11 da 27 00 00 38 2e 00 a0 00 00 06 60 00 00 c1 80 00 bf",
        ),
        DaikinAcCommand(
            state=DaikinAcState(power=False, mode=DaikinAcMode.COOL, temperature=23),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.DIM),
            clock=_CLOCK_UNSET,
        ),
    ),
    "off_cool_23_quiet": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 38 2e 00 a0 00 00 06 60 20 00 c1 80 00 df",
        ),
        DaikinAcCommand(
            state=DaikinAcState(
                power=False, mode=DaikinAcMode.COOL, temperature=23, quiet=True
            ),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_23_econo": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 2e 00 a0 00 00 06 60 00 00 c1 84 00 c4",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.COOL, temperature=23, econo=True),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_23_econo_quiet": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 2e 00 a0 00 00 06 60 20 00 c1 84 00 e4",
        ),
        DaikinAcCommand(
            state=DaikinAcState(
                mode=DaikinAcMode.COOL, temperature=23, econo=True, quiet=True
            ),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_23_comfort_sensor": (
        (
            "11 da 27 00 c5 30 10 17",
            _UNSET_CLOCK,
            "11 da 27 00 00 39 2e 00 a0 00 00 06 60 00 00 c1 82 00 c2",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.COOL, temperature=23, sensor=True),
            comfort=DaikinAcComfort(comfort=True, brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_23_swing_h": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 2e 00 a0 0f 00 06 60 00 00 c1 80 00 cf",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.COOL, temperature=23, swing_h=True),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_23_swing_both": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 2e 00 af 0f 00 06 60 00 00 c1 80 00 de",
        ),
        DaikinAcCommand(
            state=DaikinAcState(
                mode=DaikinAcMode.COOL, temperature=23, swing_v=True, swing_h=True
            ),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_23_swing_v": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 2e 00 af 00 00 06 60 00 00 c1 80 00 cf",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.COOL, temperature=23, swing_v=True),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_18": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 24 00 a0 00 00 06 60 00 00 c1 80 00 b6",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.COOL, temperature=18),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_32": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 40 00 a0 00 00 06 60 00 00 c1 80 00 d2",
        ),
        DaikinAcCommand(
            state=_COOL_32,
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_32_fan_silent": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 40 00 b0 00 00 06 60 00 00 c1 80 00 e2",
        ),
        DaikinAcCommand(
            state=DaikinAcState(
                mode=DaikinAcMode.COOL, temperature=32, fan=DaikinAcFanSpeed.SILENT
            ),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_32_fan_1": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 40 00 30 00 00 06 60 00 00 c1 80 00 62",
        ),
        DaikinAcCommand(
            state=DaikinAcState(
                mode=DaikinAcMode.COOL, temperature=32, fan=DaikinAcFanSpeed.LEVEL_1
            ),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "cool_32_fan_5": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 39 40 00 70 00 00 06 60 00 00 c1 80 00 a2",
        ),
        DaikinAcCommand(
            state=DaikinAcState(
                mode=DaikinAcMode.COOL, temperature=32, fan=DaikinAcFanSpeed.LEVEL_5
            ),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "heat_10": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 49 14 00 a0 00 00 06 60 00 00 c1 80 00 b6",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.HEAT, temperature=10),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "heat_30": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 49 3c 00 a0 00 00 06 60 00 00 c1 80 00 de",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.HEAT, temperature=30),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "auto_18": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 09 24 00 a0 00 00 06 60 00 00 c1 80 00 86",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.AUTO, temperature=18),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "fan_only": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 69 32 00 a0 00 00 06 60 00 00 c1 80 00 f4",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.FAN_ONLY, temperature=None),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "dry": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            _UNSET_CLOCK,
            "11 da 27 00 00 29 c0 00 a0 00 00 06 60 00 00 c1 80 00 42",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.DRY, temperature=None),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_CLOCK_UNSET,
        ),
    ),
    "clock_thursday_0405": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            "11 da 27 00 42 f5 28 71",
            "11 da 27 00 00 39 32 00 a0 00 00 06 60 00 00 c1 80 00 c4",
        ),
        DaikinAcCommand(
            state=_COOL_25,
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=DaikinAcClock(time_of_day=time(4, 5), weekday=Day.THURSDAY),
        ),
    ),
    "on_timer_0640": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            "11 da 27 00 42 f6 28 72",
            "11 da 27 00 00 3b 32 00 a0 00 90 01 60 00 00 c1 80 00 51",
        ),
        DaikinAcCommand(
            state=DaikinAcState(
                mode=DaikinAcMode.COOL, temperature=25, on_timer=time(6, 40)
            ),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=DaikinAcClock(time_of_day=time(4, 6), weekday=Day.THURSDAY),
        ),
    ),
    "on_timer_0640_off_timer_2240": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            "11 da 27 00 42 f7 28 73",
            "11 da 27 00 00 3f 32 00 a0 00 90 01 55 00 00 c1 80 00 4a",
        ),
        DaikinAcCommand(
            state=DaikinAcState(
                mode=DaikinAcMode.COOL,
                temperature=25,
                on_timer=time(6, 40),
                off_timer=time(22, 40),
            ),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_THURSDAY_0407,
        ),
    ),
    "cool_25_powerful": (
        (
            _COMFORT_BRIGHTNESS_OFF,
            "11 da 27 00 42 f7 28 73",
            "11 da 27 00 00 39 32 00 a0 00 00 06 60 01 00 c1 80 00 c5",
        ),
        DaikinAcCommand(
            state=DaikinAcState(mode=DaikinAcMode.COOL, temperature=25, powerful=True),
            comfort=DaikinAcComfort(brightness=DaikinAcBrightness.OFF),
            clock=_THURSDAY_0407,
        ),
    ),
    # Two consecutive presses on a remote with a weekly schedule, turning it off
    "auto_25_fan_1_weekly": (
        (
            "11 da 27 00 c5 10 00 e7",
            "11 da 27 00 42 09 38 95",
            "11 da 27 00 00 09 32 00 30 00 00 06 60 00 00 c1 00 00 a4",
        ),
        DaikinAcCommand(
            state=replace(_AUTO_25_FAN_1, weekly_timer=True),
            clock=_SATURDAY_0009,
            comfort=_BRIGHT,
        ),
    ),
    "auto_25_fan_1_weekly_off": (
        (
            "11 da 27 00 c5 10 00 e7",
            "11 da 27 00 42 09 38 95",
            "11 da 27 00 00 09 32 00 30 00 00 06 60 00 00 c1 80 00 24",
        ),
        DaikinAcCommand(state=_AUTO_25_FAN_1, clock=_SATURDAY_0009, comfort=_BRIGHT),
    ),
}

# The on- and off-timer transmission as an ESPHome receiver delivered it: one signal
# per frame, since the gap between frames is longer than the receiver waits.
_TIMERS_WAKE_UP = [
    489, -378, 463, -403, 461, -404, 462, -404, 460, -406, 461, -10000,
]  # fmt: skip

_TIMERS_COMFORT = [
    3497, -1698, 462, -1269, 463, -405, 461, -405, 460, -405, 461, -1269, 462, -404,
    462, -405, 460, -405, 461, -405, 460, -1271, 461, -405, 461, -1268, 462, -1270, 462,
    -405, 461, -1269, 463, -1268, 463, -1268, 463, -1269, 461, -1270, 464, -404, 460,
    -405, 461, -1269, 463, -404, 461, -404, 462, -405, 461, -404, 461, -405, 461, -405,
    462, -403, 461, -405, 462, -404, 461, -404, 461, -1269, 463, -404, 462, -1268, 463,
    -404, 461, -405, 461, -404, 462, -1269, 461, -1270, 463, -404, 462, -403, 462, -404,
    461, -405, 461, -1269, 463, -1269, 463, -403, 463, -403, 461, -405, 462, -403, 462,
    -404, 462, -403, 463, -403, 462, -404, 461, -405, 461, -404, 462, -1268, 461, -1271,
    463, -1268, 463, -404, 461, -405, 461, -404, 462, -404, 461, -405, 461, -10000,
]  # fmt: skip

_TIMERS_CLOCK = [
    3496, -1699, 462, -1270, 459, -408, 434, -431, 461, -404, 460, -1271, 462, -405,
    460, -405, 461, -405, 461, -405, 460, -1270, 463, -403, 462, -1269, 461, -1270, 462,
    -405, 461, -1269, 462, -1269, 462, -1269, 463, -1269, 462, -1269, 462, -405, 460,
    -406, 461, -1270, 460, -406, 460, -406, 459, -406, 461, -405, 461, -405, 460, -405,
    462, -404, 460, -405, 460, -406, 461, -405, 461, -405, 459, -1271, 462, -405, 461,
    -404, 462, -404, 459, -407, 461, -1269, 461, -405, 462, -1268, 462, -1269, 463,
    -1269, 462, -405, 462, -1268, 462, -1270, 462, -1269, 462, -1270, 462, -405, 460,
    -405, 460, -405, 461, -1269, 463, -405, 461, -1269, 461, -406, 459, -406, 461,
    -1270, 462, -1269, 462, -405, 460, -405, 461, -1269, 462, -1270, 461, -1270, 461,
    -406, 461, -10000,
]  # fmt: skip

_TIMERS_STATE = [
    3497, -1697, 462, -1270, 462, -404, 462, -404, 460, -406, 462, -1268, 461, -406,
    461, -405, 461, -405, 460, -405, 460, -1270, 462, -404, 462, -1269, 462, -1270, 461,
    -405, 460, -1270, 462, -1270, 462, -1270, 461, -1270, 462, -1269, 463, -404, 462,
    -404, 461, -1269, 461, -405, 462, -404, 461, -404, 462, -405, 458, -407, 462, -404,
    461, -404, 461, -405, 461, -404, 462, -405, 460, -406, 460, -405, 462, -403, 462,
    -404, 461, -405, 461, -404, 462, -404, 461, -405, 461, -1269, 463, -1269, 462,
    -1269, 462, -1269, 461, -1270, 463, -1268, 463, -405, 461, -404, 461, -405, 461,
    -1269, 464, -403, 461, -404, 463, -1268, 463, -1269, 461, -406, 461, -404, 460,
    -406, 460, -405, 462, -404, 461, -404, 462, -404, 462, -404, 461, -404, 462, -404,
    461, -405, 460, -405, 461, -405, 462, -404, 461, -405, 461, -1269, 462, -404, 463,
    -1267, 464, -404, 461, -404, 462, -404, 462, -403, 463, -403, 463, -403, 461, -404,
    462, -404, 462, -404, 461, -404, 461, -405, 462, -403, 462, -1269, 463, -404, 462,
    -404, 461, -1269, 463, -1268, 463, -404, 460, -405, 462, -404, 462, -404, 461, -405,
    461, -404, 461, -405, 462, -1268, 463, -404, 460, -1270, 463, -404, 462, -1268, 462,
    -404, 463, -1268, 464, -403, 461, -404, 462, -404, 461, -405, 462, -403, 463, -403,
    462, -404, 462, -404, 461, -404, 462, -404, 461, -405, 462, -403, 462, -404, 462,
    -404, 461, -405, 463, -402, 462, -404, 462, -1267, 464, -404, 462, -403, 462, -404,
    462, -404, 462, -404, 462, -1267, 464, -1268, 462, -405, 463, -402, 463, -403, 461,
    -404, 463, -403, 462, -404, 463, -402, 463, -1268, 463, -403, 463, -403, 462, -404,
    462, -404, 460, -406, 462, -403, 463, -403, 461, -404, 463, -403, 462, -1268, 464,
    -403, 462, -1268, 463, -404, 462, -404, 462, -1268, 463, -403, 462, -10000,
]  # fmt: skip


def _frame_timings(frame: str) -> list[int]:
    """Build one frame's raw timings from its bytes, bypassing the encoder."""
    timings = [_LEADER_MARK, -_LEADER_SPACE]
    for byte in bytes.fromhex(frame):
        for i in range(8):
            timings += [_BIT_MARK, -(_ONE_SPACE if byte >> i & 1 else _ZERO_SPACE)]
    timings += [_BIT_MARK, -_GAP]
    return timings


def _transmission_timings(frames: tuple[str, ...]) -> list[int]:
    """Build a whole transmission's raw timings: the wake-up burst, then the frames."""
    timings = list(_WAKE_UP)
    for frame in frames:
        timings += _frame_timings(frame)
    return timings


def _extract_frames(timings: list[int]) -> list[str]:
    """Pull each frame's bytes back out of raw timings, skipping the wake-up burst."""
    frames: list[str] = []
    bits: list[int] = []
    for index in range(1, len(timings), 2):
        space = abs(timings[index])
        if space >= _MIN_GAP:
            if len(bits) % 8 == 0 and bits:
                frames.append(
                    bytes(
                        sum(bits[i + j] << j for j in range(8))
                        for i in range(0, len(bits), 8)
                    ).hex(" ")
                )
            bits = []
        elif timings[index - 1] == _LEADER_MARK:
            bits = []
        else:
            bits.append(1 if space > (_ONE_SPACE + _ZERO_SPACE) // 2 else 0)
    return frames


def _parts(
    command: DaikinAcCommand | None,
) -> tuple[DaikinAcState | None, DaikinAcComfort | None, DaikinAcClock | None] | None:
    """Return a decoded command's state, comfort and clock, for comparing at once."""
    if command is None:
        return None
    return (command.state, command.comfort, command.clock)


def _decode_state(frame: str) -> DaikinAcState | None:
    """Decode a lone state frame given as hex bytes."""
    result = DaikinAcCommand.from_raw_timings(_frame_timings(frame))
    return None if result is None else result.state


def _with_checksum(frame: str) -> str:
    """Append the checksum byte to a frame given without it."""
    data = bytes.fromhex(frame)
    return (data + bytes([sum(data) & 0xFF])).hex(" ")


def test_encode_timing_values() -> None:
    """Pin the physical layer: wake-up burst, leader, bit timings and frame gaps."""
    timings = DaikinAcCommand(
        state=_COOL_25, comfort=_BRIGHT, clock=_CLOCK_UNSET
    ).get_raw_timings()

    assert timings[: len(_WAKE_UP)] == _WAKE_UP
    assert timings[len(_WAKE_UP) : len(_WAKE_UP) + 2] == [3400, -1700]
    assert {t for t in timings if t > 0} == {3400, 425}
    assert {-t for t in timings if t < 0} == {1700, 425, 1275, 32300}
    # The wake-up burst and the three frames each end with the long gap.
    assert timings.count(-32300) == 4
    assert timings[-1] == -32300


@pytest.mark.parametrize("label", list(_CAPTURED))
def test_encode_matches_captured_frames(label: str) -> None:
    """The encoder reproduces frames captured from a physical remote, byte for byte."""
    frames, command = _CAPTURED[label]

    assert _extract_frames(command.get_raw_timings()) == list(frames)


@pytest.mark.parametrize("label", list(_CAPTURED))
def test_decode_captured_transmission(label: str) -> None:
    """A captured transmission decodes back to the command it was sent for."""
    frames, expected = _CAPTURED[label]

    result = DaikinAcCommand.from_raw_timings(_transmission_timings(frames))

    assert result is not None
    assert result.state == expected.state
    assert result.comfort == expected.comfort
    assert result.clock == expected.clock


@pytest.mark.parametrize("label", list(_CAPTURED))
def test_decode_captured_frames_one_at_a_time(label: str) -> None:
    """Each captured frame decodes on its own into a command holding just its part."""
    (comfort, clock, state), expected = _CAPTURED[label]

    assert [
        _parts(DaikinAcCommand.from_raw_timings(_frame_timings(frame)))
        for frame in (comfort, clock, state)
    ] == [
        (None, expected.comfort, None),
        (None, None, expected.clock),
        (expected.state, None, None),
    ]


def test_decode_receiver_capture() -> None:
    """Decode the signals a receiver delivered, with their real timing jitter."""
    expected_state = DaikinAcState(
        mode=DaikinAcMode.COOL,
        temperature=25,
        on_timer=time(6, 40),
        off_timer=time(22, 40),
    )
    expected_comfort = DaikinAcComfort(brightness=DaikinAcBrightness.OFF)

    assert [
        _parts(DaikinAcCommand.from_raw_timings(signal))
        for signal in (_TIMERS_WAKE_UP, _TIMERS_COMFORT, _TIMERS_CLOCK, _TIMERS_STATE)
    ] == [
        None,
        (None, expected_comfort, None),
        (None, None, _THURSDAY_0407),
        (expected_state, None, None),
    ]

    # The same signals as one capture, as a receiver waiting out the gaps delivers them
    assert _parts(
        DaikinAcCommand.from_raw_timings(
            _TIMERS_WAKE_UP + _TIMERS_COMFORT + _TIMERS_CLOCK + _TIMERS_STATE
        )
    ) == (expected_state, expected_comfort, _THURSDAY_0407)


@pytest.mark.parametrize(
    ("frames", "expected"),
    [
        pytest.param((0, 1), (None, _DISPLAY_OFF, _CLOCK_UNSET), id="state_missing"),
        pytest.param(
            (1, 0, 2), (_COOL_32, _DISPLAY_OFF, _CLOCK_UNSET), id="out_of_order"
        ),
    ],
)
def test_decode_partial_transmission(
    frames: tuple[int, ...],
    expected: tuple[DaikinAcState | None, DaikinAcComfort | None, DaikinAcClock | None],
) -> None:
    """A capture decodes into the parts it carries, whatever their order."""
    captured, _ = _CAPTURED["cool_32"]

    result = DaikinAcCommand.from_raw_timings(
        _transmission_timings(tuple(captured[i] for i in frames))
    )

    assert _parts(result) == expected


def test_decode_keeps_last_of_repeated_frame() -> None:
    """When a capture holds a frame twice, the last one, the newest state, is kept."""
    (_, _, cool_32), _ = _CAPTURED["cool_32"]
    (_, _, cool_18), expected = _CAPTURED["cool_18"]

    result = DaikinAcCommand.from_raw_timings(_transmission_timings((cool_32, cool_18)))

    assert result is not None
    assert result.state == expected.state


@pytest.mark.parametrize(
    ("command", "missing"),
    [
        pytest.param(
            DaikinAcCommand(state=None, comfort=_BRIGHT, clock=_CLOCK_UNSET),
            "state",
            id="state",
        ),
        pytest.param(
            DaikinAcCommand(state=_COOL_25, comfort=None, clock=_CLOCK_UNSET),
            "comfort",
            id="comfort",
        ),
        pytest.param(
            DaikinAcCommand(state=_COOL_25, comfort=None, clock=None),
            "comfort, clock",
            id="comfort_and_clock",
        ),
    ],
)
def test_encode_needs_every_part(command: DaikinAcCommand, missing: str) -> None:
    """The unit ignores a transmission missing a frame, so sending one is refused."""
    with pytest.raises(ValueError, match=f"missing: {missing}$"):
        command.get_raw_timings()


def test_roundtrip_half_degree() -> None:
    """The frame carries half degrees, though the remotes captured step whole ones."""
    state = DaikinAcState(mode=DaikinAcMode.HEAT, temperature=21.5)

    result = DaikinAcCommand.from_raw_timings(
        DaikinAcCommand(
            state=state, comfort=_BRIGHT, clock=_CLOCK_UNSET
        ).get_raw_timings()
    )

    assert result is not None
    assert result.state == state


@pytest.mark.parametrize("weekday", list(Day))
def test_roundtrip_weekday(weekday: Day) -> None:
    """Every day of the week survives the frame's Sunday-first numbering."""
    clock = DaikinAcClock(time_of_day=time(23, 59), weekday=weekday)

    result = DaikinAcCommand.from_raw_timings(
        DaikinAcCommand(state=_COOL_25, clock=clock, comfort=_BRIGHT).get_raw_timings()
    )

    assert result is not None
    assert result.clock == clock


def test_decode_esphome_state_frame() -> None:
    """A frame from ESPHome's encoder, which leaves the remote's fixed bits clear."""
    frame = _with_checksum("11 da 27 00 00 31 30 00 a0 00 00 06 60 00 00 c0 00 00")

    assert _decode_state(frame) == DaikinAcState(
        mode=DaikinAcMode.COOL, temperature=24, weekly_timer=True
    )


def test_default_modulation() -> None:
    """The command defaults to 38 kHz and sends a single transmission."""
    cmd = DaikinAcCommand(state=_COOL_25, comfort=_BRIGHT, clock=_CLOCK_UNSET)

    assert cmd.modulation == 38000
    assert cmd.repeat_count == 0


def test_temperature_limits() -> None:
    """Pin the setpoint limits, the lowest and highest any remote captured sends."""
    assert (MIN_TEMPERATURE, MAX_TEMPERATURE) == (10, 32)


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(
            DaikinAcState(mode=DaikinAcMode.COOL, temperature=10), id="cool_10"
        ),
        pytest.param(
            DaikinAcState(mode=DaikinAcMode.HEAT, temperature=32), id="heat_32"
        ),
    ],
)
def test_limits_apply_to_every_mode(state: DaikinAcState) -> None:
    """Any mode encodes the whole range: narrowing it per mode is up to the caller."""
    frames = _extract_frames(
        DaikinAcCommand(
            state=state, comfort=_BRIGHT, clock=_CLOCK_UNSET
        ).get_raw_timings()
    )

    assert _decode_state(frames[2]) == state


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        pytest.param(
            {"mode": DaikinAcMode.HEAT, "temperature": 9.5},
            "out of range",
            id="below_minimum",
        ),
        pytest.param(
            {"mode": DaikinAcMode.COOL, "temperature": 32.5},
            "out of range",
            id="above_maximum",
        ),
        pytest.param(
            {"mode": DaikinAcMode.COOL, "temperature": 24.25},
            "not a multiple",
            id="quarter_degree",
        ),
        pytest.param(
            {"mode": DaikinAcMode.COOL, "temperature": None},
            "needs a temperature",
            id="cool_without_temperature",
        ),
        pytest.param(
            {"mode": DaikinAcMode.DRY, "temperature": 24},
            "takes no temperature",
            id="dry_with_temperature",
        ),
        pytest.param(
            {"mode": DaikinAcMode.FAN_ONLY, "temperature": 25},
            "takes no temperature",
            id="fan_only_with_temperature",
        ),
        pytest.param(
            {
                "mode": DaikinAcMode.COOL,
                "temperature": 24,
                "powerful": True,
                "econo": True,
            },
            "powerful cannot",
            id="powerful_econo",
        ),
        pytest.param(
            {
                "mode": DaikinAcMode.COOL,
                "temperature": 24,
                "powerful": True,
                "quiet": True,
            },
            "powerful cannot",
            id="powerful_quiet",
        ),
    ],
)
def test_state_rejects_what_the_remote_cannot_send(
    kwargs: dict[str, Any], match: str
) -> None:
    """A state the remote cannot produce is rejected at construction."""
    with pytest.raises(ValueError, match=match):
        DaikinAcState(**kwargs)


def test_corrupted_frame_decodes_once_its_checksum_is_fixed() -> None:
    """Pin that the rejection cases below fail on the field, not on the checksum."""
    frame = _with_checksum("11 da 27 00 00 39 32 00 a0 00 00 06 60 00 00 c1 80 00")

    assert _decode_state(frame) == _COOL_25


@pytest.mark.parametrize(
    "frame",
    [
        pytest.param(
            "11 da 27 00 00 39 32 00 a0 00 00 06 60 00 00 c1 80 00 c5",
            id="bad_checksum",
        ),
        pytest.param(
            _with_checksum("11 da 27 01 00 39 32 00 a0 00 00 06 60 00 00 c1 80 00"),
            id="wrong_address",
        ),
        pytest.param(
            _with_checksum("11 da 27 00 01 39 32 00 a0 00 00 06 60 00 00 c1 80 00"),
            id="unknown_type",
        ),
        pytest.param(
            _with_checksum("11 da 27 00 00 39 32 00 a0 00 00 06 60 00 00 c1 80"),
            id="state_too_short",
        ),
        pytest.param(_with_checksum("11 da 27 00 c5 30 00 00"), id="comfort_too_long"),
        pytest.param(
            _with_checksum("11 da 27 00 00 59 32 00 a0 00 00 06 60 00 00 c1 80 00"),
            id="undefined_mode",
        ),
        pytest.param(
            _with_checksum("11 da 27 00 00 39 32 00 80 00 00 06 60 00 00 c1 80 00"),
            id="undefined_fan",
        ),
        pytest.param(
            _with_checksum("11 da 27 00 00 39 12 00 a0 00 00 06 60 00 00 c1 80 00"),
            id="temperature_below_minimum",
        ),
        pytest.param(
            _with_checksum("11 da 27 00 00 39 32 00 a0 00 00 06 60 01 00 c1 84 00"),
            id="powerful_econo",
        ),
        pytest.param(
            _with_checksum("11 da 27 00 00 3b 32 00 a0 00 a0 05 60 00 00 c1 80 00"),
            id="on_timer_past_midnight",
        ),
        pytest.param(
            _with_checksum("11 da 27 00 00 3d 32 00 a0 00 00 06 5a 00 00 c1 80 00"),
            id="off_timer_past_midnight",
        ),
        pytest.param(_with_checksum("11 da 27 00 c5 00 00"), id="brightness_zero"),
        pytest.param(_with_checksum("11 da 27 00 42 49 05"), id="clock_day_zero"),
        pytest.param(_with_checksum("11 da 27 00 42 a0 15"), id="clock_past_midnight"),
    ],
)
def test_decode_returns_none_for_invalid_frame(frame: str) -> None:
    """A broken checksum or header, or a value no remote sends, is rejected."""
    assert DaikinAcCommand.from_raw_timings(_frame_timings(frame)) is None
