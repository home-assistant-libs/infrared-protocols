"""Emmeti split-frame climate commands."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate_fields import temperature_value
from ._split_climate import SplitClimateCommand
from ._timing import PulseTiming, bits, number


class EmmetiMode(IntEnum):
    """Emmeti operating modes."""

    AUTO = 0x0
    COOL = 0x1
    DRY = 0x2
    FAN_ONLY = 0x3
    HEAT = 0x4


class EmmetiFanSpeed(IntEnum):
    """Emmeti fan speeds."""

    AUTO = 0x0
    LOW = 0x1
    MEDIUM = 0x2
    HIGH = 0x3


@dataclass(frozen=True, kw_only=True)
class EmmetiState:
    """Settings carried by an Emmeti packet, using its native enums and units."""

    power: bool | None = None
    mode: EmmetiMode | None = None
    temperature: int | None = None
    fan: EmmetiFanSpeed | None = None
    swing_v: bool | None = None


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


class EmmetiCommand(SplitClimateCommand[EmmetiState]):
    """Whole-state Emmeti command with a separate fixed off word.

    Decoding requires all sections in one capture. Configure the receiver idle
    timeout above 20 ms, or join captures with their measured intervening gaps.
    A default 10 ms ESPHome receiver splits this packet; pass the consecutive
    bursts from one press to from_raw_captures() to decode it.
    """

    HEADER = (9076, -4408)
    TIMING = PulseTiming(660, 530, 1630)

    def __init__(
        self,
        *,
        mode: EmmetiMode | None,
        temperature: int | None = None,
        power: bool = True,
        fan: EmmetiFanSpeed | None = EmmetiFanSpeed.AUTO,
        blade: EmmetiBlade | None = EmmetiBlade.STOP,
    ) -> None:
        """Build a 16..30 °C state or the protocol's fixed power-off message."""
        if not power:
            if temperature is not None:
                temperature_value(temperature, 16, 30)
            if mode is not None:
                EmmetiMode(mode)
            if fan is not None:
                EmmetiFanSpeed(fan)
            if blade is not None:
                EmmetiBlade(blade)
            super().__init__(data=_OFF)
            return
        temp = temperature_value(temperature, 16, 30)
        mode_code = int(EmmetiMode(mode))
        blade = EmmetiBlade(blade)
        swing = blade in (
            EmmetiBlade.FULL_SWING,
            EmmetiBlade.LOW_SWING,
            EmmetiBlade.MIDDLE_SWING,
        )
        first = (
            bits(mode_code, 3, lsb=True)
            + [1]
            + bits(int(EmmetiFanSpeed(fan)), 2, lsb=True)
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
        super().__init__(data=number(first + second))

    @property
    def blade(self) -> EmmetiBlade | None:
        """Return the native vane request, absent on a power-off packet."""
        if self.state.power is False:
            return None
        return EmmetiBlade(number(bits(self.data, self.WIDTH)[35:39], lsb=True))

    @property
    def state(self) -> EmmetiState:
        """Validate the checksum and report only fields present in the command."""
        if self.data == _OFF:
            return EmmetiState(power=False)
        values = bits(self.data, self.WIDTH)
        mode_code, temp = number(values[:3], lsb=True), number(values[8:12], lsb=True)
        if (
            number(values[24:35]) != 0x52
            or number(values[63:], lsb=True) != (temp + mode_code + 2) & 15
        ):
            raise ValueError("invalid Emmeti signature or checksum")
        if not values[3]:
            return EmmetiState(power=False)
        temperature_value(temp + 16, 16, 30)
        EmmetiBlade(number(values[35:39], lsb=True))
        return EmmetiState(
            power=True,
            mode=EmmetiMode(mode_code),
            temperature=temp + 16,
            fan=EmmetiFanSpeed(number(values[4:6], lsb=True)),
            swing_v=bool(values[6]),
        )
