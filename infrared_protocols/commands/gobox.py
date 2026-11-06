"""Go-Box infrared remote commands."""

from typing import Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number


class GoboxCommand(Command):
    """Seventeen-bit Go-Box button code following a fixed fifteen-bit prefix."""

    def __init__(self, *, code: int, modulation: int = 38000) -> None:
        """Initialize a button command."""
        bits(code, 17)
        super().__init__(modulation=modulation)
        self.code = code

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the prefix and code."""
        return [
            *PulseTiming(580, 545, 1640).encode(bits((0x3262 << 17) | self.code, 32)),
            580,
            -2000,
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode a Go-Box frame and validate its prefix."""
        r = Reader(timings=timings)
        try:
            value = number(r.read_bits(PulseTiming(580, 545, 1640), 32))
            r.expect(580)
            r.end(min_gap=1500)
            if value >> 17 != 0x3262:
                return None
            return cls(code=value & 0x1FFFF)
        except ValueError:
            return None
