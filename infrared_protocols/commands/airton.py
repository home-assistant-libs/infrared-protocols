"""Airton SMVH09B state commands and flap positions."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import temperature_value
from ._timing import PulseTiming


class AirtonMode(IntEnum):
    """Airton operating modes."""

    AUTO = 0x0
    COOL = 0x1
    DRY = 0x2
    FAN_ONLY = 0x3
    HEAT = 0x4


class AirtonFanSpeed(IntEnum):
    """Airton fan speeds."""

    AUTO = 0x0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5


@dataclass(frozen=True, kw_only=True)
class AirtonState:
    """Settings carried by an Airton packet, using its native enums and units."""

    power: bool | None = None
    mode: AirtonMode | None = None
    temperature: int | None = None
    fan: AirtonFanSpeed | None = None
    swing_v: bool | None = None


class AirtonDirection(IntEnum):
    """Vertical flap settings."""

    OFF = 0
    SWING = 1
    UP = 2
    MIDDLE_UP = 3
    MIDDLE = 4
    MIDDLE_DOWN = 5
    DOWN = 6


class AirtonCommand(ClimatePacket[AirtonState]):
    """Full Airton state; mode is retained when power is off."""

    HEADER = (6630, -3350)
    TIMING = PulseTiming(400, 430, 1260)
    LENGTH = 7
    GAP = 100000

    def __init__(
        self,
        *,
        mode: AirtonMode,
        temperature: int | None = None,
        power: bool = True,
        fan: AirtonFanSpeed = AirtonFanSpeed.AUTO,
        direction: AirtonDirection = AirtonDirection.OFF,
        display: bool = True,
        sleep: bool = False,
        turbo: bool = False,
        economy: bool = False,
        health: bool = True,
    ) -> None:
        """Build a state; automatic mode uses 25 °C and disallows sleep."""
        temp = None if temperature is None else temperature_value(temperature, 16, 31)
        if power and mode == AirtonMode.AUTO:
            temp = 9
        if temp is None:
            raise ValueError("temperature is required for this mode")
        if sleep and mode in (AirtonMode.AUTO, AirtonMode.FAN_ONLY):
            raise ValueError("sleep is unavailable in automatic and fan-only modes")
        settings = (
            (64 if health else 0)
            | (128 if display else 0)
            | (2 if sleep else 0)
            | int(economy)
        )
        settings |= 16 if power and mode == AirtonMode.HEAT else 0
        settings |= 4 if not power or mode != AirtonMode.AUTO else 0
        data = bytes(
            [
                0xD3,
                0x11,
                int(AirtonMode(mode))
                | (8 if power else 0)
                | int(AirtonFanSpeed(fan)) << 4
                | (128 if turbo else 0),
                temp,
                AirtonDirection(direction),
                settings,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @staticmethod
    def checksum(data: bytes) -> int:
        """Return the Airton checksum."""
        return ((127 - sum(data)) & 255) ^ 0x2C

    @property
    def direction(self) -> AirtonDirection:
        """Return the flap position carried by this packet."""
        return AirtonDirection(self.data[4] & 15)

    @property
    def display(self) -> bool:
        """Return whether the display is enabled."""
        return bool(self.data[5] & 128)

    @property
    def sleep(self) -> bool:
        """Return whether sleep is enabled."""
        return bool(self.data[5] & 2)

    @property
    def turbo(self) -> bool:
        """Return the independent turbo bit carried by the remote."""
        return bool(self.data[2] & 128)

    @property
    def economy(self) -> bool:
        """Return the remote's economy bit."""
        return bool(self.data[5] & 1)

    @property
    def health(self) -> bool:
        """Return the remote's health bit."""
        return bool(self.data[5] & 64)

    @classmethod
    def parse(cls, data: bytes) -> AirtonState:
        """Validate and decode every native fan level."""
        cls._validate_packet(data)
        if data[:2] != b"\xd3\x11":
            raise ValueError("invalid Airton signature")
        direction = AirtonDirection(data[4] & 15)
        fan_code = (data[2] >> 4) & 7
        power = bool(data[2] & 8)
        mode = AirtonMode(data[2] & 7)
        return AirtonState(
            power=power,
            mode=mode,
            temperature=None
            if power and mode == AirtonMode.AUTO
            else (data[3] & 15) + 16,
            fan=AirtonFanSpeed(fan_code),
            swing_v=direction == AirtonDirection.SWING,
        )
