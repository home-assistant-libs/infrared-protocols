"""Daikin air-conditioner IR protocol, as sent by ARC43x and ARC466 remotes.

Carried over the AEHA physical layer. A transmission is a wake-up burst followed by
three frames, each closed by a long gap:

  wake-up:  five zero bits with no leader
  frame 1:  8 bytes, type 0xC5: comfort and display brightness
  frame 2:  8 bytes, type 0x42: the remote's clock
  frame 3:  19 bytes, type 0x00: the unit state

Every frame opens with 0x11 0xDA 0x27 0x00, carries its type in byte 4 and ends with a
checksum, the low byte of the sum of the bytes before it.

Frame 1:
  byte 5:  display brightness << 4
  byte 6:  comfort << 4

Frame 2:
  bytes 5-6:  minutes past midnight in bits 0-10 and the day of the week in bits
              11-13, counting from Sunday as 1

Frame 3:
  byte 5:       mode << 4 | 0x08 | off timer << 2 | on timer << 1 | power
  byte 6:       temperature * 2, or 0xC0 in dry and 0x32 in fan only
  byte 8:       fan << 4 | vertical swing
  byte 9:       horizontal swing
  bytes 10-12:  on time then off time, 12 bits each in minutes past midnight, 0x600
                while that timer is unset
  byte 13:      quiet << 5 | powerful
  byte 15:      0xC1
  byte 16:      weekly timer off << 7 | econo << 2 | sensor << 1

A swinging axis sets its whole nibble. Bits not listed are clear on every remote
captured; the encoder sends them as the remotes do and the decoder ignores them, so
frames from encoders that clear byte 5 bit 3 or send 0xC0 in byte 15 still decode.

The gap between frames, around 30 ms, is longer than many receivers wait before ending
a capture (ESPHome waits 10 ms by default), so each frame often arrives as a signal of
its own. :meth:`DaikinAcFrames.from_raw_timings` decodes whatever frames a signal
holds, leaving the parts it did not carry as None.
"""

from calendar import Day
from dataclasses import dataclass
from datetime import time
from enum import IntEnum
from typing import ClassVar, Self, override

from . import Command
from .aeha import AehaCommand, AehaTiming


class DaikinAcMode(IntEnum):
    """AC operating mode; value is the mode field at state byte 5 bits 4-6."""

    AUTO = 0
    DRY = 2
    COOL = 3
    HEAT = 4
    FAN_ONLY = 6


class DaikinAcFanSpeed(IntEnum):
    """Fan speed; value is the fan field at state byte 8 bits 4-7."""

    LEVEL_1 = 3
    LEVEL_2 = 4
    LEVEL_3 = 5
    LEVEL_4 = 6
    LEVEL_5 = 7
    AUTO = 0xA
    SILENT = 0xB


class DaikinAcBrightness(IntEnum):
    """Indoor unit display brightness; value is the field at comfort byte 5 bits 4-5."""

    BRIGHT = 1
    DIM = 2
    OFF = 3


# Setpoint limits in degrees Celsius
MIN_TEMP = 10.0
MAX_TEMP = 32.0

_FIXED_TEMPERATURE: dict[DaikinAcMode, int] = {
    DaikinAcMode.DRY: 0xC0,
    DaikinAcMode.FAN_ONLY: 0x32,
}

# Nominal AEHA, except for 30ms gap after the wake-up burst and each frame
_DAIKIN_TIMING = AehaTiming(trailer_space=32300)

_WAKE_UP_BITS = 5

# Common
_ADDRESS = (0x11, 0xDA, 0x27, 0x00)
_TYPE_BYTE = 4

# Comfort frame
_COMFORT_TYPE = 0xC5
_COMFORT_LENGTH = 8
_BRIGHTNESS_BYTE = 5
_COMFORT_BYTE = 6

# Clock frame
_CLOCK_TYPE = 0x42
_CLOCK_LENGTH = 8
_CLOCK_BYTE = 5
_CLOCK_MINUTES_MASK = 0x7FF
_CLOCK_DAY_SHIFT = 11
_CLOCK_DAY_MASK = 0x7

# State frame
_STATE_TYPE = 0x00
_STATE_LENGTH = 19
_MODE_BYTE = 5
_MODE_BYTE_BASE = 0x08
_TEMPERATURE_BYTE = 6
_FAN_BYTE = 8
_SWING_H_BYTE = 9
_TIMER_BYTE = 10
_PRESET_BYTE = 13
_FIXED_BYTE = 15
_FIXED_BYTE_VALUE = 0xC1
_FLAGS_BYTE = 16
_POWER_BIT = 0x01
_ON_TIMER_BIT = 0x02
_OFF_TIMER_BIT = 0x04
_POWERFUL_BIT = 0x01
_QUIET_BIT = 0x20
_SENSOR_BIT = 0x02
_ECONO_BIT = 0x04
_WEEKLY_TIMER_OFF_BIT = 0x80
_SWING_ON = 0xF

_TIMER_UNSET = 0x600
_MINUTES_PER_DAY = 24 * 60


def _checksum(message: list[int]) -> int:
    """Return the checksum of a frame: the low byte of the sum of its other bytes."""
    return sum(message[:-1]) & 0xFF


def _minutes(value: time) -> int:
    """Return the minutes past midnight a time of day is sent as."""
    return value.hour * 60 + value.minute


def _time(minutes: int) -> time | None:
    """Return the time of day a minute count stands for, or None past the day's end."""
    if minutes >= _MINUTES_PER_DAY:
        return None
    return time(*divmod(minutes, 60))


@dataclass(frozen=True, slots=True, kw_only=True)
class DaikinAcState:
    """The unit state carried by frame 3 including mode.

    Includes mode, temperature, presets and the daily timers.
    """

    power: bool = True
    mode: DaikinAcMode
    temperature: float | None
    fan: DaikinAcFanSpeed = DaikinAcFanSpeed.AUTO
    swing_v: bool = False
    swing_h: bool = False
    powerful: bool = False
    econo: bool = False
    quiet: bool = False
    sensor: bool = False
    on_timer: time | None = None
    off_timer: time | None = None
    weekly_timer: bool = False

    def __post_init__(self) -> None:
        """Reject a state the remote cannot send."""
        if self.mode in _FIXED_TEMPERATURE:
            if self.temperature is not None:
                raise ValueError(f"{self.mode.name} mode takes no temperature")
        else:
            if self.temperature is None:
                raise ValueError(f"{self.mode.name} mode needs a temperature")
            if not MIN_TEMP <= self.temperature <= MAX_TEMP:
                raise ValueError(
                    f"temperature {self.temperature} out of range "
                    f"{MIN_TEMP}..{MAX_TEMP}"
                )
            if (self.temperature * 2) % 1:
                raise ValueError(
                    f"temperature {self.temperature} is not a multiple of 0.5"
                )
        if self.powerful and (self.econo or self.quiet):
            raise ValueError("powerful cannot be combined with econo or quiet")


@dataclass(frozen=True, slots=True, kw_only=True)
class DaikinAcComfort:
    """The settings carried by frame 1: comfort airflow and display brightness.

    ``brightness`` is None when the frame carries 0 there, as ESPHome sends.
    """

    comfort: bool = False
    brightness: DaikinAcBrightness | None = DaikinAcBrightness.BRIGHT


@dataclass(frozen=True, slots=True, kw_only=True)
class DaikinAcClock:
    """The remote's clock, carried by frame 2, which the unit's timers run against.

    Only the hour and minute of ``time_of_day`` are sent. The default is what a remote
    whose clock was never set sends.
    """

    time_of_day: time = time(0, 0)
    weekday: Day = Day.MONDAY


# What a remote sends out of the box
_DEFAULT_COMFORT = DaikinAcComfort()
_DEFAULT_CLOCK = DaikinAcClock()


def _frame(frame_type: int, length: int) -> list[int]:
    """Return a frame of the given type and length, zeroed past its header."""
    message = [0] * length
    message[: len(_ADDRESS)] = _ADDRESS
    message[_TYPE_BYTE] = frame_type
    return message


def _comfort_message(comfort: DaikinAcComfort) -> bytes:
    """Build frame 1 from the comfort settings."""
    message = _frame(_COMFORT_TYPE, _COMFORT_LENGTH)
    if comfort.brightness is not None:
        message[_BRIGHTNESS_BYTE] = comfort.brightness << 4
    message[_COMFORT_BYTE] = comfort.comfort << 4
    message[-1] = _checksum(message)
    return bytes(message)


def _clock_message(clock: DaikinAcClock) -> bytes:
    """Build frame 2 from the clock."""
    message = _frame(_CLOCK_TYPE, _CLOCK_LENGTH)
    # Day counts Monday as 0; the frame counts Sunday as 1.
    day = (clock.weekday + 1) % 7 + 1
    value = _minutes(clock.time_of_day) | day << _CLOCK_DAY_SHIFT
    message[_CLOCK_BYTE] = value & 0xFF
    message[_CLOCK_BYTE + 1] = value >> 8
    message[-1] = _checksum(message)
    return bytes(message)


def _state_message(state: DaikinAcState) -> bytes:
    """Build frame 3 from the unit state."""
    message = _frame(_STATE_TYPE, _STATE_LENGTH)
    message[_MODE_BYTE] = (
        state.mode << 4
        | _MODE_BYTE_BASE
        | (_POWER_BIT if state.power else 0)
        | (_ON_TIMER_BIT if state.on_timer is not None else 0)
        | (_OFF_TIMER_BIT if state.off_timer is not None else 0)
    )
    if state.temperature is None:
        message[_TEMPERATURE_BYTE] = _FIXED_TEMPERATURE[state.mode]
    else:
        message[_TEMPERATURE_BYTE] = round(state.temperature * 2)
    message[_FAN_BYTE] = state.fan << 4 | (_SWING_ON if state.swing_v else 0)
    message[_SWING_H_BYTE] = _SWING_ON if state.swing_h else 0

    on_time = _TIMER_UNSET if state.on_timer is None else _minutes(state.on_timer)
    off_time = _TIMER_UNSET if state.off_timer is None else _minutes(state.off_timer)
    message[_TIMER_BYTE] = on_time & 0xFF
    message[_TIMER_BYTE + 1] = on_time >> 8 | (off_time & 0xF) << 4
    message[_TIMER_BYTE + 2] = off_time >> 4

    message[_PRESET_BYTE] = (_POWERFUL_BIT if state.powerful else 0) | (
        _QUIET_BIT if state.quiet else 0
    )
    message[_FIXED_BYTE] = _FIXED_BYTE_VALUE
    message[_FLAGS_BYTE] = (
        (0 if state.weekly_timer else _WEEKLY_TIMER_OFF_BIT)
        | (_ECONO_BIT if state.econo else 0)
        | (_SENSOR_BIT if state.sensor else 0)
    )
    message[-1] = _checksum(message)
    return bytes(message)


def _decode_comfort(message: list[int]) -> DaikinAcComfort:
    """Decode frame 1."""
    brightness = message[_BRIGHTNESS_BYTE] >> 4 & 0x3
    return DaikinAcComfort(
        comfort=bool(message[_COMFORT_BYTE] >> 4 & 1),
        brightness=DaikinAcBrightness(brightness) if brightness else None,
    )


def _decode_clock(message: list[int]) -> DaikinAcClock | None:
    """Decode frame 2, or None if it carries a time or day no remote sends."""
    value = message[_CLOCK_BYTE] | message[_CLOCK_BYTE + 1] << 8
    time_of_day = _time(value & _CLOCK_MINUTES_MASK)
    day = value >> _CLOCK_DAY_SHIFT & _CLOCK_DAY_MASK
    if time_of_day is None or not 1 <= day <= 7:
        return None
    return DaikinAcClock(time_of_day=time_of_day, weekday=Day((day - 2) % 7))


def _decode_timer(message: list[int], enabled_bit: int, minutes: int) -> time | None:
    """Return a timer's time of day, or None while it is unset.

    Raises ValueError for a set timer past the end of the day, so the decoder rejects
    the frame alongside the undefined enum values.
    """
    if not message[_MODE_BYTE] & enabled_bit:
        return None
    if (value := _time(minutes)) is None:
        raise ValueError(f"timer {minutes} minutes is past the end of the day")
    return value


def _decode_state(message: list[int]) -> DaikinAcState | None:
    """Decode frame 3, or None if it carries a state no remote sends."""
    timers = message[_TIMER_BYTE : _TIMER_BYTE + 3]
    try:
        mode = DaikinAcMode(message[_MODE_BYTE] >> 4 & 0x7)
        fan = DaikinAcFanSpeed(message[_FAN_BYTE] >> 4)
        on_timer = _decode_timer(
            message, _ON_TIMER_BIT, timers[0] | (timers[1] & 0xF) << 8
        )
        off_timer = _decode_timer(
            message, _OFF_TIMER_BIT, timers[1] >> 4 | timers[2] << 4
        )
        return DaikinAcState(
            power=bool(message[_MODE_BYTE] & _POWER_BIT),
            mode=mode,
            temperature=(
                None if mode in _FIXED_TEMPERATURE else message[_TEMPERATURE_BYTE] / 2
            ),
            fan=fan,
            swing_v=bool(message[_FAN_BYTE] & _SWING_ON),
            swing_h=bool(message[_SWING_H_BYTE] & _SWING_ON),
            powerful=bool(message[_PRESET_BYTE] & _POWERFUL_BIT),
            econo=bool(message[_FLAGS_BYTE] & _ECONO_BIT),
            quiet=bool(message[_PRESET_BYTE] & _QUIET_BIT),
            sensor=bool(message[_FLAGS_BYTE] & _SENSOR_BIT),
            on_timer=on_timer,
            off_timer=off_timer,
            weekly_timer=not message[_FLAGS_BYTE] & _WEEKLY_TIMER_OFF_BIT,
        )
    except ValueError:
        return None


class _DaikinAcFrame(AehaCommand):
    """One Daikin frame on the AEHA physical layer."""

    TIMING: ClassVar[AehaTiming] = _DAIKIN_TIMING

    @classmethod
    def decode(cls, timings: list[int]) -> list[int] | None:
        """Decode timings into a frame with the Daikin address and a valid checksum."""
        data = cls._decode_data(timings)
        if data is None or len(data) <= _TYPE_BYTE + 1:
            return None
        message = list(data)
        if tuple(message[: len(_ADDRESS)]) != _ADDRESS:
            return None
        if message[-1] != _checksum(message):
            return None
        return message

    @classmethod
    def wake_up_timings(cls) -> list[int]:
        """Return the raw timings of the wake-up burst."""
        timing = cls.TIMING
        timings: list[int] = []
        for _ in range(_WAKE_UP_BITS):
            timings += [timing.bit_mark, -timing.zero_space]
        timings += [timing.bit_mark, -timing.trailer_space]
        return timings


def _decode_frame(
    timings: list[int],
) -> DaikinAcComfort | DaikinAcClock | DaikinAcState | None:
    """Decode the raw timings of one frame into what it carries.

    Returns None for the wake-up burst, for a frame whose type, length or checksum
    does not match, and for a message no remote sends.
    """
    message = _DaikinAcFrame.decode(timings)
    if message is None:
        return None
    frame = (message[_TYPE_BYTE], len(message))
    if frame == (_COMFORT_TYPE, _COMFORT_LENGTH):
        return _decode_comfort(message)
    if frame == (_CLOCK_TYPE, _CLOCK_LENGTH):
        return _decode_clock(message)
    if frame == (_STATE_TYPE, _STATE_LENGTH):
        return _decode_state(message)
    return None


def _split_frames(timings: list[int]) -> list[list[int]]:
    """Split a capture at every gap long enough to end a frame."""
    frames: list[list[int]] = []
    start = 0
    for index in range(1, len(timings), 2):
        if abs(timings[index]) >= _DAIKIN_TIMING.min_trailer_space:
            frames.append(timings[start : index + 1])
            start = index + 1
    if start < len(timings):
        frames.append(timings[start:])
    return frames


class DaikinAcCommand(Command):
    """Daikin air-conditioner IR command: the wake-up burst and all three frames.

    Every transmission carries the whole state, so a command changing one setting has
    to resend every other one as the unit last had it. The unit ignores a transmission
    missing any frame, so every command sends all three.

    The unit's frames often reach a receiver as separate signals, so decoding is done
    by :class:`DaikinAcFrames` rather than by this command.
    """

    state: DaikinAcState
    comfort: DaikinAcComfort
    clock: DaikinAcClock

    def __init__(
        self,
        *,
        state: DaikinAcState,
        comfort: DaikinAcComfort = _DEFAULT_COMFORT,
        clock: DaikinAcClock = _DEFAULT_CLOCK,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Daikin AC IR command."""
        super().__init__(modulation=modulation)
        self.state = state
        self.comfort = comfort
        self.clock = clock

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Daikin AC command."""
        timings = _DaikinAcFrame.wake_up_timings()
        for message in (
            _comfort_message(self.comfort),
            _clock_message(self.clock),
            _state_message(self.state),
        ):
            timings.extend(_DaikinAcFrame(data=message).get_raw_timings())
        return timings


@dataclass(frozen=True, slots=True, kw_only=True)
class DaikinAcFrames:
    """The frames a received signal carried, each part None when its frame was absent.

    Unlike :class:`DaikinAcCommand`, this cannot be sent: the unit ignores a
    transmission missing any frame.
    """

    state: DaikinAcState | None = None
    comfort: DaikinAcComfort | None = None
    clock: DaikinAcClock | None = None

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into the frames they carry.

        Accepts a single frame or a whole transmission, skipping the wake-up burst and
        anything that is not a Daikin frame. When a frame appears more than once, the
        last one is kept. Returns None when no frame decodes.
        """
        state: DaikinAcState | None = None
        comfort: DaikinAcComfort | None = None
        clock: DaikinAcClock | None = None
        for frame in _split_frames(timings):
            match _decode_frame(frame):
                case DaikinAcState() as decoded:
                    state = decoded
                case DaikinAcComfort() as decoded:
                    comfort = decoded
                case DaikinAcClock() as decoded:
                    clock = decoded
        if state is None and comfort is None and clock is None:
            return None
        return cls(state=state, comfort=comfort, clock=clock)
