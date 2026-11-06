"""Roomba eight-bit infrared remote protocol."""

from typing import Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number

_TIMING = PulseTiming(1000, 3000, 1000, one_mark=3000)


class RoombaCommand(Command):
    """An eight-bit Roomba infrared command."""

    def __init__(self, *, data: int, modulation: int = 38000) -> None:
        """Initialize the remote command."""
        bits(data, 8)
        super().__init__(modulation=modulation)
        self.data = data

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the eight pulse-width symbols."""
        return _TIMING.encode(bits(self.data, 8))

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode a command even when the receiver drops its final space."""
        r = Reader(timings=timings)
        try:
            data = number(r.read_bits(_TIMING, 8, last_space_optional=True))
            r.end()
            return cls(data=data)
        except ValueError:
            return None
