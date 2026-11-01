"""Emmeti split-frame climate commands."""

from enum import IntEnum

from ._split_climate import SplitClimateCommand
from ._timing import PulseTiming, bits, number
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
    ClimateFan.LOW: 1,
    ClimateFan.MEDIUM: 2,
    ClimateFan.HIGH: 3,
}
_OFF = number(
    bits(9, 12)
    + bits(0, 8)
    + bits(0x2052, 15)
    + bits(0, 8)
    + bits(1, 2)
    + bits(0, 18)
    + bits(12, 4)
)


class EmmetiBlade(IntEnum):
    """Native four-bit vane positions and swing ranges."""

    STOP = 0
    FULL_SWING = 1
    POSITION_1 = 2
    POSITION_2 = 3
    POSITION_3 = 4
    POSITION_4 = 5
    POSITION_5 = 6
    LOW_SWING = 7
    MIDDLE_SWING = 9


class EmmetiCommand(SplitClimateCommand):
    """Whole-state Emmeti command with a separate fixed off word."""

    HEADER = (9076, -4408)
    TIMING = PulseTiming(660, 530, 1630)

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: int,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        blade: EmmetiBlade = EmmetiBlade.STOP,
    ) -> None:
        """Build a 16..30 °C state or the protocol's fixed power-off message."""
        temp = temperature_value(temperature, 16, 30)
        mode_code = selection(mode, _MODES)
        blade = EmmetiBlade(blade)
        swing = blade in (
            EmmetiBlade.FULL_SWING,
            EmmetiBlade.LOW_SWING,
            EmmetiBlade.MIDDLE_SWING,
        )
        first = (
            bits(mode_code, 3, lsb=True)
            + [1]
            + bits(selection(fan, _FANS), 2, lsb=True)
            + [int(swing), 0]
        )
        first += bits(temp, 4, lsb=True) + bits(0, 8) + [0, 1, 1, 0] + bits(0x52, 11)
        second = (
            bits(blade, 4, lsb=True)
            + bits(0, 4)
            + bits(2, 2, lsb=True)
            + bits(0, 18)
            + bits((temp + mode_code + 2) & 15, 4, lsb=True)
        )
        super().__init__(data=number(first + second) if power else _OFF)

    @property
    def state(self) -> ClimateState:
        """Validate the checksum and report only fields present in the command."""
        if self.data == _OFF:
            return ClimateState(power=False)
        values = bits(self.data, self.WIDTH)
        mode_code, temp = number(values[:3], lsb=True), number(values[8:12], lsb=True)
        if (
            not values[3]
            or number(values[24:35]) != 0x52
            or number(values[63:], lsb=True) != (temp + mode_code + 2) & 15
        ):
            raise ValueError("invalid Emmeti signature or checksum")
        temperature_value(temp + 16, 16, 30)
        EmmetiBlade(number(values[35:39], lsb=True))
        return ClimateState(
            power=True,
            mode=decoded(mode_code, _MODES),
            temperature=temp + 16,
            fan=decoded(number(values[4:6], lsb=True), _FANS),
            swing_v=bool(values[6]),
        )
