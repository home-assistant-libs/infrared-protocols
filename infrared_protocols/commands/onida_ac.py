"""Onida air-conditioner IR protocol.

NEC-family timing (9000/4500 leader, 562 mark, 562/1687 spaces), reverse-engineered
from a physical Onida remote. A command is a single frame built from two bit blocks
separated by a long space:

  leader + block A (35 data bits) + end pulse + ~20100 us space
         + block B (32 data bits) + end pulse

Block A carries the full state; block B carries the swing detail and the checksum.
(An earlier capture with a too-short receiver idle split this into two frames; it is
one frame with a long mid-space.)

Bits are sent least-significant first within each field; index 0 below is the first
transmitted bit.

Block A (35 bits):
  bits 0-2:   mode
  bit 3:      power
  bits 4-5:   fan speed
  bit 6:      swing (set when either vertical or horizontal swing is on)
  bits 8-11:  temperature (temp_c - 16)
  bit 20:     turbo
  bit 21:     display light
  bit 23:     blow
  bits 28,30,33: fixed trailer

Block B (32 bits):
  bit 0:      vertical swing
  bit 4:      horizontal swing
  bit 13:     fixed signature
  bits 28-31: checksum

Block A's bit 6 only records that some swing is on; block B's bits 0 and 4 say which.
"""

from enum import IntEnum
from typing import Self, override

from . import Command

MIN_TEMP = 16
MAX_TEMP = 30

_TEMP_OFFSET = 16

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
# with an absolute window that keeps a zero and a one space apart (562 vs 1687).
_BIT_TOLERANCE = 350

# Block A field positions (bit index, width), LSB-first within the field.
_A_MODE = (0, 3)
_A_POWER = 3
_A_FAN = (4, 2)
_A_SWING = 6
_A_TEMP = (8, 4)
_A_TURBO = 20
_A_DISPLAY = 21
_A_BLOW = 23
_A_TRAILER = (28, 30, 33)

# Block B field positions.
_B_SWING_V = 0
_B_SWING_H = 4
_B_SIGNATURE = 13
_B_CHECKSUM = (28, 4)

# Added into the checksum on top of the state; the contribution of the fixed bits.
_CHECKSUM_CONST = 12


class OnidaAcMode(IntEnum):
    """AC operating mode; value is the mode field at block A bits 0-2."""

    AUTO = 0
    COOL = 1
    DRY = 2
    FAN_ONLY = 3
    HEAT = 4


class OnidaAcFanSpeed(IntEnum):
    """Fan speed; value is the fan field at block A bits 4-5."""

    AUTO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


def _get_field(bits: list[int], start: int, width: int) -> int:
    """Read a LSB-first field of the given width from a bit list."""
    return sum(bits[start + i] << i for i in range(width))


def _set_field(bits: list[int], start: int, width: int, value: int) -> None:
    """Write a LSB-first field of the given width into a bit list."""
    for i in range(width):
        bits[start + i] = (value >> i) & 1


def _checksum(*, mode: int, power: bool, temp: int, swing_h: bool) -> int:
    """Return the block B checksum nibble.

    Vertical swing does not enter the checksum; only horizontal does.
    """
    total = mode + (8 if power else 0) + (temp - _TEMP_OFFSET)
    total += (1 if swing_h else 0) + _CHECKSUM_CONST
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


class OnidaAcCommand(Command):
    """Onida air-conditioner IR command.

    ``temperature`` is in whole degrees celsius, 16 to 30.
    """

    power: bool
    mode: OnidaAcMode
    temperature: int
    fan: OnidaAcFanSpeed
    swing_v: bool
    swing_h: bool
    turbo: bool
    display: bool
    blow: bool

    def __init__(
        self,
        *,
        power: bool = True,
        mode: OnidaAcMode,
        temperature: int,
        fan: OnidaAcFanSpeed = OnidaAcFanSpeed.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        turbo: bool = False,
        display: bool = True,
        blow: bool = False,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Onida AC IR command."""
        super().__init__(modulation=modulation)

        if not MIN_TEMP <= temperature <= MAX_TEMP:
            raise ValueError(
                f"temperature {temperature} out of range {MIN_TEMP}..{MAX_TEMP}"
            )

        self.power = power
        self.mode = mode
        self.temperature = temperature
        self.fan = fan
        self.swing_v = swing_v
        self.swing_h = swing_h
        self.turbo = turbo
        self.display = display
        self.blow = blow

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Onida AC command."""
        frame_a = [0] * _FRAME_A_BITS
        _set_field(frame_a, *_A_MODE, self.mode.value)
        frame_a[_A_POWER] = int(self.power)
        _set_field(frame_a, *_A_FAN, self.fan.value)
        frame_a[_A_SWING] = int(self.swing_v or self.swing_h)
        _set_field(frame_a, *_A_TEMP, self.temperature - _TEMP_OFFSET)
        frame_a[_A_TURBO] = int(self.turbo)
        frame_a[_A_DISPLAY] = int(self.display)
        frame_a[_A_BLOW] = int(self.blow)
        for index in _A_TRAILER:
            frame_a[index] = 1

        frame_b = [0] * _FRAME_B_BITS
        frame_b[_B_SWING_V] = int(self.swing_v)
        frame_b[_B_SWING_H] = int(self.swing_h)
        frame_b[_B_SIGNATURE] = 1
        checksum = _checksum(
            mode=self.mode.value,
            power=self.power,
            temp=self.temperature,
            swing_h=self.swing_h,
        )
        _set_field(frame_b, *_B_CHECKSUM, checksum)

        timings = _encode_frame(frame_a, leader=True)
        timings.append(-_FRAME_GAP)
        timings.extend(_encode_frame(frame_b, leader=False))
        timings.append(-_FRAME_GAP)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into an OnidaAcCommand.

        Expects block A followed by block B, as ``get_raw_timings`` emits them.
        Returns an OnidaAcCommand if the timings match, or None otherwise.
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

        frame_b = _decode_bits(timings, frame_a_len + 1, _FRAME_B_BITS)
        if frame_b is None:
            return None

        for index in _A_TRAILER:
            if frame_a[index] != 1:
                return None
        if frame_b[_B_SIGNATURE] != 1:
            return None

        try:
            mode = OnidaAcMode(_get_field(frame_a, *_A_MODE))
            fan = OnidaAcFanSpeed(_get_field(frame_a, *_A_FAN))
        except ValueError:
            return None

        temperature = _get_field(frame_a, *_A_TEMP) + _TEMP_OFFSET
        if not MIN_TEMP <= temperature <= MAX_TEMP:
            return None

        power = bool(frame_a[_A_POWER])
        swing_h = bool(frame_b[_B_SWING_H])
        if _get_field(frame_b, *_B_CHECKSUM) != _checksum(
            mode=mode.value, power=power, temp=temperature, swing_h=swing_h
        ):
            return None

        return cls(
            power=power,
            mode=mode,
            temperature=temperature,
            fan=fan,
            swing_v=bool(frame_b[_B_SWING_V]),
            swing_h=swing_h,
            turbo=bool(frame_a[_A_TURBO]),
            display=bool(frame_a[_A_DISPLAY]),
            blow=bool(frame_a[_A_BLOW]),
        )
