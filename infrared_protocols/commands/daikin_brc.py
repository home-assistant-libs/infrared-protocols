"""Daikin BRC4C commands, with sub-unit addressing and native temperature variants."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket, FramePart
from ._climate_fields import decoded, selection, temperature_value
from ._daikin import checked, validate_sections
from ._timing import PulseTiming


class DaikinBrcMode(IntEnum):
    """DaikinBrc operating modes."""

    AUTO = 0x3
    COOL = 0x2
    HEAT = 0x1
    DRY = 0x7
    FAN_ONLY = 0x0


class DaikinBrcFanSpeed(IntEnum):
    """DaikinBrc fan speeds."""

    LOW = 0x1
    MEDIUM = 0x3
    HIGH = 0x5


@dataclass(frozen=True, kw_only=True)
class DaikinBrcState:
    """Settings carried by a DaikinBrc packet, using its native enums and units."""

    power: bool | None = None
    mode: DaikinBrcMode | None = None
    temperature: float | None = None
    fan: DaikinBrcFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None
    is_fahrenheit: bool = False


_MODES = {
    DaikinBrcMode.AUTO: 3,
    DaikinBrcMode.COOL: 2,
    DaikinBrcMode.HEAT: 1,
    DaikinBrcMode.DRY: 7,
    DaikinBrcMode.FAN_ONLY: 0,
}
_FANS = {
    DaikinBrcFanSpeed.LOW: 1,
    DaikinBrcFanSpeed.MEDIUM: 3,
    DaikinBrcFanSpeed.HIGH: 5,
}


class DaikinBrcCommand(ClimatePacket[DaikinBrcState]):
    """BRC remote with native Celsius or Fahrenheit and three fan speeds.

    Decoding requires all sections in one capture. Configure the receiver idle
    timeout above 29.41 ms, or join captures with their measured intervening gaps.
    A default 10 ms ESPHome receiver splits this packet; pass the consecutive
    bursts from one press to from_raw_captures() to decode it.
    """

    HEADER = (5070, -2140)
    TIMING = PulseTiming(370, 710, 1780)
    LENGTH = 22
    PARTS = (FramePart(7, HEADER, 29410), FramePart(15, HEADER))

    def __init__(
        self,
        *,
        mode: DaikinBrcMode,
        temperature: int,
        is_fahrenheit: bool = False,
        power: bool = True,
        fan: DaikinBrcFanSpeed = DaikinBrcFanSpeed.LOW,
        swing: bool = False,
        sub_unit: int = 0,
        mode_button: bool = False,
    ) -> None:
        """Build a state in 16..32 °C, or 60..90 °F with is_fahrenheit=True."""
        selection(mode, _MODES)
        temperature_value(
            temperature, 60 if is_fahrenheit else 16, 90 if is_fahrenheit else 32
        )
        if not 0 <= sub_unit <= 5:
            raise ValueError("sub_unit must be 0..5")
        no_temp = power and mode in (DaikinBrcMode.DRY, DaikinBrcMode.FAN_ONLY)
        temp = (
            (72 if is_fahrenheit else 16)
            if no_temp
            else temperature
            if is_fahrenheit
            else (temperature - 9) * 2
        )
        header = bytes([0x11, 0xDA, 0x17, 0x18 | sub_unit])
        preamble = checked(header + bytes([4, 0]))
        alt = (
            {DaikinBrcMode.DRY: 0x23, DaikinBrcMode.FAN_ONLY: 0x63}.get(mode, 0x73)
            if power
            else 0x73
        )
        state = header + bytes(
            [
                0,
                alt,
                4 if mode_button else 0,
                selection(mode, _MODES) << 4 | 1 if power else 0,
                0,
                0,
                temp,
                selection(fan, _FANS) << 4 | (5 if swing else 6),
                0,
                32,
            ]
        )
        super().__init__(data=preamble + checked(state))

    @property
    def is_fahrenheit(self) -> bool:
        """Return the native units identified by the temperature encoding."""
        return self.state.is_fahrenheit

    @property
    def temperature(self) -> int | None:
        """Return the native set point, excluding dry/fan-only placeholders."""
        if self.state.temperature is None:
            return None
        return self.data[17] if self.is_fahrenheit else self.data[17] // 2 + 9

    @property
    def sub_unit(self) -> int:
        """Return the addressed indoor unit."""
        return self.data[3] & 7

    @property
    def mode_button(self) -> bool:
        """Return whether the mode button triggered this packet."""
        return bool(self.data[13] & 4)

    @classmethod
    def parse(cls, data: bytes) -> DaikinBrcState:
        """Validate both sections and interpret temperature for this remote variant."""
        validate_sections(data, (7, 15), bytes([0x11, 0xDA, 0x17]))
        if (
            data[3] != data[10]
            or data[3] & 0xF8 != 0x18
            or data[3] & 7 > 5
            or data[4] != 4
            or data[11] != 0
        ):
            raise ValueError("invalid BRC sub-unit or frame type")
        power = bool(data[14] & 1)
        mode = decoded(data[14] >> 4, _MODES) if power else None
        is_fahrenheit = data[17] >= 60
        temperature_value(
            data[17] if is_fahrenheit else data[17] / 2 + 9,
            60 if is_fahrenheit else 16,
            90 if is_fahrenheit else 32,
        )
        temperature = data[17] if is_fahrenheit else data[17] // 2 + 9
        return DaikinBrcState(
            power=power,
            mode=mode,
            temperature=None
            if power and mode in (DaikinBrcMode.DRY, DaikinBrcMode.FAN_ONLY)
            else temperature,
            is_fahrenheit=is_fahrenheit,
            fan=decoded(data[18] >> 4, _FANS),
            swing_v=data[18] & 15 == 5,
            swing_h=data[18] & 15 == 5,
        )
