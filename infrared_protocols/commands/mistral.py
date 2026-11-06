"""Mistral MHFE1126A / MR112C AEHA climate commands."""

from ._aeha_climate import AehaClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming, bits, number
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {
    ClimateMode.COOL: 0xC0,
    ClimateMode.DRY: 0x40,
    ClimateMode.FAN_ONLY: 0x80,
    ClimateMode.HEAT: 0x60,
    ClimateMode.AUTO: 0x10,
}
_FANS = {
    ClimateFan.AUTO: 0xA400,
    ClimateFan.LOW: 0x4440,
    ClimateFan.MEDIUM: 0x24C0,
    ClimateFan.HIGH: 0xA4A0,
}


def _reverse(value: int) -> int:
    return number(bits(value & 255, 8), lsb=True)


class MistralCommand(AehaClimatePacket):
    """Mistral full state; data includes the AEHA address bytes in wire order."""

    HEADER = (3400, -1700)
    TIMING = PulseTiming(425, 425, 1275)
    LENGTH = 14
    LSB = False

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
                0x32,
                0x2C,
                0x56,
                fan_code >> 8,
                8,
                32 if power else 0,
                selection(mode, _MODES) if power else 0x10,
                _reverse(159 - int(temperature)),
                fan_code & 255,
                0,
                0xE8,
                0,
                0x60,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @staticmethod
    def checksum(data: bytes) -> int:
        """Checksum the six defined fields in their native bit order."""
        return _reverse(sum(_reverse(data[i]) for i in (3, 5, 6, 7, 8, 10)))

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Validate the frame signature and recover the state."""
        super().parse(data)
        if (
            data[:3] != b"\x32\x2c\x56"
            or data[4] != 8
            or data[9:13] != b"\x00\xe8\x00\x60"
            or data[5] not in (0, 32)
        ):
            raise ValueError("invalid Mistral signature")
        temperature = 159 - _reverse(data[7])
        temperature_value(temperature, 16, 30)
        return ClimateState(
            power=bool(data[5]),
            mode=decoded(data[6], _MODES) if bool(data[5]) else None,
            temperature=temperature,
            fan=decoded(data[3] << 8 | data[8], _FANS),
        )
