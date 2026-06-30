"""LG air-conditioner IR protocol.

LG 28-bit protocol. Frame layout (28 bits, MSB first):
  bits 27-20: 0x88 signature
  bits 19-16: command upper nibble
  bits 15-12: command lower nibble
  bits 11-8:  temperature field (temp_c - 15, valid 0–15)
  bits 7-4:   fan speed nibble
  bits 3-0:   checksum (sum of nibbles 1–6, low 4 bits)

Power-on/mode-change commands use the LG standard header (8500/4250 µs).
Power-off uses the LG2 short header (3200/9900 µs) as transmitted by the
physical remote.
"""

from dataclasses import dataclass
from enum import IntEnum

from . import Command

MIN_TEMP = 16
MAX_TEMP = 30

_HDR_MARK = 8500
_HDR_SPACE = 4250
# Power-off uses a distinct short-burst header captured from the physical remote.
_OFF_HDR_MARK = 3200
_OFF_HDR_SPACE = 9900
_BIT_MARK = 550
_BIT_ONE_SPACE = 1600
_BIT_ZERO_SPACE = 550

_BASE = 0x8800000
_BITS = 28

# Dry mode always encodes fixed 24 °C regardless of setpoint — verified from captures.
_DRY_TEMP_FIELD = 0x900

# Some remotes set bit 3 of the command's low nibble as a variant flag without
# changing the operating mode; mask it off before mapping back to a mode.
_CMD_VARIANT_BIT = 0x08

_HDR_TOLERANCE = 2000


class LgAcMode(IntEnum):
    """AC operating mode; value is the command byte at frame bits 19-12."""

    COOL = 0x00
    DRY = 0x01
    FAN_ONLY = 0x02
    HEAT = 0x04
    OFF = 0xC0


class LgAcFanSpeed(IntEnum):
    """Fan speed; value is the protocol nibble at frame bits 7-4."""

    LOW = 0x0
    QUIET = 0x1
    MEDIUM = 0x2
    HIGH = 0x4
    AUTO = 0x5


@dataclass(frozen=True, slots=True)
class LgAcState:
    """Decoded AC state from an IR signal."""

    mode: LgAcMode
    fan: LgAcFanSpeed
    temp_c: int | None


def _checksum(value: int) -> int:
    total = sum((value >> (i * 4)) & 0xF for i in range(1, 7))
    return value | (total & 0xF)


def _encode_frame(frame: int, hdr_mark: int, hdr_space: int) -> list[int]:
    timings: list[int] = [hdr_mark, -hdr_space]
    for i in range(_BITS - 1, -1, -1):
        bit = (frame >> i) & 1
        timings.append(_BIT_MARK)
        timings.append(-(_BIT_ONE_SPACE if bit else _BIT_ZERO_SPACE))
    timings.append(_BIT_MARK)
    return timings


def decode(timings: list[int]) -> LgAcState | None:
    """Decode raw LG AC IR timings to an :class:`LgAcState`.

    Returns ``None`` if the signal is not a recognised LG AC command.
    """
    if len(timings) < 58:  # header(2) + 28 bit-pairs(56)
        return None

    hdr_mark = timings[0]
    hdr_space = abs(timings[1])

    is_standard = (
        _HDR_MARK - _HDR_TOLERANCE <= hdr_mark <= _HDR_MARK + _HDR_TOLERANCE
        and _HDR_SPACE - _HDR_TOLERANCE <= hdr_space <= _HDR_SPACE + _HDR_TOLERANCE
    )
    is_lg2 = (
        _OFF_HDR_MARK - _HDR_TOLERANCE <= hdr_mark <= _OFF_HDR_MARK + _HDR_TOLERANCE
        and _OFF_HDR_SPACE - _HDR_TOLERANCE
        <= hdr_space
        <= _OFF_HDR_SPACE + _HDR_TOLERANCE
    )
    if not is_standard and not is_lg2:
        return None

    frame = 0
    i = 2
    bits_read = 0
    while i + 1 < len(timings) and bits_read < _BITS:
        frame = (frame << 1) | (1 if abs(timings[i + 1]) > 1000 else 0)
        i += 2
        bits_read += 1

    if frame >> 20 != 0x88:
        return None

    nibs = [(frame >> (j * 4)) & 0xF for j in range(7)]

    if sum(nibs[1:7]) & 0xF != nibs[0]:
        return None

    cmd_byte = ((nibs[4] << 4) | nibs[3]) & ~_CMD_VARIANT_BIT
    try:
        mode = LgAcMode(cmd_byte)
    except ValueError:
        return None

    try:
        fan = LgAcFanSpeed(nibs[1])
    except ValueError:
        fan = LgAcFanSpeed.AUTO
    temp_c: int | None = None
    if mode not in (LgAcMode.OFF, LgAcMode.DRY, LgAcMode.FAN_ONLY) and nibs[2] > 0:
        temp_c = nibs[2] + 15

    return LgAcState(mode=mode, fan=fan, temp_c=temp_c)


class LgAcCommand(Command):
    """LG air-conditioner IR command.

    ``mode=LgAcMode.OFF`` uses the LG2 short header; all other modes use the
    LG standard header. ``temperature`` is required for ``COOL`` and ``HEAT``
    modes and is ignored for ``DRY`` (protocol-fixed at 24 °C) and ``FAN_ONLY``.
    """

    def __init__(
        self,
        *,
        mode: LgAcMode,
        temperature: int | None = None,
        fan: LgAcFanSpeed = LgAcFanSpeed.AUTO,
        modulation: int = 38000,
    ) -> None:
        """Build an LG AC IR command."""
        super().__init__(modulation=modulation)

        if mode in (LgAcMode.COOL, LgAcMode.HEAT):
            if temperature is None:
                raise ValueError(f"temperature is required for mode {mode.name}")
            if not MIN_TEMP <= temperature <= MAX_TEMP:
                raise ValueError(
                    f"temperature {temperature} out of range {MIN_TEMP}..{MAX_TEMP}"
                )

        cmd = mode.value << 12
        fan_bits = fan.value << 4

        if mode is LgAcMode.DRY:
            temp_field = _DRY_TEMP_FIELD
        elif mode in (LgAcMode.COOL, LgAcMode.HEAT):
            temp_field = max(0, min(15, (temperature or MIN_TEMP) - 15)) << 8
        else:
            temp_field = 0

        # Power-off is the only mode that uses the LG2 short-burst header.
        if mode is LgAcMode.OFF:
            header = (_OFF_HDR_MARK, _OFF_HDR_SPACE)
        else:
            header = (_HDR_MARK, _HDR_SPACE)

        frame = _checksum(_BASE | cmd | fan_bits | temp_field)
        self._timings = _encode_frame(frame, *header)

    def get_raw_timings(self) -> list[int]:
        """Return signed µs timings."""
        return self._timings
