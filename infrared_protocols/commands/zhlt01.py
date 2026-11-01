"""ZH/LT-01 remote commands used by Chigo, Eurom and related units."""

from ._climate import ClimatePacket
from ._timing import PulseTiming
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
    decoded,
    selection,
    temperature_value,
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
    ClimateFan.HIGH: 0x20,
    ClimateFan.MEDIUM: 0x40,
    ClimateFan.LOW: 0x60,
    ClimateFan.QUIET: 1,
}


class Zhlt01Command(ClimatePacket):
    """ZH/LT-01 full state with boost and silent/sleep fan selection."""

    HEADER = (6100, -7400)
    TIMING = PulseTiming(500, 600, 1800)
    LENGTH = 12

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        boost: bool = False,
    ) -> None:
        """Build a state for 16..32 °C; QUIET selects the sleep fan setting."""
        temp = temperature_value(temperature, 16, 32)
        control = (2 if power else 0) | (4 if swing_v else 8) | (0 if swing_h else 16)
        control |= selection(ClimateFan.HIGH if boost else fan, _FANS)
        values = bytes(
            [
                0,
                8 if boost else 0,
                0,
                control,
                (selection(mode, _MODES) << 5 if power else 0) | temp,
                0xD5,
            ]
        )
        data = bytes(byte for value in values for byte in (value ^ 255, value))
        super().__init__(data=data)

    @property
    def boost(self) -> bool:
        """Return whether turbo is enabled."""
        return bool(self.data[3] & 8)

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Validate every inverted byte pair and the remote identifier."""
        if (
            len(data) != cls.LENGTH
            or data[-1] != 0xD5
            or any(data[i] ^ data[i + 1] != 255 for i in range(0, 12, 2))
        ):
            raise ValueError("invalid ZH/LT-01 byte pair or identifier")
        temperature = (data[9] & 31) + 16
        temperature_value(temperature, 16, 32)
        return ClimateState(
            power=bool(data[7] & 2),
            mode=decoded(data[9] >> 5, _MODES),
            temperature=temperature,
            fan=decoded(data[7] & 0xE1, _FANS),
            swing_v=data[7] & 12 == 4,
            swing_h=not bool(data[7] & 16),
        )
