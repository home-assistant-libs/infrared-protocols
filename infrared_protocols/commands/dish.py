"""Dish Network infrared remote protocol."""

from typing import Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number

_TIMING = PulseTiming(400, 2800, 1700)


class DishCommand(Command):
    """Dish unit address 1..16 and six-bit button command."""

    def __init__(self, *, address: int, command: int, modulation: int = 57600) -> None:
        """Initialize a Dish command."""
        bits(address - 1, 4)
        bits(command, 6)
        super().__init__(modulation=modulation)
        self.address, self.command = address, command

    @override
    def get_raw_timings(self) -> list[int]:
        """Send the four copies required for a Dish button press."""
        frame = _TIMING.encode(
            bits(self.command, 6) + bits(self.address - 1, 4, lsb=True) + [0] * 6
        )
        return [400, -6100] + (frame + [400, -6100]) * 4

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode a single received frame or a complete four-frame press."""
        r = Reader(timings=timings)
        try:
            r.expect(400, -6100)
            fields = r.read_bits(_TIMING, 16)
            if any(fields[10:]):
                return None
            r.expect(400)
            while len(timings) - r.pos > 1:
                r.expect(-6100)
                if r.read_bits(_TIMING, 16) != fields:
                    return None
                r.expect(400)
            r.end()
            return cls(
                address=number(fields[6:10], lsb=True) + 1, command=number(fields[:6])
            )
        except ValueError:
            return None
