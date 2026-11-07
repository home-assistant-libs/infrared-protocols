"""Remko AR715 / ClimaButler 52-bit air-conditioner commands."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Self

from ._climate_fields import temperature_value
from ._timing import PulseTiming, Reader, number
from ._word import WordCommand


class RemkoAr715Mode(IntEnum):
    """Mode selectors; COOL uses the fan code instead of a fixed mode byte."""

    COOL = 0x80
    DRY = 0xA4
    FAN_ONLY = 0xA3


class RemkoAr715FanSpeed(IntEnum):
    """RemkoAr715 fan speeds."""

    AUTO = 0x80
    LOW = 0xA2
    MEDIUM = 0x91
    HIGH = 0x88


@dataclass(frozen=True, kw_only=True)
class RemkoAr715State:
    """Settings carried by a RemkoAr715 packet, using its native enums and units."""

    power: bool | None = None
    mode: RemkoAr715Mode | None = None
    temperature: int | None = None
    fan: RemkoAr715FanSpeed | None = None
    swing_v: bool | None = None


class RemkoAr715Command(WordCommand):
    """Remko state with cooling, drying and fan-only modes."""

    HEADER = (511, -3492)
    TIMING = PulseTiming(511, 548, 1540)
    FOOTER = (511, -3492)
    WIDTH = 52

    def __init__(
        self,
        *,
        mode: RemkoAr715Mode,
        temperature: int,
        power: bool = True,
        fan: RemkoAr715FanSpeed | None = RemkoAr715FanSpeed.AUTO,
        swing_v: bool = False,
    ) -> None:
        """Build a whole-degree 16..30 °C state."""
        temp = temperature_value(temperature, 16, 30)
        if mode == RemkoAr715Mode.COOL:
            mode_fan = int(RemkoAr715FanSpeed(fan))
        elif mode in (RemkoAr715Mode.DRY, RemkoAr715Mode.FAN_ONLY):
            if fan not in (None, RemkoAr715FanSpeed.AUTO):
                raise ValueError("dry and fan-only commands do not carry a fan speed")
            mode_fan = int(mode)
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
    def state(self) -> RemkoAr715State:
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
        mode = {
            int(mode): mode for mode in (RemkoAr715Mode.DRY, RemkoAr715Mode.FAN_ONLY)
        }.get(mode_fan, RemkoAr715Mode.COOL)
        return RemkoAr715State(
            power=bool(power_code),
            mode=mode,
            temperature=temperature,
            fan=RemkoAr715FanSpeed(mode_fan) if mode == RemkoAr715Mode.COOL else None,
            swing_v=swing_code == 5,
        )

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode the complete 52-bit state, including its checksum."""
        reader = Reader(timings=timings)
        try:
            reader.expect(*cls.HEADER)
            value = number(reader.read_bits(cls.TIMING, cls.WIDTH))
            reader.expect(cls.TIMING.mark)
            if len(timings) - reader.pos >= 2:
                reader.expect(-3492, cls.TIMING.mark)
            reader.end()
            result = cls.__new__(cls)
            WordCommand.__init__(result, data=value)
            _ = result.state
            return result
        except ValueError:
            return None
