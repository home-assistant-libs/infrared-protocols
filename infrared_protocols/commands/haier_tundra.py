"""Haier Tundra 112-bit state and button commands."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import temperature_value
from .haier import HaierCommand


class HaierTundraMode(IntEnum):
    """HaierTundra operating modes."""

    AUTO = 0x0
    COOL = 0x1
    DRY = 0x2
    HEAT = 0x4
    FAN_ONLY = 0x6


class HaierTundraFanSpeed(IntEnum):
    """HaierTundra fan speeds."""

    AUTO = 0x5
    HIGH = 0x1
    MEDIUM = 0x2
    LOW = 0x3


@dataclass(frozen=True, kw_only=True)
class HaierTundraState:
    """Settings carried by a HaierTundra packet, using its native enums and units."""

    power: bool | None = None
    mode: HaierTundraMode | None = None
    temperature: int | None = None
    fan: HaierTundraFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None


class HaierUnit(IntEnum):
    """Unit identifiers for paired installations."""

    A = 0xA6
    B = 0x59


class HaierButton(IntEnum):
    """Button recorded in the full state packet."""

    TEMPERATURE_UP = 0
    TEMPERATURE_DOWN = 1
    SWING_V = 2
    SWING_H = 3
    FAN = 4
    POWER = 5
    MODE = 6
    HEALTH = 7
    TURBO_QUIET = 8
    SLEEP = 11
    TIMER = 16
    LIGHT_TOGGLE = 21
    SELF_CLEAN = 25


class HaierTundraCommand(ClimatePacket[HaierTundraState]):
    """Tundra state; LIGHT_TOGGLE changes the light without reporting its state."""

    HEADER = HaierCommand.HEADER
    TIMING = HaierCommand.TIMING
    LENGTH = 14
    LSB = False

    def __init__(
        self,
        *,
        mode: HaierTundraMode | None,
        temperature: int,
        power: bool = True,
        fan: HaierTundraFanSpeed = HaierTundraFanSpeed.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        unit: HaierUnit = HaierUnit.A,
        button: HaierButton = HaierButton.POWER,
        health: bool = False,
        quiet: bool = False,
        turbo: bool = False,
    ) -> None:
        """Build a state for 16..30 °C with optional health, quiet or turbo."""
        if power:
            HaierTundraMode(mode)
        temp = temperature_value(temperature, 16, 30)
        if (
            quiet
            and turbo
            or (quiet or turbo)
            and (not power or mode not in (HaierTundraMode.COOL, HaierTundraMode.HEAT))
        ):
            raise ValueError(
                "quiet and turbo are exclusive and require cooling or heating"
            )
        vertical = 12 if swing_v else 10 if mode == HaierTundraMode.HEAT else 2
        data = bytes(
            [
                HaierUnit(unit),
                temp << 4 | (vertical if power else 0),
                0xE0 if swing_h else 0,
                2 if health else 0,
                64 if power else 0,
                int(HaierTundraFanSpeed(fan)) << 5,
                (128 if quiet else 0) | (64 if turbo else 0),
                int(HaierTundraMode(mode)) << 5 if power else 0,
                0,
                0,
                16 if button == HaierButton.SELF_CLEAN else 0,
                0,
                HaierButton(button),
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @property
    def health(self) -> bool:
        """Return whether the health function is enabled."""
        return bool(self.data[3] & 2)

    @property
    def quiet(self) -> bool:
        """Return whether quiet operation is selected."""
        return bool(self.data[6] & 128)

    @property
    def turbo(self) -> bool:
        """Return whether turbo operation is selected."""
        return bool(self.data[6] & 64)

    @property
    def button(self) -> HaierButton:
        """Return the transmitted button."""
        return HaierButton(self.data[12])

    @property
    def unit(self) -> HaierUnit:
        """Return the unit identifier."""
        return HaierUnit(self.data[0])

    @classmethod
    def parse(cls, data: bytes) -> HaierTundraState:
        """Read common state after checksum and identifier validation."""
        cls._validate_packet(data)
        HaierUnit(data[0])
        HaierButton(data[12])
        temperature = (data[1] >> 4) + 16
        temperature_value(temperature, 16, 30)
        return HaierTundraState(
            power=bool(data[4] & 64),
            mode=HaierTundraMode(data[7] >> 5) if bool(data[4] & 64) else None,
            temperature=temperature,
            fan=HaierTundraFanSpeed(data[5] >> 5),
            swing_v=(data[1] & 15 == 12) if data[4] & 64 else None,
            swing_h=data[2] >> 5 == 7,
        )
