"""Internal support for fixed-width infrared words."""

from typing import ClassVar, Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number


class WordCommand(Command):
    """Unsigned data word with fixed framing."""

    WIDTH: ClassVar[int]
    TIMING: ClassVar[PulseTiming]
    HEADER: ClassVar[tuple[int, ...]] = ()
    FOOTER: ClassVar[tuple[int, ...]] = ()
    CARRIER: ClassVar[int] = 38000

    def __init__(self, *, data: int, modulation: int | None = None) -> None:
        """Validate the word before encoding it."""
        if not 0 <= data < 1 << self.WIDTH:
            raise ValueError(f"data must fit in {self.WIDTH} bits")
        super().__init__(modulation=self.CARRIER if modulation is None else modulation)
        self.data = data

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the word most-significant bit first."""
        return [
            *self.HEADER,
            *self.TIMING.encode(bits(self.data, self.WIDTH)),
            *self.FOOTER,
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode one complete word, or None for an invalid capture."""
        reader = Reader(timings=timings)
        try:
            reader.expect(*cls.HEADER)
            data = number(reader.read_bits(cls.TIMING, cls.WIDTH))
            reader.expect(*cls.FOOTER)
            reader.end()
            return cls._from_data(data)
        except ValueError:
            return None

    @classmethod
    def _from_data(cls, data: int) -> Self:
        """Build and validate the received word's application fields."""
        return cls(data=data)
