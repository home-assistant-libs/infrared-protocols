"""Samsung air-conditioner IR commands."""

from enum import IntEnum
from typing import Self, override

from . import Command


class SamsungAC0292HvacMode(IntEnum):
    """AC HVAC mode; value is the mode nibble at section3 byte 5 bits 4-7.

    OFF has no mode nibble of its own: the frame is a separate fixed payload, so this
    sentinel value (outside the real 0-4 nibble range) only marks that case internally.
    """

    AUTO = 0
    COOL = 1
    DRY = 2
    FAN_ONLY = 3
    HEAT = 4
    OFF = 0xF


class SamsungACFanMode(IntEnum):
    """AC fan mode; value is the fan nibble at section3 byte 5 bits 1-3."""

    AUTO = 0
    LOW = 2
    MEDIUM = 4
    HIGH = 5


class SamsungACSwingMode(IntEnum):
    """AC swing mode; value is the pre-shift code embedded in section3 byte 2."""

    VERTICAL = 0x2
    OFF = 0x7


AC0292_MIN_TEMP = 16
AC0292_MAX_TEMP = 30

_AC0292_SECTION1_BASE = [0x02, 0x02, 0x00, 0x00, 0x00, 0x00, 0xF0]
_AC0292_SECTION2_BASE = [0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00]
_AC0292_SECTION3_BASE = [0x01, 0x02, 0x00, 0x71, 0x00, 0x11, 0xF0]

_AC0292_OFF_PAYLOAD = [
    0x02, 0xB2, 0x0F, 0x00, 0x00, 0x00, 0xC0, 0x01, 0xD2, 0x0F, 0x00,
    0x00, 0x00, 0x00, 0x01, 0x02, 0xFF, 0x71, 0x80, 0x11, 0xC0
]  # fmt: skip

_AC0292_PAYLOAD_LEN = 21
_AC0292_SECTION_LEN = 7
_AC0292_NUM_SECTIONS = _AC0292_PAYLOAD_LEN // _AC0292_SECTION_LEN

_AC0292_HDR_MARK = 690
_AC0292_HDR_SPACE = 17844

_AC0292_SECTION_MARK = 3086
_AC0292_SECTION_SPACE = 8864

_AC0292_BIT_MARK = 586
_AC0292_BIT_ONE_SPACE = 1432
_AC0292_BIT_ZERO_SPACE = 436

_AC0292_TRAILER_MARK = 586
_AC0292_TRAILER_SPACE_LAST = 30000
_AC0292_TRAILER_SPACE_MORE = 2886


_AC0292_MARK_TOLERANCE = 0.3
_AC0292_SPACE_TOLERANCE = 0.25
_AC0292_BIT_TOLERANCE = 300

_AC0292_TIMINGS_LEN = 2 + _AC0292_NUM_SECTIONS * (2 + _AC0292_SECTION_LEN * 8 * 2 + 2)

_AC0292_MIN_TIMINGS_LEN = _AC0292_TIMINGS_LEN - 1


def _ac0292_is_close(actual: int, expected: int, tolerance: float) -> bool:
    margin = expected * tolerance
    return expected - margin <= actual <= expected + margin


def _ac0292_matches_pair(mark: int, space: int, exp_mark: int, exp_space: int) -> bool:
    return _ac0292_is_close(
        mark, exp_mark, _AC0292_MARK_TOLERANCE
    ) and _ac0292_is_close(space, exp_space, _AC0292_SPACE_TOLERANCE)


def _ac0292_decode_bit(mark: int, space: int) -> int | None:
    if abs(mark - _AC0292_BIT_MARK) > _AC0292_BIT_TOLERANCE:
        return None
    if abs(space - _AC0292_BIT_ZERO_SPACE) <= _AC0292_BIT_TOLERANCE:
        return 0
    if abs(space - _AC0292_BIT_ONE_SPACE) <= _AC0292_BIT_TOLERANCE:
        return 1
    return None


def _ac0292_apply_checksum(section: list[int]) -> list[int]:
    section = list(section)
    checksum = _ac0292_section_checksum(section)
    section[1] = (section[1] & 0x0F) | ((checksum & 0x0F) << 4)
    section[2] = (section[2] & 0xF0) | ((checksum >> 4) & 0x0F)
    return section


def _ac0292_section_checksum(section: list[int]) -> int:
    total = (
        section[0].bit_count()
        + (section[1] & 0x0F).bit_count()
        + (section[2] >> 4).bit_count()
        + sum(byte.bit_count() for byte in section[3:7])
    )
    return total ^ 0xFF


def _ac0292_verify_checksum(section: list[int]) -> bool:
    """Check a section's embedded checksum.

    The checksum formula only reads bits that survive checksum embedding (the low
    nibble of byte 1, the high nibble of byte 2), so it can be recomputed directly
    from a decoded section and compared against the checksum nibbles stored in it.
    """
    stored = ((section[1] >> 4) & 0xF) | ((section[2] & 0x0F) << 4)
    return stored == _ac0292_section_checksum(section)


_AC0292_SECTION1 = _ac0292_apply_checksum(_AC0292_SECTION1_BASE)
_AC0292_SECTION2 = _ac0292_apply_checksum(_AC0292_SECTION2_BASE)


class SamsungAC0292Command(Command):
    """Samsung AC 0292 21-byte IR command.

    ``target_temperature``, ``fan_mode``, and ``swing_mode`` are required unless
    ``hvac_mode`` is ``OFF``, in which case they must be left as ``None`` (the frame
    for OFF is fixed and carries none of them).
    """

    hvac_mode: SamsungAC0292HvacMode
    target_temperature: int | None
    fan_mode: SamsungACFanMode | None
    swing_mode: SamsungACSwingMode | None

    def __init__(
        self,
        *,
        hvac_mode: SamsungAC0292HvacMode,
        target_temperature: int | None = None,
        fan_mode: SamsungACFanMode | None = None,
        swing_mode: SamsungACSwingMode | None = None,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Samsung AC 0292 IR command."""
        super().__init__(modulation=modulation, repeat_count=0)

        if hvac_mode is SamsungAC0292HvacMode.OFF:
            if (
                target_temperature is not None
                or fan_mode is not None
                or swing_mode is not None
            ):
                raise ValueError(
                    "target_temperature, fan_mode, and swing_mode must be None "
                    "when hvac_mode is OFF"
                )
        else:
            if target_temperature is None:
                raise ValueError(
                    f"target_temperature is required for hvac_mode {hvac_mode.name}"
                )
            if not AC0292_MIN_TEMP <= target_temperature <= AC0292_MAX_TEMP:
                raise ValueError(
                    f"target_temperature {target_temperature} out of range "
                    f"{AC0292_MIN_TEMP}..{AC0292_MAX_TEMP}"
                )
            if fan_mode is None:
                raise ValueError(f"fan_mode is required for hvac_mode {hvac_mode.name}")
            if swing_mode is None:
                raise ValueError(
                    f"swing_mode is required for hvac_mode {hvac_mode.name}"
                )

        self.hvac_mode = hvac_mode
        self.target_temperature = target_temperature
        self.fan_mode = None if hvac_mode is SamsungAC0292HvacMode.AUTO else fan_mode
        self.swing_mode = swing_mode

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Samsung AC 0292 command."""
        payload = self._build_payload()

        timings: list[int] = [_AC0292_HDR_MARK, -_AC0292_HDR_SPACE]
        for offset in range(0, len(payload), _AC0292_SECTION_LEN):
            timings.extend([_AC0292_SECTION_MARK, -_AC0292_SECTION_SPACE])
            for byte in payload[offset : offset + _AC0292_SECTION_LEN]:
                for bit in range(8):
                    timings.extend(
                        [
                            _AC0292_BIT_MARK,
                            -_AC0292_BIT_ONE_SPACE
                            if (byte >> bit) & 1
                            else -_AC0292_BIT_ZERO_SPACE,
                        ]
                    )
            is_last = offset + _AC0292_SECTION_LEN >= len(payload)
            timings.extend(
                [
                    _AC0292_TRAILER_MARK,
                    -_AC0292_TRAILER_SPACE_LAST
                    if is_last
                    else -_AC0292_TRAILER_SPACE_MORE,
                ]
            )

        return timings

    def _build_payload(self) -> list[int]:
        if self.hvac_mode is SamsungAC0292HvacMode.OFF:
            return _AC0292_OFF_PAYLOAD.copy()

        section3 = list(_AC0292_SECTION3_BASE)

        assert self.swing_mode is not None
        section3[2] = 0x80 | (self.swing_mode.value << 4)

        assert self.target_temperature is not None
        section3[4] = (self.target_temperature - AC0292_MIN_TEMP) << 4

        if self.hvac_mode is SamsungAC0292HvacMode.AUTO:
            fan = 6
        else:
            assert self.fan_mode is not None
            fan = self.fan_mode.value
        section3[5] = 0x01 | (fan << 1) | (self.hvac_mode.value << 4)

        return _AC0292_SECTION1 + _AC0292_SECTION2 + _ac0292_apply_checksum(section3)

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a SamsungAC0292Command.

        Returns a SamsungAC0292Command if the timings match, or None otherwise. A
        missing final trailer space (some receivers don't record the trailing gap
        after the last mark) and extra timings after the signal ends are both
        tolerated.
        """
        if len(timings) < _AC0292_MIN_TIMINGS_LEN:
            return None

        if not _ac0292_matches_pair(
            timings[0], abs(timings[1]), _AC0292_HDR_MARK, _AC0292_HDR_SPACE
        ):
            return None

        idx = 2
        payload: list[int] = []
        for section_index in range(_AC0292_NUM_SECTIONS):
            if not _ac0292_matches_pair(
                timings[idx],
                abs(timings[idx + 1]),
                _AC0292_SECTION_MARK,
                _AC0292_SECTION_SPACE,
            ):
                return None
            idx += 2

            for _ in range(_AC0292_SECTION_LEN):
                byte = 0
                for bit in range(8):
                    decoded = _ac0292_decode_bit(timings[idx], abs(timings[idx + 1]))
                    if decoded is None:
                        return None
                    byte |= decoded << bit
                    idx += 2
                payload.append(byte)

            is_last_section = section_index == _AC0292_NUM_SECTIONS - 1
            expected_trailer_space = (
                _AC0292_TRAILER_SPACE_LAST
                if is_last_section
                else _AC0292_TRAILER_SPACE_MORE
            )

            if not _ac0292_is_close(
                timings[idx], _AC0292_TRAILER_MARK, _AC0292_MARK_TOLERANCE
            ):
                return None
            idx += 1

            if idx < len(timings):
                if not _ac0292_is_close(
                    abs(timings[idx]), expected_trailer_space, _AC0292_SPACE_TOLERANCE
                ):
                    return None
                idx += 1
            elif not is_last_section:
                return None

        if payload == _AC0292_OFF_PAYLOAD:
            return cls(hvac_mode=SamsungAC0292HvacMode.OFF)

        section1 = payload[0:7]
        section2 = payload[7:14]
        section3 = payload[14:21]

        if section1 != _AC0292_SECTION1:
            return None

        if section2 != _AC0292_SECTION2:
            return None

        if (
            section3[0] != _AC0292_SECTION3_BASE[0]
            or (section3[1] & 0x0F) != (_AC0292_SECTION3_BASE[1] & 0x0F)
            or section3[3] != _AC0292_SECTION3_BASE[3]
            or (section3[4] & 0x0F) != (_AC0292_SECTION3_BASE[4] & 0x0F)
            or section3[6] != _AC0292_SECTION3_BASE[6]
            or not _ac0292_verify_checksum(section3)
        ):
            return None

        swing_nibble = (section3[2] >> 4) & 0xF
        if swing_nibble & 0x8 == 0:
            return None
        try:
            swing_mode = SamsungACSwingMode(swing_nibble & 0x7)
        except ValueError:
            return None

        temperature = ((section3[4] >> 4) & 0xF) + AC0292_MIN_TEMP
        if not AC0292_MIN_TEMP <= temperature <= AC0292_MAX_TEMP:
            return None

        combined = section3[5]
        if combined & 0x1 != 1:
            return None

        try:
            hvac_mode = SamsungAC0292HvacMode((combined >> 4) & 0xF)
        except ValueError:
            return None
        if hvac_mode is SamsungAC0292HvacMode.OFF:
            return None

        fan_nibble = (combined >> 1) & 0x7
        if hvac_mode is SamsungAC0292HvacMode.AUTO:
            if fan_nibble != 6:
                return None
            fan_mode = SamsungACFanMode.AUTO
        else:
            try:
                fan_mode = SamsungACFanMode(fan_nibble)
            except ValueError:
                return None

        return cls(
            hvac_mode=hvac_mode,
            target_temperature=temperature,
            fan_mode=fan_mode,
            swing_mode=swing_mode,
        )
