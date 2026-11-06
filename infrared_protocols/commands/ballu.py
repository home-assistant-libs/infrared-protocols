"""Ballu YKR-K/002E state commands."""

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
    ClimateMode.HEAT: 4,
    ClimateMode.FAN_ONLY: 6,
}
_FANS = {
    ClimateFan.AUTO: 5,
    ClimateFan.HIGH: 1,
    ClimateFan.MEDIUM: 2,
    ClimateFan.LOW: 3,
}


class BalluCommand(ClimatePacket):
    """Ballu full-state command, with independent horizontal and vertical swing."""

    HEADER = (9000, -4500)
    TIMING = PulseTiming(575, 550, 1675)
    LENGTH = 13

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
    ) -> None:
        """Build a state for 16..32 °C in whole degrees."""
        selection(mode, _MODES)
        temp = temperature_value(temperature, 16, 32) + 8
        data = bytes(
            [
                0xC3,
                temp << 3 | (0 if swing_v else 7),
                0 if swing_h else 0xE0,
                0,
                selection(fan, _FANS) << 5,
                0,
                selection(mode, _MODES) << 5 if power else 0,
                0,
                0,
                0x20 if power else 0,
                0,
                0x1E,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Read the common state after validating the signature and checksum."""
        super().parse(data)
        if data[0] != 0xC3:
            raise ValueError("invalid Ballu signature")
        temperature = (data[1] >> 3) + 8
        temperature_value(temperature, 16, 32)
        return ClimateState(
            power=bool(data[9] & 32),
            mode=decoded(data[6] >> 5, _MODES) if bool(data[9] & 32) else None,
            temperature=temperature,
            fan=decoded(data[4] >> 5, _FANS),
            swing_v=data[1] & 7 == 0,
            swing_h=data[2] & 0xE0 == 0,
        )
