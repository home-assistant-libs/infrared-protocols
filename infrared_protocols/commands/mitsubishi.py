"""Mitsubishi Electric 144-bit state commands."""

from enum import IntEnum, StrEnum

from ._climate import ClimatePacket
from ._timing import PulseTiming
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
    decoded,
    selection,
    temperature_value,
)

_MODES = {
    ClimateMode.HEAT: 8,
    ClimateMode.DRY: 16,
    ClimateMode.COOL: 24,
    ClimateMode.AUTO: 32,
    ClimateMode.FAN_ONLY: 56,
}


class MitsubishiFan(IntEnum):
    """Native levels; three-speed units use 1/2/3, four-speed units 1/2/3/4."""

    AUTO = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    QUIET = 5


class MitsubishiPreset(StrEnum):
    """Optional model-dependent operating presets."""

    NONE = "none"
    ECONO_COOL = "econo_cool"
    NIGHT = "night"
    POWERFUL = "powerful"


class MitsubishiCommand(ClimatePacket):
    """Two identical 18-byte packets form one transmission."""

    HEADER = (3500, -1700)
    TIMING = PulseTiming(430, 390, 1250)
    LENGTH = 18
    COPIES = 2
    REPEAT_GAP = 17500

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fahrenheit: bool = False,
        fan: MitsubishiFan = MitsubishiFan.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        vertical_position: int = 0,
        horizontal_position: int = 3,
        dual_vanes: bool = False,
        preset: MitsubishiPreset = MitsubishiPreset.NONE,
    ) -> None:
        """Build a state with half degrees, native fan levels and vane positions.

        Vertical positions are 0 (auto) through 5 (down). Horizontal positions
        are 1..5 (left to right) or 8 (split). Dry mode sends 24 °C.
        With fahrenheit=True, temperature is 61..88 °F and uses the remote's
        lookup table. Decoded state reports the corresponding wire Celsius value.
        """
        if fahrenheit:
            temperature_value(temperature, 61, 88)
            codes = (
                0x00, 0x10, 0x01, 0x11, 0x02, 0x12, 0x03, 0x04,
                0x05, 0x15, 0x06, 0x16, 0x07, 0x17, 0x08, 0x18,
                0x09, 0x19, 0x0A, 0x1A, 0x0B, 0x1B, 0x0C, 0x1C,
                0x0D, 0x1D, 0x0E, 0x0F,
            )  # fmt: skip
            code = codes[int(temperature) - 61]
            temperature = 16 + (code & 15) + (0.5 if code & 16 else 0)
        else:
            temperature_value(temperature, 16, 31, 0.5)
        if not 0 <= vertical_position <= 5 or horizontal_position not in (
            1,
            2,
            3,
            4,
            5,
            8,
        ):
            raise ValueError("invalid Mitsubishi vane position")
        mode_code = selection(mode, _MODES)
        effective_temp = 24 if mode == ClimateMode.DRY else temperature
        temp_code = int(effective_temp) - 16 | (16 if effective_temp % 1 else 0)
        mode_aux = {ClimateMode.HEAT: 0, ClimateMode.DRY: 2}.get(mode, 6)
        vane_fan = (
            int(MitsubishiFan(fan)) | ((7 if swing_v else vertical_position) << 3) | 64
        )
        preset = MitsubishiPreset(preset)
        eco, boost = 0, 0
        if preset == MitsubishiPreset.ECONO_COOL:
            mode_code, mode_aux, eco = 24 | 64, 6, 32
        elif preset == MitsubishiPreset.NIGHT:
            vane_fan, eco = 0, 0xC1
        elif preset == MitsubishiPreset.POWERFUL:
            mode_code |= 64
            boost = 8
        data = bytes(
            [
                0x23,
                0xCB,
                0x26,
                1,
                0,
                32 if power else 0,
                mode_code,
                temp_code,
                mode_aux | (0xC0 if swing_h else horizontal_position << 4),
                vane_fan,
                0,
                0,
                0,
                0,
                eco,
                boost,
                vane_fan & 0x38 if dual_vanes else 0,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @property
    def fan(self) -> MitsubishiFan:
        """Return the native fan level without assuming a unit's speed count."""
        return MitsubishiFan(self.data[9] & 7)

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Check packet identity and recover common state fields."""
        super().parse(data)
        if data[:5] != bytes([0x23, 0xCB, 0x26, 1, 0]):
            raise ValueError("invalid Mitsubishi signature")
        temperature = 16 + (data[7] & 15) + (0.5 if data[7] & 16 else 0)
        temperature_value(temperature, 16, 31.5, 0.5)
        fan = MitsubishiFan(data[9] & 7)
        common_fan = {
            MitsubishiFan.AUTO: ClimateFan.AUTO,
            MitsubishiFan.LEVEL_1: ClimateFan.LOW,
            MitsubishiFan.QUIET: ClimateFan.QUIET,
        }.get(fan)
        return ClimateState(
            power=bool(data[5] & 32),
            mode=decoded(data[6] & 0x38, _MODES),
            temperature=temperature,
            fan=common_fan,
            swing_v=data[9] & 0x38 == 0x38,
            swing_h=data[8] & 0xF0 == 0xC0,
        )
