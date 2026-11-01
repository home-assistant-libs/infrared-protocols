"""Remko AR715 / ClimaButler 52-bit air-conditioner commands."""

from typing import Self

from ._timing import PulseTiming, Reader, number
from ._word import WordCommand
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
    decoded,
    selection,
    temperature_value,
)

_FANS = {
    ClimateFan.AUTO: 0x80,
    ClimateFan.LOW: 0xA2,
    ClimateFan.MEDIUM: 0x91,
    ClimateFan.HIGH: 0x88,
}


class RemkoAr715Command(WordCommand):
    """Remko state with cooling, drying and fan-only modes."""

    HEADER = (511, -3492)
    TIMING = PulseTiming(511, 548, 1540)
    FOOTER = (511, -3492)
    WIDTH = 52

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: int,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_v: bool = False,
    ) -> None:
        """Build a whole-degree 16..30 °C state."""
        temp = temperature_value(temperature, 16, 30)
        if mode == ClimateMode.COOL:
            mode_fan = selection(fan, _FANS)
        elif mode in (ClimateMode.DRY, ClimateMode.FAN_ONLY):
            if fan != ClimateFan.AUTO:
                raise ValueError("dry and fan-only commands do not carry a fan speed")
            mode_fan = 0xA4 if mode == ClimateMode.DRY else 0xA3
        else:
            raise ValueError("Remko supports cool, dry and fan-only modes")
        value = (
            8 << 48
            | (3 if power else 0) << 44
            | (5 if swing_v else 7) << 16
            | mode_fan << 8
            | temp << 4
        )
        value |= (15 - sum(value >> shift & 15 for shift in range(4, 52, 4))) & 15
        super().__init__(data=value)

    @property
    def state(self) -> ClimateState:
        """Validate the nibble checksum and extract the state."""
        value = self.data
        if (
            value >> 48 != 8
            or (sum(value >> i & 15 for i in range(0, 52, 4)) & 15) != 15
        ):
            raise ValueError("invalid Remko signature or checksum")
        power_code, swing_code = value >> 44 & 15, value >> 16 & 15
        if power_code not in (0, 3) or swing_code not in (5, 7):
            raise ValueError("invalid Remko power or swing")
        mode_fan = value >> 8 & 255
        temperature = (value >> 4 & 15) + 16
        temperature_value(temperature, 16, 30)
        mode = {0xA4: ClimateMode.DRY, 0xA3: ClimateMode.FAN_ONLY}.get(
            mode_fan, ClimateMode.COOL
        )
        return ClimateState(
            power=bool(power_code),
            mode=mode,
            temperature=temperature,
            fan=decoded(mode_fan, _FANS) if mode == ClimateMode.COOL else None,
            swing_v=swing_code == 5,
        )

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode the complete 52-bit state, including its checksum."""
        reader = Reader(timings)
        try:
            reader.expect(*cls.HEADER)
            value = number(reader.read_bits(cls.TIMING, cls.WIDTH))
            reader.expect(cls.TIMING.mark)
            reader.end()
            result = cls.__new__(cls)
            WordCommand.__init__(result, data=value)
            _ = result.state
            return result
        except ValueError:
            return None
