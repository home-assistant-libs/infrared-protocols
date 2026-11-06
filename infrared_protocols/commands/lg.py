"""Raw LG 28- and 32-bit transports, without appliance-specific fields."""

from typing import Self, override

from ._timing import PulseTiming, Reader, bits, close, number
from ._word import WordCommand


class _LgCommand(WordCommand):
    """An arbitrary LG word with protocol-defined short repeat codes."""

    HEADER = (8000, -4000)
    TIMING = PulseTiming(600, 550, 1600)
    FOOTER = (600,)
    REPEAT_HEADER = 8500

    def __init__(
        self, *, data: int, modulation: int | None = None, repeat_count: int = 0
    ) -> None:
        """Initialize the word and held-key repeat count."""
        super().__init__(data=data, modulation=modulation)
        self.repeat_count = repeat_count

    @property
    def _repeat_header(self) -> int:
        return self.REPEAT_HEADER

    def _frame(self) -> list[int]:
        return super().get_raw_timings()

    @override
    def get_raw_timings(self) -> list[int]:
        """Emit the complete word, then held-key repeat codes on their cadence."""
        result = self._frame()
        previous = sum(abs(t) for t in result)
        repeat = [self._repeat_header, -2250, 550]
        for _ in range(self.repeat_count):
            result.extend([-max(39750, 108050 - previous), *repeat])
            previous = sum(abs(t) for t in repeat)
        return result

    @classmethod
    def _read_capture(
        cls, timings: list[int], *, header: tuple[int, ...], repeat_header: int
    ) -> tuple[int, int] | None:
        reader = Reader(timings=timings)
        try:
            reader.expect(*header)
            value = number(reader.read_bits(cls.TIMING, cls.WIDTH))
            reader.expect(*cls.FOOTER)
            repeats = 0
            scale = (timings[0] - timings[1]) / sum(abs(t) for t in header)
            previous_duration = sum(abs(t) for t in timings[: reader.pos])
            while len(timings) - reader.pos > 1:
                gap = max(39750 * scale, 108050 * scale - previous_duration)
                if repeats == 0 and close(timings[reader.pos], -39750 * scale):
                    gap = 39750 * scale
                reader.expect(-round(gap))
                start = reader.pos
                remaining = len(timings) - reader.pos
                if remaining < 3:
                    reader.expect(*(repeat_header, -2250, 550)[:remaining])
                    break
                reader.expect(repeat_header, -2250, 550)
                repeats += 1
                previous_duration = sum(abs(t) for t in timings[start : reader.pos])
            reader.end()
            return value, repeats
        except ValueError:
            return None

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode the word and any trailing held-key repeat codes."""
        result = cls._read_capture(
            timings, header=cls.HEADER, repeat_header=cls.REPEAT_HEADER
        )
        if result is None:
            return None
        return cls(data=result[0], repeat_count=result[1])


class Lg28Command(_LgCommand):
    """Raw 28-bit LG payload, before application checksum interpretation."""

    WIDTH = 28

    def __init__(
        self,
        *,
        data: int,
        lg2: bool = False,
        modulation: int | None = None,
        repeat_count: int = 0,
    ) -> None:
        """Select LG or LG2 framing for the 28-bit payload."""
        super().__init__(data=data, modulation=modulation, repeat_count=repeat_count)
        self.lg2 = lg2

    @property
    def _repeat_header(self) -> int:
        return 3200 if self.lg2 else 8500

    def _frame(self) -> list[int]:
        if self.lg2:
            return [
                3200,
                -9900,
                *PulseTiming(550, 550, 1600).encode(bits(self.data, 28)),
                550,
            ]
        return super()._frame()

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Retain LG2 framing, which only exists for the 28-bit transport."""
        result = super().from_raw_timings(timings)
        if result is not None:
            return result
        decoded = cls._read_capture(timings, header=(3200, -9900), repeat_header=3200)
        if decoded is None:
            return None
        return cls(data=decoded[0], repeat_count=decoded[1], lg2=True)


class Lg32Command(_LgCommand):
    """The 32-bit variant of the same pulse-distance transport."""

    WIDTH = 32
    REPEAT_HEADER = 8950
