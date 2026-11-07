"""Airton SMVH09B state commands and flap positions."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import decoded, selection, temperature_value
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
    LOW = 0x1
    MEDIUM = 0x3
    HIGH = 0x5


@dataclass(frozen=True, kw_only=True)
class AirtonState:
    """Settings carried by an Airton packet, using its native enums and units."""

    power: bool | None = None
    mode: AirtonMode | None = None
    temperature: float | None = None
    fan: AirtonFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None
    is_fahrenheit: bool = False


_MODES = {
    AirtonMode.AUTO: 0,
    AirtonMode.COOL: 1,
    AirtonMode.DRY: 2,
    AirtonMode.FAN_ONLY: 3,
    AirtonMode.HEAT: 4,
}
_FANS = {
    AirtonFanSpeed.AUTO: 0,
    AirtonFanSpeed.LOW: 1,
    AirtonFanSpeed.MEDIUM: 3,
    AirtonFanSpeed.HIGH: 5,
}


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
        temperature: float,
        power: bool = True,
        fan: AirtonFanSpeed = AirtonFanSpeed.AUTO,
        direction: AirtonDirection = AirtonDirection.OFF,
        display: bool = True,
        sleep: bool = False,
    ) -> None:
        """Build a state; automatic mode uses 25 °C and disallows sleep."""
        temp = temperature_value(temperature, 16, 31)
        if sleep and mode in (AirtonMode.AUTO, AirtonMode.FAN_ONLY):
            raise ValueError("sleep is unavailable in automatic and fan-only modes")
        settings = 0x40 | (128 if display else 0) | (2 if sleep else 0)
        settings |= 16 if power and mode == AirtonMode.HEAT else 0
        settings |= 4 if not power or mode != AirtonMode.AUTO else 0
        data = bytes(
            [
                0xD3,
                0x11,
                selection(mode, _MODES)
                | (8 if power else 0)
                | selection(fan, _FANS) << 4,
                9 if power and mode == AirtonMode.AUTO else temp,
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

    @classmethod
    def parse(cls, data: bytes) -> AirtonState:
        """Validate and read common state; finer fan levels remain in data."""
        cls._validate_packet(data)
        if data[:2] != b"\xd3\x11":
            raise ValueError("invalid Airton signature")
        direction = AirtonDirection(data[4] & 15)
        fan_code = (data[2] >> 4) & 7
        fan_code = {2: 1, 4: 5}.get(fan_code, fan_code)
        power = bool(data[2] & 8)
        mode = decoded(data[2] & 7, _MODES)
        return AirtonState(
            power=power,
            mode=mode,
            temperature=None
            if power and mode == AirtonMode.AUTO
            else (data[3] & 15) + 16,
            fan=decoded(fan_code, _FANS),
            swing_v=direction == AirtonDirection.SWING,
        )
