"""Samsung 36-bit infrared protocol."""

from typing import Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number

_TIMING = PulseTiming(500, 500, 1500)


class Samsung36Command(Command):
    """Sixteen-bit address and twenty-bit command, both in wire order."""

    def __init__(self, *, address: int, command: int, modulation: int = 38000) -> None:
        """Initialize a split Samsung frame."""
        bits(address, 16)
        bits(command, 20)
        super().__init__(modulation=modulation)
        self.address, self.command = address, command

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode both blocks and their separator."""
        return [
            4500,
            -4500,
            *_TIMING.encode(bits(self.address, 16)),
            500,
            -4500,
            *_TIMING.encode(bits(self.command, 20)),
            500,
            -59000,
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode a frame, allowing the final idle space to be omitted."""
        r = Reader(timings=timings)
        try:
            r.expect(4500, -4500)
            address = number(r.read_bits(_TIMING, 16))
            r.expect(500, -4500)
            command = number(r.read_bits(_TIMING, 20))
            r.expect(500)
            r.end()
            return cls(address=address, command=command)
        except ValueError:
            return None
