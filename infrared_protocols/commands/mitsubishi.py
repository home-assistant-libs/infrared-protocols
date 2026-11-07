"""Mitsubishi Electric 144-bit state commands."""

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from ._climate import ClimatePacket
from ._climate_fields import temperature_value
from ._timing import PulseTiming


class MitsubishiMode(IntEnum):
    """Mitsubishi operating modes."""

    HEAT = 0x8
    DRY = 0x10
    COOL = 0x18
    AUTO = 0x20
    FAN_ONLY = 0x38


class MitsubishiFanSpeed(IntEnum):
    """Native levels; three-speed units use 1/2/3, four-speed units 1/2/3/4."""

    AUTO = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    QUIET = 5


@dataclass(frozen=True, kw_only=True)
class MitsubishiState:
    """Settings carried by a Mitsubishi packet, using its native enums and units."""

    power: bool | None = None
    mode: MitsubishiMode | None = None
    temperature: float | None = None
    fan: MitsubishiFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None


class MitsubishiPreset(StrEnum):
    """Optional model-dependent operating presets."""

    NONE = "none"
    ECONO_COOL = "econo_cool"
    NIGHT = "night"
    POWERFUL = "powerful"


class MitsubishiCommand(ClimatePacket[MitsubishiState]):
    """Two identical 18-byte packets form one transmission."""

    HEADER = (3500, -1700)
    TIMING = PulseTiming(430, 390, 1250)
    LENGTH = 18
    COPIES = 2
    REPEAT_GAP = 17500

    def __init__(
        self,
        *,
        mode: MitsubishiMode,
        temperature: float | None = None,
        power: bool = True,
        fahrenheit_compatibility: bool = False,
        fan: MitsubishiFanSpeed = MitsubishiFanSpeed.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        vertical_position: int = 0,
        horizontal_position: int = 3,
        dual_vanes: bool = False,
        preset: MitsubishiPreset = MitsubishiPreset.NONE,
    ) -> None:
        """Build a state with half degrees, native fan levels and vane positions.

        Vertical positions are 0 (auto) through 5 (down). Horizontal positions
        are 1..5 (left to right) or 8 (split). The native swing positions 7
        (vertical) and 12 (horizontal) require the matching swing flag.
        Dry mode sends 24 °C.
        With fahrenheit_compatibility=True, temperature is 61..88 °F and uses
        the remote's lookup table. Decoded state reports the wire Celsius value.
        """
        if temperature is not None:
            temperature_value(
                temperature,
                61 if fahrenheit_compatibility else 16,
                88 if fahrenheit_compatibility else 31,
                1 if fahrenheit_compatibility else 0.5,
            )
        if mode == MitsubishiMode.DRY:
            temperature = 24
        elif temperature is None:
            raise ValueError("temperature is required for this mode")
        elif fahrenheit_compatibility:
            codes = (
                0x00, 0x10, 0x01, 0x11, 0x02, 0x12, 0x03, 0x04,
                0x05, 0x15, 0x06, 0x16, 0x07, 0x17, 0x08, 0x18,
                0x09, 0x19, 0x0A, 0x1A, 0x0B, 0x1B, 0x0C, 0x1C,
                0x0D, 0x1D, 0x0E, 0x0F,
            )  # fmt: skip
            code = codes[int(temperature) - 61]
            temperature = 16 + (code & 15) + (0.5 if code & 16 else 0)
        if (
            not 0 <= vertical_position <= 5 and not (swing_v and vertical_position == 7)
        ) or (
            horizontal_position not in (1, 2, 3, 4, 5, 8)
            and not (swing_h and horizontal_position == 12)
        ):
            raise ValueError("invalid Mitsubishi vane position")
        mode_code = int(MitsubishiMode(mode))
        temp_code = int(temperature) - 16 | (16 if temperature % 1 else 0)
        mode_aux = {MitsubishiMode.HEAT: 0, MitsubishiMode.DRY: 2}.get(mode, 6)
        vane_fan = (
            int(MitsubishiFanSpeed(fan))
            | ((7 if swing_v else vertical_position) << 3)
            | 64
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
    def preset(self) -> MitsubishiPreset:
        """Return the native operating preset."""
        if self.data[14] == 0xC1:
            return MitsubishiPreset.NIGHT
        if self.data[14] & 32:
            return MitsubishiPreset.ECONO_COOL
        if self.data[15] & 8:
            return MitsubishiPreset.POWERFUL
        return MitsubishiPreset.NONE

    @property
    def vertical_position(self) -> int:
        """Return the native vertical position, including 7 for swing."""
        return self.data[9] >> 3 & 7

    @property
    def horizontal_position(self) -> int:
        """Return the native horizontal position, including 12 for swing."""
        return self.data[8] >> 4

    @property
    def dual_vanes(self) -> bool | None:
        """Return True for a non-auto second vane, otherwise its presence is unknown."""
        return True if self.data[16] & 0x38 else None

    @classmethod
    def parse(cls, data: bytes) -> MitsubishiState:
        """Check packet identity and recover common state fields."""
        cls._validate_packet(data)
        if data[:5] != bytes([0x23, 0xCB, 0x26, 1, 0]):
            raise ValueError("invalid Mitsubishi signature")
        temperature = 16 + (data[7] & 15) + (0.5 if data[7] & 16 else 0)
        temperature_value(temperature, 16, 31.5, 0.5)
        fan = MitsubishiFanSpeed(data[9] & 7)
        mode = MitsubishiMode(data[6] & 0x38)
        return MitsubishiState(
            power=bool(data[5] & 32),
            mode=mode,
            temperature=None if mode == MitsubishiMode.DRY else temperature,
            fan=fan,
            swing_v=data[9] & 0x38 == 0x38,
            swing_h=data[8] & 0xF0 == 0xC0,
        )
