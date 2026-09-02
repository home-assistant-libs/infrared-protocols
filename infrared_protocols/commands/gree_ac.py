"""Gree air-conditioner IR protocol, Sinclair timing variant.

Frame layout (35 bits, LSB first):
  bits 0-2:   mode
  bit 3:      power
  bits 4-5:   fan speed
  bit 6:      vertical swing
  bit 7:      sleep
  bits 8-11:  temperature field (temp_c - 16)
  bits 12-19: timer (half hour at 12, hour tens at 13-14, enabled at 15,
              hour units at 16-19; the hour is split into decimal digits)
  bit 20:     humidity
  bit 21:     light
  bit 22:     anion
  bit 23:     save
  bits 24-25: air (fresh-air intake; the fourth value is undefined)
  bits 26-34: 0x94 signature

The signature is constant across every frame and is what identifies a Sinclair
frame when decoding.
"""

from enum import IntEnum
from typing import Self, override

from . import Command

MIN_TEMP = 16
MAX_TEMP = 30

_TEMP_OFFSET = MIN_TEMP

_MAX_TIMER_HOURS = 24

_HDR_MARK = 9000
_HDR_SPACE = 4500

_BIT_MARK = 560
_BIT_ONE_SPACE = 1690
_BIT_ZERO_SPACE = 560

# IR receivers distort marks (AGC) but keep spaces accurate.
_MARK_TOLERANCE = 0.7
_SPACE_TOLERANCE = 0.25

# A receiver skews a bit's mark and space by roughly a fixed number of microseconds
# rather than a fixed proportion, so bits get an absolute tolerance. It covers the skew
# seen in practice and still keeps the zero and one spaces apart (210-910 vs 1340-2040).
_BIT_TOLERANCE = 350

# A Sinclair frame carries 35 bits: 32 data bits (4 bytes) plus a 3-bit tail.
_BITS = 35
# Required entries: header pair (2) + 35 bit pairs (70) + end mark (1).
_FRAME_LENGTH = 2 + 2 * _BITS + 1

_SIGNATURE = 0x94
_SIGNATURE_SHIFT = 26
_SIGNATURE_MASK = 0x1FF


class GreeAcMode(IntEnum):
    """AC operating mode; value is the mode field at frame bits 0-2."""

    AUTO = 0x00
    COOL = 0x01
    DRY = 0x02
    FAN_ONLY = 0x03
    HEAT = 0x04


class GreeAcFanSpeed(IntEnum):
    """Fan speed; value is the protocol field at frame bits 4-5."""

    AUTO = 0x00
    LOW = 0x01
    MEDIUM = 0x02
    HIGH = 0x03


class GreeAcAir(IntEnum):
    """Fresh-air intake; value is the protocol field at frame bits 24-25.

    The field's fourth value is not produced by the remote and has no known
    meaning, so it is rejected when decoding.
    """

    OFF = 0x00
    LEVEL_1 = 0x01
    LEVEL_2 = 0x02


def _is_close(actual: int, expected: int, tolerance: float) -> bool:
    """Check if a timing is within the given relative tolerance of the expected."""
    margin = expected * tolerance
    return expected - margin <= actual <= expected + margin


def _decode_bit(mark: int, space: int) -> int | None:
    """Decode one bit from its mark and space, or None if it matches neither."""
    if abs(mark - _BIT_MARK) > _BIT_TOLERANCE:
        return None
    if abs(space - _BIT_ZERO_SPACE) <= _BIT_TOLERANCE:
        return 0
    if abs(space - _BIT_ONE_SPACE) <= _BIT_TOLERANCE:
        return 1
    return None


def _pack_timer(hours: float | None) -> int:
    """Pack a timer setting into frame bits 12-19, or 0 when it is off."""
    if hours is None:
        return 0
    whole_hours, half = divmod(round(hours * 2), 2)
    tens, units = divmod(whole_hours, 10)
    return (half << 12) | (tens << 13) | (1 << 15) | (units << 16)


def _unpack_timer(frame: int) -> float | None:
    """Read the timer from frame bits 12-19, or None when it is off.

    Raises ValueError for a digit or duration the remote cannot produce, so the
    decoder rejects the frame alongside the undefined enum values.
    """
    if not (frame >> 15) & 1:
        # The remote zeroes the whole field when the timer is off.
        if (frame >> 12) & 0xFF:
            raise ValueError("timer bits set while the timer is off")
        return None

    tens = (frame >> 13) & 0x03
    units = (frame >> 16) & 0x0F
    hours = tens * 10 + units + 0.5 * ((frame >> 12) & 1)
    if tens > 2 or units > 9 or hours > _MAX_TIMER_HOURS:
        raise ValueError(f"timer {hours} out of range 0..{_MAX_TIMER_HOURS}")
    return hours


def _encode_frame(value: int) -> list[int]:
    """Encode a 35-bit frame value as raw timings, LSB first."""
    timings: list[int] = [_HDR_MARK, -_HDR_SPACE]
    for i in range(_BITS):
        bit = (value >> i) & 1
        timings.append(_BIT_MARK)
        timings.append(-(_BIT_ONE_SPACE if bit else _BIT_ZERO_SPACE))
    timings.append(_BIT_MARK)
    return timings


def _decode_frame(timings: list[int]) -> int | None:
    """Decode raw IR timings into a validated 35-bit Sinclair frame.

    Timings after the end mark are ignored.
    """
    if len(timings) < _FRAME_LENGTH:
        return None

    if not _is_close(timings[0], _HDR_MARK, _MARK_TOLERANCE) or not _is_close(
        -timings[1], _HDR_SPACE, _SPACE_TOLERANCE
    ):
        return None

    frame = 0
    for i in range(_BITS):
        # Negating the space entry makes a wrongly signed timing fail the bit check.
        bit = _decode_bit(timings[2 + 2 * i], -timings[3 + 2 * i])
        if bit is None:
            return None
        frame |= bit << i

    if abs(timings[2 + 2 * _BITS] - _BIT_MARK) > _BIT_TOLERANCE:
        return None

    if (frame >> _SIGNATURE_SHIFT) & _SIGNATURE_MASK != _SIGNATURE:
        return None

    return frame


class GreeAcSinclairCommand(Command):
    """Gree air-conditioner IR command, Sinclair timing variant.

    Encodes the full AC state into a 35-bit frame carrying mode, power, fan
    speed, swing, sleep, temperature, timer, humidity, light, anion, save and
    air, followed by a constant signature. Every field is preserved on a
    decode/encode round trip.

    ``temperature`` is in whole degrees celsius, 16 to 30.
    """

    power: bool
    mode: GreeAcMode
    temperature: int
    fan: GreeAcFanSpeed
    swing_v: bool
    sleep: bool
    timer_hours: float | None
    humidity: bool
    light: bool
    anion: bool
    save: bool
    air: GreeAcAir

    def __init__(
        self,
        *,
        power: bool = True,
        mode: GreeAcMode,
        temperature: int,
        fan: GreeAcFanSpeed = GreeAcFanSpeed.AUTO,
        swing_v: bool = False,
        sleep: bool = False,
        timer_hours: float | None = None,
        humidity: bool = False,
        light: bool = False,
        anion: bool = False,
        save: bool = False,
        air: GreeAcAir = GreeAcAir.OFF,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Gree AC Sinclair command."""
        super().__init__(modulation=modulation)

        if not MIN_TEMP <= temperature <= MAX_TEMP:
            raise ValueError(
                f"temperature {temperature} out of range {MIN_TEMP}..{MAX_TEMP}"
            )
        if timer_hours is not None:
            if not 0 <= timer_hours <= _MAX_TIMER_HOURS:
                raise ValueError(
                    f"timer_hours {timer_hours} out of range 0..{_MAX_TIMER_HOURS}"
                )
            if (timer_hours * 2) % 1:
                raise ValueError(f"timer_hours {timer_hours} is not a multiple of 0.5")

        self.power = power
        self.mode = mode
        self.temperature = temperature
        self.fan = fan
        self.swing_v = swing_v
        self.sleep = sleep
        self.timer_hours = timer_hours
        self.humidity = humidity
        self.light = light
        self.anion = anion
        self.save = save
        self.air = air

    def _frame_value(self) -> int:
        """Pack the AC state into the 35-bit Sinclair frame value (LSB-0)."""
        return (
            self.mode.value
            | (int(self.power) << 3)
            | (self.fan.value << 4)
            | (int(self.swing_v) << 6)
            | (int(self.sleep) << 7)
            | ((self.temperature - _TEMP_OFFSET) << 8)
            | _pack_timer(self.timer_hours)
            | (int(self.humidity) << 20)
            | (int(self.light) << 21)
            | (int(self.anion) << 22)
            | (int(self.save) << 23)
            | (self.air.value << 24)
            | (_SIGNATURE << _SIGNATURE_SHIFT)
        )

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Gree AC Sinclair command.

        Sinclair timing (in microseconds):
        - Header pulse: 9000µs high, 4500µs low
        - Logical '0': 560µs high, 560µs low
        - Logical '1': 560µs high, 1690µs low
        - 35-bit frame value (LSB-0), see the module docstring
        - End mark: 560µs high
        """
        return _encode_frame(self._frame_value())

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a GreeAcSinclairCommand.

        Returns a GreeAcSinclairCommand if the timings match a Sinclair frame,
        or None otherwise. Every field is recovered so the command re-encodes to
        the same frame.
        """
        frame = _decode_frame(timings)
        if frame is None:
            return None

        # The 4-bit field can only overshoot the range, never undershoot it.
        temperature = ((frame >> 8) & 0x0F) + _TEMP_OFFSET
        if temperature > MAX_TEMP:
            return None

        # The mode, air and timer fields are wider than the values the protocol
        # defines.
        try:
            mode = GreeAcMode(frame & 0x07)
            fan = GreeAcFanSpeed((frame >> 4) & 0x03)
            air = GreeAcAir((frame >> 24) & 0x03)
            timer_hours = _unpack_timer(frame)
        except ValueError:
            return None

        return cls(
            power=bool(frame & (1 << 3)),
            mode=mode,
            temperature=temperature,
            fan=fan,
            swing_v=bool(frame & (1 << 6)),
            sleep=bool(frame & (1 << 7)),
            timer_hours=timer_hours,
            humidity=bool(frame & (1 << 20)),
            light=bool(frame & (1 << 21)),
            anion=bool(frame & (1 << 22)),
            save=bool(frame & (1 << 23)),
            air=air,
        )
