"""Raw LG 28- and 32-bit transports, without appliance-specific fields."""

from typing import Self

from ._timing import PulseTiming, Reader, number
from ._word import WordCommand


class _LgCommand(WordCommand):
    """An arbitrary 28-bit LG word; no application checksum is imposed."""

    WIDTH = 28
    HEADER = (8000, -4000)
    TIMING = PulseTiming(600, 550, 1600)
    FOOTER = (600,)

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode LG or LG2 physical framing at the configured payload width."""
        for header in (cls.HEADER, (3200, -9900)):
            reader = Reader(timings)
            try:
                reader.expect(*header)
                value = number(reader.read_bits(cls.TIMING, cls.WIDTH))
                reader.expect(*cls.FOOTER)
                reader.end()
                return cls(data=value)
            except ValueError:
                continue
        return None


class Lg28Command(_LgCommand):
    """Raw 28-bit LG payload, before application checksum interpretation."""

    WIDTH = 28


class Lg32Command(_LgCommand):
    """The 32-bit variant of the same pulse-distance transport."""

    WIDTH = 32
