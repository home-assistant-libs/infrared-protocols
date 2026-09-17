"""Gree air-conditioner IR protocol.

A 9000/4500 leader, 562 marks, and 562 and 1687 spaces. Remotes vary around these
values, so the decoder matches bits with a window wide enough to also take a 620
mark and 540/1600 spaces.

A command is a single frame built from two bit blocks separated by a long space:

  leader + block A (35 data bits) + end pulse + ~20100 us space
         + block B (32 data bits) + end pulse

Block A carries the full state; block B carries the swing detail and the checksum.

Bits are sent least-significant first within each field; index 0 below is the first
transmitted bit.

Block A (35 bits):
  bits 0-2:   mode
  bit 3:      power
  bits 4-5:   fan speed
  bit 6:      swing (set while either axis is actually swinging)
  bit 7:      sleep
  bits 8-11:  temperature (temp_c - 16)
  bits 12-19: timer (half hour at 12, hour tens at 13-14, enabled at 15,
              hour units at 16-19; the hour is split into decimal digits)
  bit 20:     turbo
  bit 21:     display light
  bit 22:     anion
  bit 23:     blow
  bits 24-25: air (fresh-air intake; the fourth value is undefined)
  bits 28,30,33: fixed trailer

Block B (32 bits):
  bit 0:      vertical swing
  bit 4:      horizontal swing
  bit 13:     fixed signature
  bits 28-31: checksum

Block A's bit 6 records whether anything is swinging; block B's bits 0 and 4 say which
axis. Block B's bits latch: they keep the last selected axis after swing is switched
off, so they only describe live movement while block A's bit 6 is set. The checksum is
computed over block B's latched horizontal bit rather than the effective state.

Only part of the state enters the checksum, so many fields do not affect it; see
``_checksum``.
"""

from enum import IntEnum
from typing import Self, override

from . import Command

MIN_TEMP = 16
MAX_TEMP = 30

_TEMP_OFFSET = 16

_MAX_TIMER_HOURS = 24

_LEADER_MARK = 9000
_LEADER_SPACE = 4500
_BIT_MARK = 562
_BIT_ONE_SPACE = 1687
_BIT_ZERO_SPACE = 562

# Long mid-frame space after block A, and the trailing space after block B.
_FRAME_GAP = 20100

_FRAME_A_BITS = 35
_FRAME_B_BITS = 32

_TOLERANCE = 0.35
# Marks are stretched by receiver AGC far more than spaces, so bit timing is matched
# with an absolute window that keeps a zero and a one space apart (562 vs 1687). The
# window is also wide enough to decode remotes emitting a 620 mark and 540/1600
# spaces.
_BIT_TOLERANCE = 350

# Block A field positions (bit index, width), LSB-first within the field.
_A_MODE = (0, 3)
_A_POWER = 3
_A_FAN = (4, 2)
_A_SWING = 6
_A_SLEEP = 7
_A_TEMP = (8, 4)
_A_TIMER_HALF = 12
_A_TIMER_TENS = (13, 2)
_A_TIMER_ENABLED = 15
_A_TIMER_UNITS = (16, 4)
_A_TURBO = 20
_A_DISPLAY = 21
_A_ANION = 22
_A_BLOW = 23
_A_AIR = (24, 2)
_A_TRAILER = (28, 30, 33)

# Block B field positions.
_B_SWING_V = 0
_B_SWING_H = 4
_B_SIGNATURE = 13
_B_CHECKSUM = (28, 4)

# The checksum starts from a fixed base rather than zero.
_CHECKSUM_BASE = 10


class GreeAcMode(IntEnum):
    """AC operating mode; value is the mode field at block A bits 0-2."""

    AUTO = 0
    COOL = 1
    DRY = 2
    FAN_ONLY = 3
    HEAT = 4


class GreeAcFanSpeed(IntEnum):
    """Fan speed; value is the fan field at block A bits 4-5."""

    AUTO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class GreeAcAir(IntEnum):
    """Fresh-air intake; value is the air field at block A bits 24-25.

    The field's fourth value is not produced by the remote and has no known
    meaning, so it is rejected when decoding.
    """

    OFF = 0
    LEVEL_1 = 1
    LEVEL_2 = 2


def _get_field(bits: list[int], start: int, width: int) -> int:
    """Read a LSB-first field of the given width from a bit list."""
    return sum(bits[start + i] << i for i in range(width))


def _set_field(bits: list[int], start: int, width: int, value: int) -> None:
    """Write a LSB-first field of the given width into a bit list."""
    for i in range(width):
        bits[start + i] = (value >> i) & 1


def _pack_timer(bits: list[int], hours: float | None) -> None:
    """Write a timer setting into block A bits 12-19; an off timer leaves them zero."""
    if hours is None:
        return
    whole_hours, half = divmod(round(hours * 2), 2)
    tens, units = divmod(whole_hours, 10)
    bits[_A_TIMER_HALF] = half
    _set_field(bits, *_A_TIMER_TENS, tens)
    bits[_A_TIMER_ENABLED] = 1
    _set_field(bits, *_A_TIMER_UNITS, units)


def _unpack_timer(bits: list[int]) -> float | None:
    """Read the timer from block A bits 12-19, or None when it is off.

    Raises ValueError for a digit or duration the remote cannot produce, so the
    decoder rejects the frame alongside the undefined enum values.
    """
    half = bits[_A_TIMER_HALF]
    tens = _get_field(bits, *_A_TIMER_TENS)
    units = _get_field(bits, *_A_TIMER_UNITS)

    if not bits[_A_TIMER_ENABLED]:
        # The remote zeroes the whole field when the timer is off.
        if half or tens or units:
            raise ValueError("timer bits set while the timer is off")
        return None

    hours = tens * 10 + units + 0.5 * half
    if units > 9 or hours > _MAX_TIMER_HOURS:
        raise ValueError(f"timer {hours} out of range 0..{_MAX_TIMER_HOURS}")
    return hours


def _checksum(frame_a: list[int], frame_b: list[int]) -> int:
    """Return the block B checksum nibble for the two blocks as sent.

    The state is eight bytes, block A's 32 data bits followed by block B's. The sum
    takes the low nibble of the first four and the high nibble of the next three, so
    half of the state stays outside it: mode, power, temperature, the timer hour
    units, air and horizontal swing enter, while sleep, the rest of the timer, turbo,
    display, anion, blow and vertical swing do not.
    """
    total = _CHECKSUM_BASE
    total += sum(_get_field(frame_a, 8 * i, 4) for i in range(4))
    total += sum(_get_field(frame_b, 8 * i + 4, 4) for i in range(3))
    return total & 0xF


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


def _encode_frame(bits: list[int], *, leader: bool) -> list[int]:
    """Encode a bit list into raw timings, with or without the leader."""
    timings: list[int] = [_LEADER_MARK, -_LEADER_SPACE] if leader else []
    for bit in bits:
        timings.append(_BIT_MARK)
        timings.append(-(_BIT_ONE_SPACE if bit else _BIT_ZERO_SPACE))
    timings.append(_BIT_MARK)
    return timings


def _decode_bits(timings: list[int], offset: int, count: int) -> list[int] | None:
    """Decode ``count`` bits starting at ``offset``, or None on any bad bit."""
    bits: list[int] = []
    for i in range(count):
        bit = _decode_bit(timings[offset + 2 * i], abs(timings[offset + 2 * i + 1]))
        if bit is None:
            return None
        bits.append(bit)
    return bits


class GreeAcCommand(Command):
    """Gree air-conditioner IR command.

    ``temperature`` is in whole degrees celsius, 16 to 30.

    ``timer_hours`` is the countdown the remote is set to, 0 to 24 in half-hour
    steps, or None when the timer is off.
    """

    power: bool
    mode: GreeAcMode
    temperature: int
    fan: GreeAcFanSpeed
    swing_v: bool
    swing_h: bool
    turbo: bool
    display: bool
    blow: bool
    sleep: bool
    timer_hours: float | None
    anion: bool
    air: GreeAcAir

    def __init__(
        self,
        *,
        power: bool = True,
        mode: GreeAcMode,
        temperature: int,
        fan: GreeAcFanSpeed = GreeAcFanSpeed.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        turbo: bool = False,
        display: bool = True,
        blow: bool = False,
        sleep: bool = False,
        timer_hours: float | None = None,
        anion: bool = False,
        air: GreeAcAir = GreeAcAir.OFF,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Gree AC IR command."""
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
        self.swing_h = swing_h
        self.turbo = turbo
        self.display = display
        self.blow = blow
        self.sleep = sleep
        self.timer_hours = timer_hours
        self.anion = anion
        self.air = air

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Gree AC command."""
        frame_a = [0] * _FRAME_A_BITS
        _set_field(frame_a, *_A_MODE, self.mode.value)
        frame_a[_A_POWER] = int(self.power)
        _set_field(frame_a, *_A_FAN, self.fan.value)
        frame_a[_A_SWING] = int(self.swing_v or self.swing_h)
        frame_a[_A_SLEEP] = int(self.sleep)
        _set_field(frame_a, *_A_TEMP, self.temperature - _TEMP_OFFSET)
        _pack_timer(frame_a, self.timer_hours)
        frame_a[_A_TURBO] = int(self.turbo)
        frame_a[_A_DISPLAY] = int(self.display)
        frame_a[_A_ANION] = int(self.anion)
        frame_a[_A_BLOW] = int(self.blow)
        _set_field(frame_a, *_A_AIR, self.air.value)
        for index in _A_TRAILER:
            frame_a[index] = 1

        frame_b = [0] * _FRAME_B_BITS
        frame_b[_B_SWING_V] = int(self.swing_v)
        frame_b[_B_SWING_H] = int(self.swing_h)
        frame_b[_B_SIGNATURE] = 1
        _set_field(frame_b, *_B_CHECKSUM, _checksum(frame_a, frame_b))

        timings = _encode_frame(frame_a, leader=True)
        timings.append(-_FRAME_GAP)
        timings.extend(_encode_frame(frame_b, leader=False))
        timings.append(-_FRAME_GAP)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a GreeAcCommand.

        Expects block A followed by block B, as ``get_raw_timings`` emits them.
        Returns a GreeAcCommand if the timings match, or None otherwise.
        """
        # Block A: leader (2) + 35 bit pairs (70) + end mark (1).
        frame_a_len = 2 + 2 * _FRAME_A_BITS + 1
        # Then the mid-frame gap (1), then block B: 32 bit pairs (64) + end mark (1).
        if len(timings) < frame_a_len + 1 + 2 * _FRAME_B_BITS + 1:
            return None

        if not _is_close(timings[0], _LEADER_MARK, _TOLERANCE) or not _is_close(
            abs(timings[1]), _LEADER_SPACE, _TOLERANCE
        ):
            return None

        frame_a = _decode_bits(timings, 2, _FRAME_A_BITS)
        if frame_a is None:
            return None
        if abs(timings[2 + 2 * _FRAME_A_BITS] - _BIT_MARK) > _BIT_TOLERANCE:
            return None

        # The mid-frame gap is a space, so it must be negative as well as long.
        if timings[frame_a_len] >= 0 or not _is_close(
            abs(timings[frame_a_len]), _FRAME_GAP, _TOLERANCE
        ):
            return None

        frame_b_start = frame_a_len + 1
        frame_b = _decode_bits(timings, frame_b_start, _FRAME_B_BITS)
        if frame_b is None:
            return None
        if abs(timings[frame_b_start + 2 * _FRAME_B_BITS] - _BIT_MARK) > _BIT_TOLERANCE:
            return None

        for index in _A_TRAILER:
            if frame_a[index] != 1:
                return None
        if frame_b[_B_SIGNATURE] != 1:
            return None

        # The checksum is computed over the frames as sent, so over block B's latched
        # horizontal bit rather than the effective swing state.
        if _get_field(frame_b, *_B_CHECKSUM) != _checksum(frame_a, frame_b):
            return None

        # The mode, fan, air and timer fields are wider than the values the protocol
        # defines.
        try:
            mode = GreeAcMode(_get_field(frame_a, *_A_MODE))
            fan = GreeAcFanSpeed(_get_field(frame_a, *_A_FAN))
            air = GreeAcAir(_get_field(frame_a, *_A_AIR))
            timer_hours = _unpack_timer(frame_a)
        except ValueError:
            return None

        temperature = _get_field(frame_a, *_A_TEMP) + _TEMP_OFFSET
        if not MIN_TEMP <= temperature <= MAX_TEMP:
            return None

        power = bool(frame_a[_A_POWER])
        # Block B's two bits latch the axis last selected and keep that value after
        # swing is switched off, so block A's bit is what says whether anything is
        # actually swinging. Turning one axis off while both ran sends block A's bit
        # clear with the other axis still set in block B.
        swinging = bool(frame_a[_A_SWING])
        swing_v = swinging and bool(frame_b[_B_SWING_V])
        swing_h = swinging and bool(frame_b[_B_SWING_H])

        return cls(
            power=power,
            mode=mode,
            temperature=temperature,
            fan=fan,
            swing_v=swing_v,
            swing_h=swing_h,
            turbo=bool(frame_a[_A_TURBO]),
            display=bool(frame_a[_A_DISPLAY]),
            blow=bool(frame_a[_A_BLOW]),
            sleep=bool(frame_a[_A_SLEEP]),
            timer_hours=timer_hours,
            anion=bool(frame_a[_A_ANION]),
            air=air,
        )
