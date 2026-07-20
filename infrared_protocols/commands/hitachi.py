"""Hitachi air-conditioner IR protocol.

Hitachi AC344 protocol variant (43 Byte / 344 Bit state frame).
"""

from enum import IntEnum
from typing import Self, override

from . import Command

MIN_TEMP = 16
MAX_TEMP = 32

_HDR_MARK = 3300
_HDR_SPACE = 1600
_BIT_MARK = 400
_BIT_ONE_SPACE = 1200
_BIT_ZERO_SPACE = 400
_FOOTER_MARK = 400

_TOLERANCE = 0.4

_BASE_SKELETON = [
    0x01, 0x10, 0x00, 0x40, 0xBF, 0xFF, 0x00, 0xCC, 0x33, 0xA5, 0x5A, 0x13, 0xEC, 0x68, 0x97, 0x00,
    0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x43, 0xBC, 0xF1, 0x0E, 0x00,
    0xFF, 0x00, 0xFF, 0x80, 0x7F, 0x03, 0xFC, 0x04, 0xFB, 0x20, 0xDF, 0x00, 0xFF
]


class HitachiAcMode(IntEnum):
    """Hitachi AC operating mode."""

    FAN_ONLY = 1
    COOL = 3
    DRY = 5
    HEAT = 6


class HitachiAcFanSpeed(IntEnum):
    """Hitachi AC fan speed."""

    AUTO = 1
    SILENT = 2
    LOW = 3
    HIGH = 4


class HitachiAcButton(IntEnum):
    """Hitachi AC action button identifier."""

    POWER = 0x13
    MODE = 0x41
    FAN = 0x42
    TEMPERATURE = 0x44


def _is_close(actual: int, expected: int) -> bool:
    margin = expected * _TOLERANCE
    return expected - margin <= actual <= expected + margin


def _decode_bit(mark: int, space: int) -> int | None:
    if not _is_close(mark, _BIT_MARK):
        return None
    if _is_close(space, _BIT_ZERO_SPACE):
        return 0
    if _is_close(space, _BIT_ONE_SPACE):
        return 1
    return None


class HitachiAc344Command(Command):
    """Hitachi AC 344-bit (43-byte) IR command."""

    mode: HitachiAcMode
    temperature: int
    fan: HitachiAcFanSpeed
    power: bool
    button: HitachiAcButton

    def __init__(
        self,
        *,
        mode: HitachiAcMode,
        temperature: int,
        fan: HitachiAcFanSpeed = HitachiAcFanSpeed.AUTO,
        power: bool = True,
        button: HitachiAcButton = HitachiAcButton.POWER,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Hitachi AC 344-bit IR command."""
        super().__init__(modulation=modulation)

        if not MIN_TEMP <= temperature <= MAX_TEMP:
            raise ValueError(
                f"temperature {temperature} out of range {MIN_TEMP}..{MAX_TEMP}"
            )

        if mode not in HitachiAcMode:
            raise ValueError(f"invalid mode: {mode}")
        if fan not in HitachiAcFanSpeed:
            raise ValueError(f"invalid fan speed: {fan}")
        if button not in HitachiAcButton:
            raise ValueError(f"invalid button action: {button}")

        self.mode = mode
        self.temperature = temperature
        self.fan = fan
        self.power = power
        self.button = button

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Hitachi AC 344-bit command."""
        payload = list(_BASE_SKELETON)

        payload[11] = self.button.value
        payload[12] = (~self.button.value) & 0xFF

        temp_val = self.temperature * 4
        payload[13] = temp_val
        payload[14] = (~temp_val) & 0xFF

        mode_fan_val = (self.fan.value << 4) | self.mode.value
        payload[25] = mode_fan_val
        payload[26] = (~mode_fan_val) & 0xFF

        power_val = 0xF1 if self.power else 0xE1
        payload[27] = power_val
        payload[28] = (~power_val) & 0xFF

        timings: list[int] = [_HDR_MARK, -_HDR_SPACE]
        for byte_val in payload:
            for bit_idx in range(8):
                bit = (byte_val >> bit_idx) & 1
                timings.append(_BIT_MARK)
                timings.append(-(_BIT_ONE_SPACE if bit else _BIT_ZERO_SPACE))

        timings.append(_FOOTER_MARK)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a HitachiAc344Command."""
        if len(timings) < 691:
            return None

        if not _is_close(timings[0], _HDR_MARK) or not _is_close(
            -timings[1], _HDR_SPACE
        ):
            return None

        payload: list[int] = []
        for byte_idx in range(43):
            byte_val = 0
            for bit_idx in range(8):
                t_idx = 2 + 2 * (byte_idx * 8 + bit_idx)
                bit = _decode_bit(timings[t_idx], -timings[t_idx + 1])
                if bit is None:
                    return None
                byte_val |= bit << bit_idx
            payload.append(byte_val)

        if not _is_close(timings[690], _FOOTER_MARK):
            return None

        if payload[0:9] != [0x01, 0x10, 0x00, 0x40, 0xBF, 0xFF, 0x00, 0xCC, 0x33]:
            return None

        for i in range(9, 43, 2):
            if payload[i + 1] != (~payload[i]) & 0xFF:
                return None

        button_val = payload[11]
        temp_val = payload[13]
        mode_fan_val = payload[25]
        power_val = payload[27]

        if temp_val % 4 != 0:
            return None
        temperature = temp_val // 4
        if not MIN_TEMP <= temperature <= MAX_TEMP:
            return None

        mode_val = mode_fan_val & 0x0F
        fan_val = mode_fan_val >> 4

        if power_val == 0xF1:
            power = True
        elif power_val == 0xE1:
            power = False
        else:
            return None

        try:
            button = HitachiAcButton(button_val)
            mode = HitachiAcMode(mode_val)
            fan = HitachiAcFanSpeed(fan_val)
        except ValueError:
            return None

        return cls(
            mode=mode,
            temperature=temperature,
            fan=fan,
            power=power,
            button=button,
        )
