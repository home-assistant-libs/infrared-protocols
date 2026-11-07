"""Whynter 32-bit portable air-conditioner commands."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Self

from ._climate_fields import temperature_value
from ._timing import PulseTiming, bits, number
from ._word import WordCommand


class WhynterMode(IntEnum):
    """Whynter operating modes."""

    FAN_ONLY = 0x1
    DRY = 0x2
    HEAT = 0x4
    COOL = 0x8


class WhynterFanSpeed(IntEnum):
    """Whynter fan speeds."""

    HIGH = 0x1
    MEDIUM = 0x2
    LOW = 0x4


@dataclass(frozen=True, kw_only=True)
class WhynterState:
    """Settings carried by a Whynter packet, using its native enums and units."""

    power: bool | None = None
    mode: WhynterMode | None = None
    temperature: int | None = None
    fan: WhynterFanSpeed | None = None
    is_fahrenheit: bool = False


class WhynterCommand(WordCommand):
    """Whynter state with explicit Celsius or Fahrenheit input."""

    HEADER = (8000, -4000)
    TIMING = PulseTiming(600, 550, 1600)
    FOOTER = (600,)
    WIDTH = 32

    def __init__(
        self,
        *,
        mode: WhynterMode | None,
        temperature: int,
        power: bool = True,
        fan: WhynterFanSpeed = WhynterFanSpeed.HIGH,
        is_fahrenheit: bool = False,
    ) -> None:
        """Build a state; Fahrenheit uses 61..89, Celsius uses 16..32."""
        temperature_value(
            temperature, 61 if is_fahrenheit else 16, 89 if is_fahrenheit else 32
        )
        temp = temperature if is_fahrenheit else temperature - 16
        value = (
            0x12000000
            | int(WhynterFanSpeed(fan)) << 20
            | (int(WhynterMode(mode)) << 16 if power else 0)
        )
        value |= (
            int(power) << 8 | int(is_fahrenheit) << 10 | number(bits(temp, 8), lsb=True)
        )
        super().__init__(data=value)

    @property
    def _is_fahrenheit(self) -> bool:
        """Return the remote's native temperature-unit flag."""
        return bool(self.data & 1024)

    @property
    def _temperature(self) -> int:
        """Return the set point in the remote's native units."""
        native = number(bits(self.data & 255, 8), lsb=True)
        return native if self._is_fahrenheit else native + 16

    @property
    def state(self) -> WhynterState:
        """Decode the carried state; off frames carry no mode."""
        if self.data >> 24 != 0x12:
            raise ValueError("invalid Whynter signature")
        temperature_value(
            self._temperature,
            61 if self._is_fahrenheit else 16,
            89 if self._is_fahrenheit else 32,
        )
        mode_code = self.data >> 16 & 15
        return WhynterState(
            power=bool(self.data & 256),
            mode=WhynterMode(mode_code) if mode_code else None,
            temperature=self._temperature,
            is_fahrenheit=self._is_fahrenheit,
            fan=WhynterFanSpeed(self.data >> 20 & 7),
        )

    @classmethod
    def _from_data(cls, data: int) -> Self:
        """Validate the state fields of a received word."""
        result = cls.__new__(cls)
        WordCommand.__init__(result, data=data)
        _ = result.state
        return result
