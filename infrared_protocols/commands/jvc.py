"""JVC 16-bit infrared words, in wire order."""

from typing import Self, override

from ._timing import PulseTiming, Reader, bits, number
from ._word import WordCommand


class JvcCommand(WordCommand):
    """JVC frame including its leader; data is the MSB-first wire word."""

    WIDTH = 16
    TIMING = PulseTiming(525, 525, 1725)
    HEADER = (8400, -4200)
    FOOTER = (525,)

    def __init__(
        self, *, data: int, modulation: int | None = None, repeat_count: int = 0
    ) -> None:
        """Initialize a word and its protocol-defined headerless repeats."""
        super().__init__(data=data, modulation=modulation)
        self.repeat_count = repeat_count

    @override
    def get_raw_timings(self) -> list[int]:
        """Only the first word carries a leader; words start 60 ms apart."""
        result = super().get_raw_timings()
        previous = sum(abs(t) for t in result)
        repeat = [*self.TIMING.encode(bits(self.data, self.WIDTH)), *self.FOOTER]
        for _ in range(self.repeat_count):
            result.extend([-(60000 - previous), *repeat])
            previous = sum(abs(t) for t in repeat)
        return result

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Validate the initial word and matching headerless repeats."""
        reader = Reader(timings=timings)
        try:
            reader.expect(*cls.HEADER)
            value = number(reader.read_bits(cls.TIMING, cls.WIDTH))
            reader.expect(*cls.FOOTER)
            repeats = 0
            while len(timings) - reader.pos > 1:
                if timings[reader.pos] > -3000:
                    return None
                reader.pos += 1
                if number(reader.read_bits(cls.TIMING, cls.WIDTH)) != value:
                    return None
                reader.expect(*cls.FOOTER)
                repeats += 1
            reader.end()
            return cls(data=value, repeat_count=repeats)
        except ValueError:
            return None
