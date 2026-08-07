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
    0x01,
    0x10,
    0x00,
    0x40,
    0xBF,
    0xFF,
    0x00,
    0xCC,
    0x33,
    0xA5,
    0x5A,
    0x13,
    0xEC,
    0x68,
    0x97,
    0x00,
    0xFF,
    0x00,
    0xFF,
    0x00,
    0xFF,
    0x00,
    0xFF,
    0x00,
    0xFF,
    0x43,
    0xBC,
    0xF1,
    0x0E,
    0x00,
    0xFF,
    0x00,
    0xFF,
    0x80,
    0x7F,
    0x03,
    0xFC,
    0x04,
    0xFB,
    0x20,
    0xDF,
    0x00,
    0xFF,
]


class HitachiAcMode(IntEnum):
    """Hitachi AC operating mode."""

    FAN_ONLY = 1
    COOL = 3
    DRY = 5
    HEAT = 6
    AUTO = 7


class HitachiAcFanSpeed(IntEnum):
    """Hitachi AC fan speed."""

    SILENT = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    AUTO = 5


class HitachiAcSwingH(IntEnum):
    """Hitachi AC horizontal swing setting."""

    AUTO = 0
    RIGHT_MAX = 1
    RIGHT = 2
    MIDDLE = 3
    LEFT = 4
    LEFT_MAX = 5


class HitachiAcDisplay(IntEnum):
    """Hitachi AC display brightness setting."""

    BRIGHT = 0x00
    MEDIUM = 0x80
    DIM = 0xC0
    OFF = 0x40


class HitachiAcSomatosensory(IntEnum):
    """Hitachi AC somatosensory setting."""

    COMFORT = 0x00
    MOISTURIZING = 0x02


class HitachiAcMoldDuration(IntEnum):
    """Hitachi AC mold prevention duration."""

    MINS_10 = 0x00
    MINS_20 = 0x10
    MINS_30 = 0x20
    MINS_45 = 0x30
    MINS_60 = 0x08


class HitachiAcButton(IntEnum):
    """Hitachi AC action button identifier."""

    POWER = 0x13
    MODE = 0x41
    FAN = 0x42
    TEMPERATURE = 0x44
    TEMP_DOWN = 0x43
    TEMP_UP = 0x44
    SWING_V = 0x81
    SWING_H = 0x8C
    SLEEP = 0x31
    DISPLAY = 0xC9
    SOMATOSENSORY = 0xE1
    OFF_TIMER = 0x22
    ECO = 0xC1
    RAPID = 0x89
    CLEAN = 0xB9
    MOLD = 0xE2
    MOLD_TIME = 0xC0
    PM25 = 0x83
    CANCEL_TIMER = 0x24


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
    swing_v: bool
    swing_h: HitachiAcSwingH
    eco: bool
    display: HitachiAcDisplay
    somatosensory: HitachiAcSomatosensory
    off_timer_mins: int | None
    on_timer_mins: int | None
    timer_daily: bool
    mold_prevention: bool
    mold_duration: HitachiAcMoldDuration
    button: HitachiAcButton

    def __init__(
        self,
        *,
        mode: HitachiAcMode,
        temperature: int,
        fan: HitachiAcFanSpeed = HitachiAcFanSpeed.AUTO,
        power: bool = True,
        swing_v: bool = False,
        swing_h: HitachiAcSwingH = HitachiAcSwingH.MIDDLE,
        eco: bool = False,
        display: HitachiAcDisplay = HitachiAcDisplay.BRIGHT,
        somatosensory: HitachiAcSomatosensory = HitachiAcSomatosensory.COMFORT,
        off_timer_mins: int | None = None,
        on_timer_mins: int | None = None,
        timer_daily: bool = False,
        mold_prevention: bool = False,
        mold_duration: HitachiAcMoldDuration = HitachiAcMoldDuration.MINS_30,
        button: HitachiAcButton = HitachiAcButton.POWER,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Hitachi AC 344-bit IR command."""
        super().__init__(modulation=modulation)

        if mode == HitachiAcMode.AUTO:
            if not -3 <= temperature <= 3:
                raise ValueError(
                    f"temperature offset {temperature} out of range -3..3 for AUTO mode"
                )
        else:
            if not MIN_TEMP <= temperature <= MAX_TEMP:
                raise ValueError(
                    f"temperature {temperature} out of range {MIN_TEMP}..{MAX_TEMP}"
                )

        if mode not in HitachiAcMode:
            raise ValueError(f"invalid mode: {mode}")
        if fan not in HitachiAcFanSpeed:
            raise ValueError(f"invalid fan speed: {fan}")
        if swing_h not in HitachiAcSwingH:
            raise ValueError(f"invalid swing_h position: {swing_h}")
        if display not in HitachiAcDisplay:
            raise ValueError(f"invalid display brightness: {display}")
        if somatosensory not in HitachiAcSomatosensory:
            raise ValueError(f"invalid somatosensory setting: {somatosensory}")
        if mold_duration not in HitachiAcMoldDuration:
            raise ValueError(f"invalid mold duration setting: {mold_duration}")
        if button not in HitachiAcButton:
            raise ValueError(f"invalid button action: {button}")

        if off_timer_mins is not None:
            if not 60 <= off_timer_mins <= 1440:
                raise ValueError(
                    f"off timer duration {off_timer_mins} out of range 60..1440 mins"
                )

        if on_timer_mins is not None:
            if not 60 <= on_timer_mins <= 1440:
                raise ValueError(
                    f"on timer duration {on_timer_mins} out of range 60..1440 mins"
                )
            if on_timer_mins % 2 != 0:
                raise ValueError(
                    f"on timer duration {on_timer_mins} must be a multiple of 2"
                )

        self.mode = mode
        self.temperature = temperature
        self.fan = fan
        self.power = power
        self.swing_v = swing_v
        self.swing_h = swing_h
        self.eco = eco
        self.display = display
        self.somatosensory = somatosensory
        self.off_timer_mins = off_timer_mins
        self.on_timer_mins = on_timer_mins
        self.timer_daily = timer_daily
        self.mold_prevention = mold_prevention
        self.mold_duration = mold_duration
        self.button = button

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Hitachi AC 344-bit command."""
        payload = list(_BASE_SKELETON)

        payload[11] = self.button.value
        payload[12] = (~self.button.value) & 0xFF

        if self.mode == HitachiAcMode.AUTO:
            temp_val = 4 + self.temperature
        else:
            temp_val = self.temperature * 4
        payload[13] = temp_val
        payload[14] = (~temp_val) & 0xFF

        mode_fan_val = (self.fan.value << 4) | self.mode.value
        payload[25] = mode_fan_val
        payload[26] = (~mode_fan_val) & 0xFF

        power_val = 0xF1 if self.power else 0xE1
        if self.eco:
            power_val |= 0x04
        payload[27] = power_val
        payload[28] = (~power_val) & 0xFF

        # Timers encoding
        byte23_val = _BASE_SKELETON[23] & ~0xB0  # clear bits 4, 5, 7

        if self.off_timer_mins is not None:
            byte23_val |= 0x10
            timer_val = self.off_timer_mins << 4
            payload[17] = timer_val & 0xFF
            payload[18] = (~payload[17]) & 0xFF
            payload[19] = (timer_val >> 8) & 0xFF
            payload[20] = (~payload[19]) & 0xFF
        else:
            payload[17] = 0x00
            payload[18] = 0xFF
            payload[19] = 0x00
            payload[20] = 0xFF

        if self.on_timer_mins is not None:
            byte23_val |= 0x20
            on_val = self.on_timer_mins >> 1
            payload[21] = on_val & 0xFF
            payload[22] = (~payload[21]) & 0xFF
            byte23_val = (byte23_val & 0xF0) | ((on_val >> 8) & 0x0F)
        else:
            payload[21] = 0x00
            payload[22] = 0xFF
            byte23_val &= 0xF0

        if self.timer_daily:
            byte23_val |= 0x80

        payload[23] = byte23_val
        payload[24] = (~byte23_val) & 0xFF

        byte35_val = (_BASE_SKELETON[35] & 0xF8) | self.swing_h.value
        payload[35] = byte35_val
        payload[36] = (~byte35_val) & 0xFF

        # Byte 37 has display, swing V, somatosensory, and mold prevention
        # Note: swing_v and mold_duration share bit 5 (0x20).
        # If mold_prevention is active, bit 5 represents mold_duration.
        # When mold_prevention is inactive, bit 5 represents swing_v.
        byte37_val = (
            (_BASE_SKELETON[37] & 0x06) | self.somatosensory.value | self.display.value
        )
        if self.mold_prevention:
            byte37_val |= 0x01
            byte37_val |= self.mold_duration.value
        elif not self.swing_v:
            byte37_val |= 0x20

        payload[37] = byte37_val
        payload[38] = (~byte37_val) & 0xFF

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

        mode_val = mode_fan_val & 0x0F
        fan_val = mode_fan_val >> 4

        if mode_val == HitachiAcMode.AUTO:
            temperature = temp_val - 4
            if not -3 <= temperature <= 3:
                return None
        else:
            if temp_val % 4 != 0:
                return None
            temperature = temp_val // 4
            if not MIN_TEMP <= temperature <= MAX_TEMP:
                return None

        eco = (power_val & 0x04) != 0
        power_state_val = power_val & ~0x04
        if power_state_val == 0xF1:
            power = True
        elif power_state_val == 0xE1:
            power = False
        else:
            return None

        # Timers decoding
        byte23_val = payload[23]
        timer_daily = (byte23_val & 0x80) != 0

        if (byte23_val & 0x10) != 0:
            timer_val = payload[17] | (payload[19] << 8)
            off_timer_mins = timer_val >> 4
            if not 60 <= off_timer_mins <= 1440:
                return None
        else:
            off_timer_mins = None

        if (byte23_val & 0x20) != 0:
            on_val = payload[21] | ((byte23_val & 0x0F) << 8)
            on_timer_mins = on_val << 1
            if not 60 <= on_timer_mins <= 1440:
                return None
        else:
            on_timer_mins = None

        swing_h_val = payload[35] & 0x07

        # Byte 37 has display, swing V, somatosensory, and mold prevention
        byte37_val = payload[37]
        swing_v = (byte37_val & 0x20) != 0
        somatosensory_val = byte37_val & 0x02
        display_val = byte37_val & 0xC0
        mold_prevention = (byte37_val & 0x01) != 0
        if mold_prevention:
            swing_v = False
            mold_duration_val = byte37_val & 0x38
        else:
            swing_v = (byte37_val & 0x20) == 0
            mold_duration_val = 0x20  # default to MINS_30

        try:
            button = HitachiAcButton(button_val)
            mode = HitachiAcMode(mode_val)
            fan = HitachiAcFanSpeed(fan_val)
            swing_h = HitachiAcSwingH(swing_h_val)
            display = HitachiAcDisplay(display_val)
            somatosensory = HitachiAcSomatosensory(somatosensory_val)
            mold_duration = HitachiAcMoldDuration(mold_duration_val)
        except ValueError:
            return None

        return cls(
            mode=mode,
            temperature=temperature,
            fan=fan,
            power=power,
            swing_v=swing_v,
            swing_h=swing_h,
            eco=eco,
            display=display,
            somatosensory=somatosensory,
            off_timer_mins=off_timer_mins,
            on_timer_mins=on_timer_mins,
            timer_daily=timer_daily,
            mold_prevention=mold_prevention,
            mold_duration=mold_duration,
            button=button,
        )
