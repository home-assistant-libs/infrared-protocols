"""Raw LG 28- and 32-bit transports, without appliance-specific fields."""

from typing import Self, override

from ._timing import PulseTiming, Reader, bits, number
from ._word import WordCommand


class _LgCommand(WordCommand):
    """An arbitrary 28-bit LG word; no application checksum is imposed."""

    WIDTH = 28
    HEADER = (8000, -4000)
    TIMING = PulseTiming(600, 550, 1600)
    FOOTER = (600,)

    def __init__(
        self, *, data: int, lg2: bool = False, modulation: int | None = None
    ) -> None:
        """Select the payload's physical framing; LG2 carries 28 bits."""
        if lg2 and self.WIDTH != 28:
            raise ValueError("LG2 framing requires a 28-bit payload")
        super().__init__(data=data, modulation=modulation)
        self.lg2 = lg2

    @override
    def get_raw_timings(self) -> list[int]:
        """Preserve the selected LG or LG2 physical framing."""
        if self.lg2:
            return [
                3200,
                -9900,
                *PulseTiming(550, 550, 1600).encode(bits(self.data, 28)),
                550,
            ]
        return super().get_raw_timings()

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode LG or LG2 physical framing at the configured payload width."""
        for header in (cls.HEADER, (3200, -9900)) if cls.WIDTH == 28 else (cls.HEADER,):
            reader = Reader(timings=timings)
            try:
                reader.expect(*header)
                value = number(reader.read_bits(cls.TIMING, cls.WIDTH))
                reader.expect(*cls.FOOTER)
                reader.end()
                return cls(data=value, lg2=header == (3200, -9900))
            except ValueError:
                continue
        return None


class Lg28Command(_LgCommand):
    """Raw 28-bit LG payload, before application checksum interpretation."""

    WIDTH = 28


class Lg32Command(_LgCommand):
    """The 32-bit variant of the same pulse-distance transport."""

    WIDTH = 32
