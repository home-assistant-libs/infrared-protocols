"""Whynter 32-bit portable air-conditioner commands."""

from typing import Self

from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming, bits, number
from ._word import WordCommand
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {
    ClimateMode.FAN_ONLY: 1,
    ClimateMode.DRY: 2,
    ClimateMode.HEAT: 4,
    ClimateMode.COOL: 8,
}
_FANS = {ClimateFan.HIGH: 1, ClimateFan.MEDIUM: 2, ClimateFan.LOW: 4}


class WhynterCommand(WordCommand):
    """Whynter state with explicit Celsius or Fahrenheit input."""

    HEADER = (8000, -4000)
    TIMING = PulseTiming(600, 550, 1600)
    FOOTER = (600,)
    WIDTH = 32

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: int,
        power: bool = True,
        fan: ClimateFan = ClimateFan.HIGH,
        fahrenheit: bool = False,
    ) -> None:
        """Build a state; Fahrenheit uses 61..89, Celsius uses 16..32."""
        temperature_value(
            temperature, 61 if fahrenheit else 16, 89 if fahrenheit else 32
        )
        temp = temperature if fahrenheit else temperature - 16
        value = (
            0x12000000
            | selection(fan, _FANS) << 20
            | (selection(mode, _MODES) << 16 if power else 0)
        )
        value |= (
            int(power) << 8 | int(fahrenheit) << 10 | number(bits(temp, 8), lsb=True)
        )
        super().__init__(data=value)

    @property
    def state(self) -> ClimateState:
        """Decode the carried state; off frames carry no mode."""
        if self.data >> 24 != 0x12:
            raise ValueError("invalid Whynter signature")
        native = number(bits(self.data & 255, 8), lsb=True)
        fahrenheit = bool(self.data & 1024)
        temperature_value(
            native if fahrenheit else native + 16,
            61 if fahrenheit else 16,
            89 if fahrenheit else 32,
        )
        mode_code = self.data >> 16 & 15
        return ClimateState(
            power=bool(self.data & 256),
            mode=decoded(mode_code, _MODES) if mode_code else None,
            temperature=(native - 32) * 5 / 9 if fahrenheit else native + 16,
            fan=decoded(self.data >> 20 & 7, _FANS),
        )

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode a complete word and validate the state fields."""
        from ._timing import Reader

        reader = Reader(timings=timings)
        try:
            reader.expect(*cls.HEADER)
            value = number(reader.read_bits(cls.TIMING, cls.WIDTH))
            reader.expect(*cls.FOOTER)
            reader.end()
            result = cls.__new__(cls)
            WordCommand.__init__(result, data=value)
            _ = result.state
            return result
        except ValueError:
            return None
