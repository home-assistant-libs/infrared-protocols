"""DeLonghi ARC43xxx portable air-conditioner state commands."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming


class DelonghiMode(IntEnum):
    """Delonghi operating modes."""

    COOL = 0x0
    DRY = 0x2
    FAN_ONLY = 0x4
    HEAT = 0x6
    AUTO = 0x8


class DelonghiFanSpeed(IntEnum):
    """Delonghi fan speeds."""

    AUTO = 0x0
    HIGH = 0x1
    MEDIUM = 0x2
    LOW = 0x3


@dataclass(frozen=True, kw_only=True)
class DelonghiState:
    """Settings carried by a Delonghi packet, using its native enums and units."""

    power: bool | None = None
    mode: DelonghiMode | None = None
    temperature: float | None = None
    fan: DelonghiFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None
    is_fahrenheit: bool = False


_MODES = {
    DelonghiMode.COOL: 0,
    DelonghiMode.DRY: 2,
    DelonghiMode.FAN_ONLY: 4,
    DelonghiMode.HEAT: 6,
    DelonghiMode.AUTO: 8,
}
_FANS = {
    DelonghiFanSpeed.AUTO: 0,
    DelonghiFanSpeed.HIGH: 1,
    DelonghiFanSpeed.MEDIUM: 2,
    DelonghiFanSpeed.LOW: 3,
}


class DelonghiCommand(ClimatePacket[DelonghiState]):
    """DeLonghi state; the temperature range depends on operating mode."""

    HEADER = (9000, -4500)
    TIMING = PulseTiming(465, 670, 1750)
    LENGTH = 8

    def __init__(
        self,
        *,
        mode: DelonghiMode,
        temperature: float,
        power: bool = True,
        fan: DelonghiFanSpeed = DelonghiFanSpeed.AUTO,
    ) -> None:
        """Build a command: heat 13..27 °C, other modes 17..32 °C.

        The four-bit heat field uses a 12 °C offset. An off command has no
        retained operating-mode field, so its temperature uses the cool offset.
        """
        selection(mode, _MODES)
        heat = mode == DelonghiMode.HEAT
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
    def parse(cls, data: bytes) -> DelonghiState:
        """Validate and recover the state."""
        cls._validate_packet(data)
        if data[0] != 0x53:
            raise ValueError("invalid DeLonghi address")
        power = bool(data[2] & 1)
        mode = decoded(data[2] & 14, _MODES) if power else None
        heat = power and mode == DelonghiMode.HEAT
        temperature = (data[1] & 15) + (12 if heat else 17)
        temperature_value(temperature, 13 if heat else 17, 27 if heat else 32)
        return DelonghiState(
            power=power,
            mode=mode,
            temperature=temperature if power else None,
            fan=decoded(data[1] >> 5, _FANS),
        )
