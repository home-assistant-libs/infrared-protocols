"""DeLonghi ARC43xxx portable air-conditioner state commands."""

from ._climate import ClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {
    ClimateMode.COOL: 0,
    ClimateMode.DRY: 2,
    ClimateMode.FAN_ONLY: 4,
    ClimateMode.HEAT: 6,
    ClimateMode.AUTO: 8,
}
_FANS = {
    ClimateFan.AUTO: 0,
    ClimateFan.HIGH: 1,
    ClimateFan.MEDIUM: 2,
    ClimateFan.LOW: 3,
}


class DelonghiCommand(ClimatePacket):
    """DeLonghi state; the temperature range depends on operating mode."""

    HEADER = (9000, -4500)
    TIMING = PulseTiming(465, 670, 1750)
    LENGTH = 8

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
    ) -> None:
        """Build a command: heat 13..27 °C, other modes 17..32 °C.

        The four-bit heat field uses a 12 °C offset. An off command has no
        retained operating-mode field, so its temperature uses the cool offset.
        """
        selection(mode, _MODES)
        heat = mode == ClimateMode.HEAT
        temperature_value(temperature, 13 if heat else 17, 27 if heat else 32)
        temp = (
            int(temperature) - 12 if heat and power else max(17, int(temperature)) - 17
        )
        data = bytes(
            [
                0x53,
                temp | selection(fan, _FANS) << 5,
                selection(mode, _MODES) | 1 if power else 0,
                0,
                0,
                0,
                0,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Validate and recover the state."""
        super().parse(data)
        if data[0] != 0x53:
            raise ValueError("invalid DeLonghi address")
        power = bool(data[2] & 1)
        mode = decoded(data[2] & 14, _MODES) if power else None
        heat = power and mode == ClimateMode.HEAT
        temperature = (data[1] & 15) + (12 if heat else 17)
        temperature_value(temperature, 13 if heat else 17, 27 if heat else 32)
        return ClimateState(
            power=power,
            mode=mode,
            temperature=temperature if power else None,
            fan=decoded(data[1] >> 5, _FANS),
        )
