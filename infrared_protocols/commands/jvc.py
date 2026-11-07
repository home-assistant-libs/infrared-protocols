"""JVC 16-bit infrared words, in wire order."""

from typing import Self, override

from ._timing import PulseTiming, Reader, bits, close, number
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
            scale = (timings[0] - timings[1]) / sum(abs(t) for t in cls.HEADER)
            previous_duration = sum(abs(t) for t in timings[: reader.pos])
            while len(timings) - reader.pos > 1:
                gap = -round(60000 * scale - previous_duration)
                if close(timings[reader.pos], -23625 * scale):
                    gap = -round(23625 * scale)
                reader.expect(gap)
                start = reader.pos
                remaining = len(timings) - reader.pos
                if remaining < 2 * cls.WIDTH + 1:
                    prefix = reader.read_bits(cls.TIMING, remaining // 2)
                    if prefix != bits(value, cls.WIDTH)[: len(prefix)]:
                        return None
                    if remaining % 2:
                        reader.expect(cls.TIMING.mark)
                    break
                if number(reader.read_bits(cls.TIMING, cls.WIDTH)) != value:
                    return None
                reader.expect(*cls.FOOTER)
                repeats += 1
                previous_duration = sum(abs(t) for t in timings[start : reader.pos])
            reader.end()
            return cls(data=value, repeat_count=repeats)
        except ValueError:
            return None
