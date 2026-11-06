"""Islandaire PTAC commands with native Fahrenheit set points."""

from ._climate import ClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {ClimateMode.HEAT: 1, ClimateMode.COOL: 3, ClimateMode.FAN_ONLY: 4}
_FANS = {ClimateFan.AUTO: 0, ClimateFan.LOW: 2, ClimateFan.HIGH: 4}


class IslandaireCommand(ClimatePacket):
    """Islandaire full state; common state exposes Celsius."""

    HEADER = (3608, -1520)
    TIMING = PulseTiming(560, 408, 1208)
    LENGTH = 14

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature_f: int,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
    ) -> None:
        """Build a state with a whole-degree 61..88 °F set point."""
        selection(mode, _MODES)
        temperature_value(temperature_f, 61, 88)
        data = bytes(
            [
                *([0x22] * 5),
                0x24 if power else 0x20,
                selection(mode, _MODES) if power else 3,
                temperature_f,
                selection(fan, _FANS),
                0,
                0,
                0,
                0,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @property
    def temperature_f(self) -> int:
        """Return the native Fahrenheit set point."""
        return self.data[7]

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Validate and decode the state, retaining timer fields in data."""
        super().parse(data)
        if data[:5] != bytes([0x22] * 5):
            raise ValueError("invalid Islandaire signature")
        temperature_value(data[7], 61, 88)
        fan_code = data[8] & ~0x40
        return ClimateState(
            power=bool(data[5] & 4),
            mode=decoded(data[6], _MODES) if bool(data[5] & 4) else None,
            temperature=(data[7] - 32) * 5 / 9,
            fan=decoded(2 if fan_code == 1 else fan_code, _FANS),
        )
