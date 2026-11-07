"""Ballu YKR-K/002E state commands."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import temperature_value
from ._timing import PulseTiming


class BalluMode(IntEnum):
    """Ballu operating modes."""

    AUTO = 0x0
    COOL = 0x1
    DRY = 0x2
    HEAT = 0x4
    FAN_ONLY = 0x6


class BalluFanSpeed(IntEnum):
    """Ballu fan speeds."""

    AUTO = 0x5
    HIGH = 0x1
    MEDIUM = 0x2
    LOW = 0x3


@dataclass(frozen=True, kw_only=True)
class BalluState:
    """Settings carried by a Ballu packet, using its native enums and units."""

    power: bool | None = None
    mode: BalluMode | None = None
    temperature: int | None = None
    fan: BalluFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None


class BalluCommand(ClimatePacket[BalluState]):
    """Ballu full-state command, with independent horizontal and vertical swing."""

    HEADER = (9000, -4500)
    TIMING = PulseTiming(575, 550, 1675)
    LENGTH = 13

    def __init__(
        self,
        *,
        mode: BalluMode | None,
        temperature: int,
        power: bool = True,
        fan: BalluFanSpeed = BalluFanSpeed.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
    ) -> None:
        """Build a state for 16..32 °C in whole degrees."""
        if power:
            BalluMode(mode)
        temp = temperature_value(temperature, 16, 32) + 8
        data = bytes(
            [
                0xC3,
                temp << 3 | (0 if swing_v else 7),
                0 if swing_h else 0xE0,
                0,
                int(BalluFanSpeed(fan)) << 5,
                0,
                int(BalluMode(mode)) << 5 if power else 0,
                0,
                0,
                0x20 if power else 0,
                0,
                0x1E,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @classmethod
    def parse(cls, data: bytes) -> BalluState:
        """Read the common state after validating the signature and checksum."""
        cls._validate_packet(data)
        if data[0] != 0xC3:
            raise ValueError("invalid Ballu signature")
        temperature = (data[1] >> 3) + 8
        temperature_value(temperature, 16, 32)
        return BalluState(
            power=bool(data[9] & 32),
            mode=BalluMode(data[6] >> 5) if bool(data[9] & 32) else None,
            temperature=temperature,
            fan=BalluFanSpeed(data[4] >> 5),
            swing_v=data[1] & 7 == 0,
            swing_h=data[2] & 0xE0 == 0,
        )
