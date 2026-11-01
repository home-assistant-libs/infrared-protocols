"""Noblex split-frame climate commands with a four-bit checksum."""

from ._split_climate import SplitClimateCommand
from ._timing import PulseTiming, bits, byte_bits, number, pack_bytes
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
    ClimateMode.COOL: 4,
    ClimateMode.DRY: 2,
    ClimateMode.FAN_ONLY: 6,
    ClimateMode.HEAT: 1,
}
_FANS = {
    ClimateFan.AUTO: 0,
    ClimateFan.LOW: 2,
    ClimateFan.MEDIUM: 1,
    ClimateFan.HIGH: 3,
}


def _reverse(value: int) -> int:
    return number(bits(value, 8), lsb=True)


def _checksum(data: bytes) -> int:
    return _reverse(sum(_reverse(value) for value in data) & 15) >> 4


class NoblexCommand(SplitClimateCommand):
    """Noblex absolute state; the divider replaces a fixed one bit."""

    HEADER = (9000, -4500)
    TIMING = PulseTiming(660, 520, 1640)

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: int,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_v: bool = False,
    ) -> None:
        """Build a state using the receiver's mode fields, with 25 °C in auto.

        ESPHome's transmitter currently ORs mode into a cool template, which
        changes auto/dry/heat codes. Here the mode field is assigned explicitly.
        """
        temp = temperature_value(temperature, 16, 30)
        code = selection(mode, _MODES) if power else 4
        data = bytes(
            [
                code << 5
                | (16 if power else 0)
                | selection(fan, _FANS) << 2
                | (2 if swing_v else 0),
                _reverse(9 if power and mode == ClimateMode.AUTO else temp),
                2 if power else 0,
                10,
                0x58 if swing_v else 0x50,
                0,
                0x20,
                0,
            ]
        )
        values = byte_bits(data, lsb=False)
        super().__init__(
            data=number(values[:35] + values[36:] + bits(_checksum(data), 4))
        )

    @property
    def state(self) -> ClimateState:
        """Reconstruct the omitted fixed bit and verify the checksum."""
        values = bits(self.data, self.WIDTH)
        data = pack_bytes(values[:35] + [1] + values[35:63], lsb=False)
        if (
            data[3] != 10
            or data[4] & ~8 != 0x50
            or data[6:] != bytes([32, 0])
            or number(values[63:]) != _checksum(data)
        ):
            raise ValueError("invalid Noblex signature or checksum")
        temp = (_reverse(data[1]) & 15) + 16
        temperature_value(temp, 16, 30)
        return ClimateState(
            power=bool(data[0] & 16),
            mode=decoded(data[0] >> 5, _MODES),
            temperature=temp,
            fan=decoded(data[0] >> 2 & 3, _FANS),
            swing_v=bool(data[0] & 2),
        )
