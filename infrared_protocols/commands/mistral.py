"""Mistral MHFE1126A / MR112C AEHA climate commands."""

from ._aeha_climate import AehaClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {
    ClimateMode.COOL: 3,
    ClimateMode.DRY: 2,
    ClimateMode.FAN_ONLY: 1,
    ClimateMode.HEAT: 6,
    ClimateMode.AUTO: 8,
}
_FANS = {
    ClimateFan.AUTO: 0x2500,
    ClimateFan.LOW: 0x2202,
    ClimateFan.MEDIUM: 0x2403,
    ClimateFan.HIGH: 0x2505,
}


class MistralCommand(AehaClimatePacket):
    """Mistral full state; data includes the AEHA address bytes in wire order."""

    LENGTH = 14

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
    ) -> None:
        """Build a whole-degree 16..30 °C state."""
        selection(mode, _MODES)
        temperature_value(temperature, 16, 30)
        fan_code = selection(fan, _FANS)
        data = bytes(
            [
                0x4C,
                0x34,
                0x6A,
                fan_code >> 8,
                16,
                4 if power else 0,
                selection(mode, _MODES) if power else 8,
                159 - int(temperature),
                fan_code & 255,
                0,
                0x17,
                0,
                6,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @staticmethod
    def checksum(data: bytes) -> int:
        """Checksum the six defined fields in their native bit order."""
        return sum(data[i] for i in (3, 5, 6, 7, 8, 10)) & 255

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Validate the frame signature and recover the state."""
        super().parse(data)
        if (
            data[:3] != b"\x4c\x34\x6a"
            or data[4] != 16
            or data[9:13] != b"\x00\x17\x00\x06"
            or data[5] not in (0, 4)
        ):
            raise ValueError("invalid Mistral signature")
        temperature = 159 - data[7]
        temperature_value(temperature, 16, 30)
        return ClimateState(
            power=bool(data[5]),
            mode=decoded(data[6], _MODES) if bool(data[5]) else None,
            temperature=temperature,
            fan=decoded(data[3] << 8 | data[8], _FANS),
        )
