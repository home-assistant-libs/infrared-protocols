"""Airton SMVH09B state commands and flap positions."""

from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {
    ClimateMode.AUTO: 0,
    ClimateMode.COOL: 1,
    ClimateMode.DRY: 2,
    ClimateMode.FAN_ONLY: 3,
    ClimateMode.HEAT: 4,
}
_FANS = {
    ClimateFan.AUTO: 0,
    ClimateFan.LOW: 1,
    ClimateFan.MEDIUM: 3,
    ClimateFan.HIGH: 5,
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


class AirtonCommand(ClimatePacket):
    """Full Airton state; mode is retained when power is off."""

    HEADER = (6630, -3350)
    TIMING = PulseTiming(400, 430, 1260)
    LENGTH = 7
    GAP = 100000

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        direction: AirtonDirection = AirtonDirection.OFF,
        display: bool = True,
        sleep: bool = False,
    ) -> None:
        """Build a state; automatic mode uses 25 °C and disallows sleep."""
        temp = temperature_value(temperature, 16, 31)
        if sleep and mode in (ClimateMode.AUTO, ClimateMode.FAN_ONLY):
            raise ValueError("sleep is unavailable in automatic and fan-only modes")
        settings = 0x40 | (128 if display else 0) | (2 if sleep else 0)
        settings |= 16 if power and mode == ClimateMode.HEAT else 0
        settings |= 4 if not power or mode != ClimateMode.AUTO else 0
        data = bytes(
            [
                0xD3,
                0x11,
                selection(mode, _MODES)
                | (8 if power else 0)
                | selection(fan, _FANS) << 4,
                9 if power and mode == ClimateMode.AUTO else temp,
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
    def parse(cls, data: bytes) -> ClimateState:
        """Validate and read common state; finer fan levels remain in data."""
        super().parse(data)
        if data[:2] != b"\xd3\x11":
            raise ValueError("invalid Airton signature")
        direction = AirtonDirection(data[4] & 15)
        fan_code = (data[2] >> 4) & 7
        fan_code = {2: 1, 4: 5}.get(fan_code, fan_code)
        return ClimateState(
            power=bool(data[2] & 8),
            mode=decoded(data[2] & 7, _MODES),
            temperature=(data[3] & 15) + 16,
            fan=decoded(fan_code, _FANS),
            swing_v=direction == AirtonDirection.SWING,
        )
