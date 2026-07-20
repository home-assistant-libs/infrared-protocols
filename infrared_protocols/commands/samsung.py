"""Samsung IR commands."""

from typing import Literal, Self, override

from . import Command

type SamsungAC0292HvacMode = Literal["off", "auto", "cool", "dry", "fan_only", "heat"]
type SamsungACFanMode = Literal["auto", "low", "medium", "high"]
type SamsungACSwingMode = Literal["off", "vertical"]

MIN_TEMP = 16
MAX_TEMP = 30

_MODE_AUTO = 0
_MODE_COOL = 1
_MODE_DRY = 2
_MODE_FAN = 3
_MODE_HEAT = 4

_FAN_VALUE: dict[SamsungACFanMode, int] = {
    "auto": 0,
    "low": 2,
    "medium": 4,
    "high": 5,
}
_FAN_MODE_BY_VALUE: dict[int, SamsungACFanMode] = {v: k for k, v in _FAN_VALUE.items()}

_HVAC_VALUE: dict[SamsungAC0292HvacMode, int] = {
    "auto": _MODE_AUTO,
    "cool": _MODE_COOL,
    "dry": _MODE_DRY,
    "fan_only": _MODE_FAN,
    "heat": _MODE_HEAT,
}
_HVAC_MODE_BY_VALUE: dict[int, SamsungAC0292HvacMode] = {
    v: k for k, v in _HVAC_VALUE.items()
}

_OFF_PAYLOAD = [
    0x02,
    0xB2,
    0x0F,
    0x00,
    0x00,
    0x00,
    0xC0,
    0x01,
    0xD2,
    0x0F,
    0x00,
    0x00,
    0x00,
    0x00,
    0x01,
    0x02,
    0xFF,
    0x71,
    0x80,
    0x11,
    0xC0,
]

_PAYLOAD_LEN = 21
_SECTION_LEN = 7
_NUM_SECTIONS = _PAYLOAD_LEN // _SECTION_LEN

_HDR_MARK = 690
_HDR_SPACE = 17844

_SECTION_MARK = 3086
_SECTION_SPACE = 8864

_BIT_MARK = 586
_BIT_ONE_SPACE = 1432
_BIT_ZERO_SPACE = 436

_TRAILER_MARK = 586
_TRAILER_SPACE_LAST = 30000
_TRAILER_SPACE_MORE = 2886

_MARK_TOLERANCE = 0.3
_SPACE_TOLERANCE = 0.25
_BIT_TOLERANCE = 300

_TIMINGS_LEN = 2 + _NUM_SECTIONS * (2 + _SECTION_LEN * 8 * 2 + 2)


def _is_close(actual: int, expected: int, tolerance: float) -> bool:
    margin = expected * tolerance
    return expected - margin <= actual <= expected + margin


def _matches_pair(mark: int, space: int, exp_mark: int, exp_space: int) -> bool:
    return _is_close(mark, exp_mark, _MARK_TOLERANCE) and _is_close(
        space, exp_space, _SPACE_TOLERANCE
    )


def _decode_bit(mark: int, space: int) -> int | None:
    if abs(mark - _BIT_MARK) > _BIT_TOLERANCE:
        return None
    if abs(space - _BIT_ZERO_SPACE) <= _BIT_TOLERANCE:
        return 0
    if abs(space - _BIT_ONE_SPACE) <= _BIT_TOLERANCE:
        return 1
    return None


def _apply_checksum(section: list[int]) -> list[int]:
    section = list(section)
    checksum = _section_checksum(section)
    section[1] = (section[1] & 0x0F) | ((checksum & 0x0F) << 4)
    section[2] = (section[2] & 0xF0) | ((checksum >> 4) & 0x0F)
    return section


def _section_checksum(section: list[int]) -> int:
    total = (
        section[0].bit_count()
        + (section[1] & 0x0F).bit_count()
        + (section[2] >> 4).bit_count()
        + sum(byte.bit_count() for byte in section[3:7])
    )
    return total ^ 0xFF


def _verify_checksum(section: list[int]) -> bool:
    """Check a section's embedded checksum.

    The checksum formula only reads bits that survive checksum embedding (the low
    nibble of byte 1, the high nibble of byte 2), so it can be recomputed directly
    from a decoded section and compared against the checksum nibbles stored in it.
    """
    stored = ((section[1] >> 4) & 0xF) | ((section[2] & 0x0F) << 4)
    return stored == _section_checksum(section)


class Samsung32Command(Command):
    """Samsung32 IR command."""

    address: int
    command: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Samsung32 IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Samsung32 command.

        Samsung32 protocol timing (in microseconds):
        - Leader pulse: 4500µs high, 4500µs low
        - Logical '0': 560µs high, 560µs low
        - Logical '1': 560µs high, 1690µs low
        - End pulse: 560µs high
        - Repeat: full frame retransmission, total frame padded to 108ms

        Data format (32 bits, LSB first per byte):
        - Standard Samsung32: address (8-bit) + address (8-bit) + command (8-bit)
          + ~command (8-bit)
        - Extended Samsung32: address_low (8-bit) + address_high (8-bit)
          + command (8-bit) + ~command (8-bit)
        """
        leader_high = 4500
        leader_low = 4500
        bit_high = 560
        zero_low = 560
        one_low = 1690
        frame_time = 108000

        timings: list[int] = [leader_high, -leader_low]

        if self.address <= 0xFF:
            # Standard Samsung32: same address byte sent twice
            address_low = self.address & 0xFF
            address_high = self.address & 0xFF
        else:
            # Extended: 16-bit address split into low/high
            address_low = self.address & 0xFF
            address_high = (self.address >> 8) & 0xFF

        command_byte = self.command & 0xFF
        command_inverted = (~self.command) & 0xFF

        data = (
            address_low
            | (address_high << 8)
            | (command_byte << 16)
            | (command_inverted << 24)
        )

        for _ in range(32):
            bit = data & 1
            timings.append(bit_high)
            timings.append(-one_low if bit else -zero_low)
            data >>= 1

        # End pulse
        timings.append(bit_high)

        # Add repeat codes (full frame retransmission)
        if self.repeat_count > 0:
            frame_duration = sum(abs(t) for t in timings)
            gap = frame_time - frame_duration
            base_frame = timings.copy()
            for _ in range(self.repeat_count):
                timings.append(-gap)
                timings.extend(base_frame)

        return timings


class SamsungAC0292Command(Command):
    """Samsung AC 0292 21-byte IR command.

    ``target_temperature`` is required unless ``hvac_mode`` is ``"off"``.
    ``fan_mode`` carries no meaning when ``hvac_mode`` is ``"off"`` (the frame sends no
    fan) or ``"auto"`` (the unit always encodes a fixed fan value regardless of what's
    requested).
    """

    hvac_mode: SamsungAC0292HvacMode
    target_temperature: int | None
    fan_mode: SamsungACFanMode | None
    swing_mode: SamsungACSwingMode

    def __init__(
        self,
        *,
        hvac_mode: SamsungAC0292HvacMode,
        target_temperature: int | None = None,
        fan_mode: SamsungACFanMode = "auto",
        swing_mode: SamsungACSwingMode = "off",
        modulation: int = 38000,
    ) -> None:
        """Initialize the Samsung AC 0292 IR command."""
        super().__init__(modulation=modulation, repeat_count=0)

        if hvac_mode != "off":
            if target_temperature is None:
                raise ValueError(
                    f"target_temperature is required for hvac_mode {hvac_mode!r}"
                )
            if not MIN_TEMP <= target_temperature <= MAX_TEMP:
                raise ValueError(
                    f"target_temperature {target_temperature} out of range "
                    f"{MIN_TEMP}..{MAX_TEMP}"
                )

        self.hvac_mode = hvac_mode
        self.target_temperature = None if hvac_mode == "off" else target_temperature
        self.fan_mode = None if hvac_mode in ("off", "auto") else fan_mode
        self.swing_mode = swing_mode

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Samsung AC 0292 command."""
        payload = self._build_payload()

        timings: list[int] = [_HDR_MARK, -_HDR_SPACE]
        for offset in range(0, len(payload), _SECTION_LEN):
            timings.extend([_SECTION_MARK, -_SECTION_SPACE])
            for byte in payload[offset : offset + _SECTION_LEN]:
                for bit in range(8):
                    timings.extend(
                        [
                            _BIT_MARK,
                            -_BIT_ONE_SPACE if (byte >> bit) & 1 else -_BIT_ZERO_SPACE,
                        ]
                    )
            is_last = offset + _SECTION_LEN >= len(payload)
            timings.extend(
                [
                    _TRAILER_MARK,
                    -_TRAILER_SPACE_LAST if is_last else -_TRAILER_SPACE_MORE,
                ]
            )

        return timings

    def _build_payload(self) -> list[int]:
        if self.hvac_mode == "off":
            return _OFF_PAYLOAD.copy()

        section1 = _apply_checksum([0x02, 0x02, 0x00, 0x00, 0x00, 0x00, 0xF0])
        section2 = _apply_checksum([0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00])
        section3 = [0x01, 0x02, 0x00, 0x71, 0x00, 0x11, 0xF0]

        swing = 0x2 if self.swing_mode == "vertical" else 0x7
        section3[2] = 0x80 | (swing << 4)

        assert self.target_temperature is not None
        section3[4] = (self.target_temperature - MIN_TEMP) << 4

        mode = _HVAC_VALUE[self.hvac_mode]
        fan = 6 if mode == _MODE_AUTO else _FAN_VALUE[self.fan_mode or "auto"]
        section3[5] = 0x01 | (fan << 1) | (mode << 4)

        return section1 + section2 + _apply_checksum(section3)

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a SamsungAC0292Command.

        Returns a SamsungAC0292Command if the timings match, or None otherwise.
        """
        if len(timings) != _TIMINGS_LEN:
            return None

        if not _matches_pair(timings[0], abs(timings[1]), _HDR_MARK, _HDR_SPACE):
            return None

        idx = 2
        payload: list[int] = []
        for section_index in range(_NUM_SECTIONS):
            if not _matches_pair(
                timings[idx], abs(timings[idx + 1]), _SECTION_MARK, _SECTION_SPACE
            ):
                return None
            idx += 2

            for _ in range(_SECTION_LEN):
                byte = 0
                for bit in range(8):
                    decoded = _decode_bit(timings[idx], abs(timings[idx + 1]))
                    if decoded is None:
                        return None
                    byte |= decoded << bit
                    idx += 2
                payload.append(byte)

            is_last = section_index == _NUM_SECTIONS - 1
            expected_trailer_space = (
                _TRAILER_SPACE_LAST if is_last else _TRAILER_SPACE_MORE
            )
            if not _matches_pair(
                timings[idx],
                abs(timings[idx + 1]),
                _TRAILER_MARK,
                expected_trailer_space,
            ):
                return None
            idx += 2

        if payload == _OFF_PAYLOAD:
            return cls(hvac_mode="off")

        section1 = payload[0:7]
        section2 = payload[7:14]
        section3 = payload[14:21]

        if not all(
            _verify_checksum(section) for section in (section1, section2, section3)
        ):
            return None

        if (
            section1 != _apply_checksum([0x02, 0x02, 0x00, 0x00, 0x00, 0x00, 0xF0])
            or section2 != _apply_checksum([0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00])
            or section3[0] != 0x01
            or (section3[1] & 0x0F) != 0x02
            or section3[3] != 0x71
            or (section3[4] & 0x0F) != 0
            or section3[6] != 0xF0
        ):
            return None

        swing_nibble = (section3[2] >> 4) & 0xF
        if swing_nibble == 0xA:
            swing_mode: SamsungACSwingMode = "vertical"
        elif swing_nibble == 0xF:
            swing_mode = "off"
        else:
            return None

        temperature = ((section3[4] >> 4) & 0xF) + MIN_TEMP
        if not MIN_TEMP <= temperature <= MAX_TEMP:
            return None

        combined = section3[5]
        if combined & 0x1 != 1:
            return None

        mode_nibble = (combined >> 4) & 0xF
        hvac_mode = _HVAC_MODE_BY_VALUE.get(mode_nibble)
        if hvac_mode is None:
            return None

        fan_nibble = (combined >> 1) & 0x7
        if hvac_mode == "auto":
            if fan_nibble != 6:
                return None
            fan_mode: SamsungACFanMode = "auto"
        else:
            fan_mode_candidate = _FAN_MODE_BY_VALUE.get(fan_nibble)
            if fan_mode_candidate is None:
                return None
            fan_mode = fan_mode_candidate

        return cls(
            hvac_mode=hvac_mode,
            target_temperature=temperature,
            fan_mode=fan_mode,
            swing_mode=swing_mode,
        )
