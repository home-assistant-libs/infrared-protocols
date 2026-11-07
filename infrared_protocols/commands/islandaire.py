"""Islandaire PTAC commands with native Fahrenheit set points."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import temperature_value
from ._timing import PulseTiming


class IslandaireMode(IntEnum):
    """Islandaire operating modes."""

    HEAT = 0x1
    COOL = 0x3
    FAN_ONLY = 0x4


class IslandaireFanSpeed(IntEnum):
    """Islandaire fan speeds."""

    AUTO = 0x0
    LOW_ALT = 0x1
    LOW = 0x2
    HIGH = 0x4


@dataclass(frozen=True, kw_only=True)
class IslandaireState:
    """Settings carried by an Islandaire packet, using its native enums and units."""

    power: bool | None = None
    mode: IslandaireMode | None = None
    temperature: int | None = None
    fan: IslandaireFanSpeed | None = None
    is_fahrenheit: bool = False


class IslandaireCommand(ClimatePacket[IslandaireState]):
    """Islandaire full state with native Fahrenheit temperatures."""

    HEADER = (3608, -1520)
    TIMING = PulseTiming(560, 408, 1208)
    LENGTH = 14

    def __init__(
        self,
        *,
        mode: IslandaireMode | None,
        temperature: int,
        is_fahrenheit: bool = True,
        power: bool = True,
        fan: IslandaireFanSpeed = IslandaireFanSpeed.AUTO,
    ) -> None:
        """Build a state with a whole-degree 61..88 °F set point."""
        if not is_fahrenheit:
            raise ValueError("this remote only supports Fahrenheit set points")
        if power:
            IslandaireMode(mode)
        temperature_value(temperature, 61, 88)
        data = bytes(
            [
                *([0x22] * 5),
                0x24 if power else 0x20,
                int(IslandaireMode(mode)) if power else 3,
                temperature,
                int(IslandaireFanSpeed(fan)),
                0,
                0,
                0,
                0,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @classmethod
    def parse(cls, data: bytes) -> IslandaireState:
        """Validate and decode the state, retaining timer fields in data."""
        cls._validate_packet(data)
        if data[:5] != bytes([0x22] * 5):
            raise ValueError("invalid Islandaire signature")
        temperature_value(data[7], 61, 88)
        fan_code = data[8] & ~0x40
        return IslandaireState(
            power=bool(data[5] & 4),
            mode=IslandaireMode(data[6]) if bool(data[5] & 4) else None,
            temperature=data[7],
            is_fahrenheit=True,
            fan=IslandaireFanSpeed(fan_code),
        )
