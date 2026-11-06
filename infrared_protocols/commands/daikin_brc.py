"""Daikin BRC4C commands, with sub-unit addressing and native temperature variants."""

from typing import ClassVar

from ._climate import ClimatePacket, FramePart
from ._climate_fields import decoded, selection, temperature_value
from ._daikin import checked, validate_sections
from ._timing import PulseTiming
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {
    ClimateMode.AUTO: 3,
    ClimateMode.COOL: 2,
    ClimateMode.HEAT: 1,
    ClimateMode.DRY: 7,
    ClimateMode.FAN_ONLY: 0,
}
_FANS = {ClimateFan.LOW: 1, ClimateFan.MEDIUM: 3, ClimateFan.HIGH: 5}


class DaikinBrcCommand(ClimatePacket):
    """BRC Celsius remote; fan has three fixed speeds and swing drives both axes.

    Decoding requires all sections in one capture. Configure the receiver idle
    timeout above 29.41 ms, or join captures with their measured intervening gaps.
    A default 10 ms ESPHome receiver splits this packet; pass the consecutive
    bursts from one press to from_raw_captures() to decode it.
    """

    HEADER = (5070, -2140)
    TIMING = PulseTiming(370, 710, 1780)
    LENGTH = 22
    PARTS = (FramePart(7, HEADER, 29410), FramePart(15, HEADER))
    FAHRENHEIT: ClassVar[bool] = False

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: int,
        power: bool = True,
        fan: ClimateFan = ClimateFan.LOW,
        swing: bool = False,
        sub_unit: int = 0,
        mode_button: bool = False,
    ) -> None:
        """Build a state in 16..32 °C, or 60..90 °F for the Fahrenheit subclass."""
        selection(mode, _MODES)
        temperature_value(
            temperature, 60 if self.FAHRENHEIT else 16, 90 if self.FAHRENHEIT else 32
        )
        if not 0 <= sub_unit <= 5:
            raise ValueError("sub_unit must be 0..5")
        no_temp = power and mode in (ClimateMode.DRY, ClimateMode.FAN_ONLY)
        temp = (
            (72 if self.FAHRENHEIT else 16)
            if no_temp
            else temperature
            if self.FAHRENHEIT
            else (temperature - 9) * 2
        )
        header = bytes([0x11, 0xDA, 0x17, 0x18 | sub_unit])
        preamble = checked(header + bytes([4, 0]))
        alt = (
            {ClimateMode.DRY: 0x23, ClimateMode.FAN_ONLY: 0x63}.get(mode, 0x73)
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
    def sub_unit(self) -> int:
        """Return the addressed indoor unit."""
        return self.data[3] & 7

    @property
    def mode_button(self) -> bool:
        """Return whether the mode button triggered this packet."""
        return bool(self.data[13] & 4)

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
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
        temperature = (data[17] - 32) * 5 / 9 if cls.FAHRENHEIT else data[17] / 2 + 9
        return ClimateState(
            power=power,
            mode=mode,
            temperature=None
            if power and mode in (ClimateMode.DRY, ClimateMode.FAN_ONLY)
            else temperature,
            fan=decoded(data[18] >> 4, _FANS),
            swing_v=data[18] & 15 == 5,
            swing_h=data[18] & 15 == 5,
        )


class DaikinBrcFahrenheitCommand(DaikinBrcCommand):
    """BRC with native Fahrenheit input and Celsius decoded state.

    The constructor takes whole degrees Fahrenheit; state.temperature is the
    exact Celsius conversion. The remote variant is configuration, not a flag.
    """

    FAHRENHEIT = True
