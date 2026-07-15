"""LG air-conditioner IR protocol.

LG 28-bit protocol, LG2 timing variant. Frame layout (28 bits, MSB first):
  bits 27-20: 0x88 signature
  bits 19-16: mode high nibble
  bits 15-12: mode low nibble
  bits 11-8:  temperature field (temp_c - 15)
  bits 7-4:   fan speed nibble
  bits 3-0:   checksum (sum of nibbles 1-6, low 4 bits)

Bit 3 of the mode's low nibble is a settings-only flag: a remote sets it to change a
setting on a running unit. Cleared, the same frame also powers the unit on, so this
encoder always emits it clear.
"""

from enum import IntEnum
from typing import Self, override

from . import Command

MIN_TEMP = 16
MAX_TEMP = 30

_TEMP_OFFSET = 15

_HDR_MARK = 3200
_HDR_SPACE = 9900
# Some LG units use this longer header.
_ALT_HDR_MARK = 8500
_ALT_HDR_SPACE = 4250

_BIT_MARK = 550
_BIT_ONE_SPACE = 1600
_BIT_ZERO_SPACE = 550

_SIGNATURE = 0x88
_BASE = _SIGNATURE << 20
_BITS = 28

# Dry mode always encodes fixed 24 °C
_DRY_TEMP = 24

# Marks a fixed code rather than a state frame. Power-off is one, the display toggle
# (0x88C00A6) another. They differ only in bits 11-0, which carry no temperature or fan
# here, so a fixed code is identified by its whole frame.
_FIXED_CODE_MODE_BYTE = 0xC0

_OFF_FRAME = 0x88C0051

# Masked off when decoding, so a settings frame and a power-on frame give the same mode.
_SETTINGS_ONLY_BIT = 0x08

# IR receivers distort marks (AGC) but keep spaces accurate, and the space is what tells
# the two header variants apart.
_MARK_TOLERANCE = 0.7
_SPACE_TOLERANCE = 0.25

# A receiver skews a bit's mark and space by roughly a fixed number of microseconds
# rather than a fixed proportion, so bits get an absolute tolerance. It covers the skew
# seen in practice and still keeps the zero and one spaces apart (200-900 vs 1250-1950).
_BIT_TOLERANCE = 350


class LgAcMode(IntEnum):
    """AC operating mode; value is the mode byte at frame bits 19-12."""

    COOL = 0x00
    DRY = 0x01
    FAN_ONLY = 0x02
    HEAT = 0x04
    OFF = _FIXED_CODE_MODE_BYTE


class LgAcFanSpeed(IntEnum):
    """Fan speed; value is the protocol nibble at frame bits 7-4."""

    QUIET = 0x1
    LOW = 0x0
    MEDIUM_LOW = 0x9
    MEDIUM = 0x2
    MEDIUM_HIGH = 0xA
    HIGH = 0x4
    AUTO = 0x5


def _checksum(value: int) -> int:
    """Return the checksum nibble: sum of nibbles 1-6, low 4 bits."""
    return sum((value >> (i * 4)) & 0xF for i in range(1, 7)) & 0xF


def _is_close(actual: int, expected: int, tolerance: float) -> bool:
    """Check if a timing is within the given relative tolerance of the expected."""
    margin = expected * tolerance
    return expected - margin <= actual <= expected + margin


def _matches_header(mark: int, space: int, exp_mark: int, exp_space: int) -> bool:
    return _is_close(mark, exp_mark, _MARK_TOLERANCE) and _is_close(
        space, exp_space, _SPACE_TOLERANCE
    )


def _decode_bit(mark: int, space: int) -> int | None:
    """Decode one bit from its mark and space, or None if it matches neither."""
    if abs(mark - _BIT_MARK) > _BIT_TOLERANCE:
        return None
    if abs(space - _BIT_ZERO_SPACE) <= _BIT_TOLERANCE:
        return 0
    if abs(space - _BIT_ONE_SPACE) <= _BIT_TOLERANCE:
        return 1
    return None


def _encode_frame(frame: int) -> list[int]:
    timings: list[int] = [_HDR_MARK, -_HDR_SPACE]
    for i in range(_BITS - 1, -1, -1):
        bit = (frame >> i) & 1
        timings.append(_BIT_MARK)
        timings.append(-(_BIT_ONE_SPACE if bit else _BIT_ZERO_SPACE))
    timings.append(_BIT_MARK)
    return timings


class LgAcCommand(Command):
    """LG air-conditioner IR command.

    ``temperature`` is required for ``COOL`` and ``HEAT``, and ignored otherwise.
    ``fan`` is ignored for ``OFF``.
    """

    mode: LgAcMode
    temperature: int | None
    fan: LgAcFanSpeed | None

    def __init__(
        self,
        *,
        mode: LgAcMode,
        temperature: int | None = None,
        fan: LgAcFanSpeed = LgAcFanSpeed.AUTO,
        modulation: int = 38000,
    ) -> None:
        """Initialize the LG AC IR command."""
        super().__init__(modulation=modulation)

        if mode in (LgAcMode.COOL, LgAcMode.HEAT):
            if temperature is None:
                raise ValueError(f"temperature is required for mode {mode.name}")
            if not MIN_TEMP <= temperature <= MAX_TEMP:
                raise ValueError(
                    f"temperature {temperature} out of range {MIN_TEMP}..{MAX_TEMP}"
                )

        self.mode = mode
        # Only cool and heat carry a temperature; storing one the frame cannot express
        # would make a command unequal to itself after a roundtrip.
        self.temperature = (
            temperature if mode in (LgAcMode.COOL, LgAcMode.HEAT) else None
        )
        # OFF is a fixed frame that carries no fan; like temperature it is dropped to
        # None, so the field never claims a fan the frame does not send.
        self.fan = None if mode is LgAcMode.OFF else fan

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the LG AC command."""
        if self.mode is LgAcMode.OFF:
            return _encode_frame(_OFF_FRAME)

        assert self.fan is not None, "fan missing for non-OFF mode"
        mode_bits = self.mode.value << 12
        fan_bits = self.fan.value << 4

        if self.mode is LgAcMode.DRY:
            temp_bits = (_DRY_TEMP - _TEMP_OFFSET) << 8
        elif self.temperature is not None:
            temp_bits = (self.temperature - _TEMP_OFFSET) << 8
        else:
            temp_bits = 0

        frame_data = _BASE | mode_bits | fan_bits | temp_bits
        return _encode_frame(frame_data | _checksum(frame_data))

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into an LgAcCommand.

        Returns an LgAcCommand if the timings match, or None otherwise.
        """
        # Header pair (2) + 28 bit pairs (56) + the trailing mark (1)
        if len(timings) < 2 + 2 * _BITS + 1:
            return None

        hdr_mark = timings[0]
        hdr_space = abs(timings[1])
        if not (
            _matches_header(hdr_mark, hdr_space, _HDR_MARK, _HDR_SPACE)
            or _matches_header(hdr_mark, hdr_space, _ALT_HDR_MARK, _ALT_HDR_SPACE)
        ):
            return None

        frame = 0
        for i in range(2, 2 + 2 * _BITS, 2):
            bit = _decode_bit(timings[i], abs(timings[i + 1]))
            if bit is None:
                return None
            frame = (frame << 1) | bit

        if abs(timings[2 + 2 * _BITS] - _BIT_MARK) > _BIT_TOLERANCE:
            return None

        if frame >> 20 != _SIGNATURE:
            return None

        if _checksum(frame) != frame & 0xF:
            return None

        if frame == _OFF_FRAME:
            return cls(mode=LgAcMode.OFF)

        mode_byte = ((frame >> 12) & 0xFF) & ~_SETTINGS_ONLY_BIT
        if mode_byte == _FIXED_CODE_MODE_BYTE:
            # A fixed code this class does not model, such as the display toggle. The
            # power-off code is the one exception, matched in full above.
            return None

        try:
            mode = LgAcMode(mode_byte)
            fan = LgAcFanSpeed((frame >> 4) & 0xF)
        except ValueError:
            return None

        temperature: int | None = None
        if mode in (LgAcMode.COOL, LgAcMode.HEAT):
            temperature = ((frame >> 8) & 0xF) + _TEMP_OFFSET
            if not MIN_TEMP <= temperature <= MAX_TEMP:
                return None

        return cls(mode=mode, temperature=temperature, fan=fan)
