"""Internal transport for climate words split by a mid-frame gap."""

from typing import ClassVar, Self, override

from ._timing import Reader, bits, capture_gap_options, join_captures, number
from ._word import WordCommand


class SplitClimateCommand[StateT](WordCommand):
    """A 67-bit word transmitted as 35 and 32 bits."""

    WIDTH = 67
    SPLIT: ClassVar[int] = 35
    GAP: ClassVar[int] = 20000

    @classmethod
    def from_raw_captures(
        cls, captures: list[list[int]], *, idle: int = 10000
    ) -> Self | None:
        """Decode one press delivered whole or split by the receiver idle timeout."""
        if idle < 3000:
            raise ValueError("idle must be at least 3000 microseconds")
        if len(captures) == 1:
            return cls.from_raw_timings(captures[0])
        if not captures:
            return None
        boundaries = (*(-t for t in cls.HEADER if t < 0), cls.GAP)
        for gaps in capture_gap_options(boundaries, idle=idle, count=len(captures) - 1):
            try:
                result = cls.from_raw_timings(join_captures(captures, gaps))
            except ValueError:
                continue
            if result is not None:
                return result
        return None

    @property
    def state(self) -> StateT:
        """Validate and decode the protocol-specific word."""
        raise NotImplementedError

    @override
    def get_raw_timings(self) -> list[int]:
        """Insert the divider without adding a data bit."""
        values = bits(self.data, self.WIDTH)
        return [
            *self.HEADER,
            *self.TIMING.encode(values[: self.SPLIT]),
            self.TIMING.mark,
            -self.GAP,
            *self.TIMING.encode(values[self.SPLIT :]),
            self.TIMING.mark,
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode both blocks and require valid protocol state."""
        reader = Reader(timings=timings)
        try:
            reader.expect(*cls.HEADER)
            values = reader.read_bits(cls.TIMING, cls.SPLIT)
            reader.expect(cls.TIMING.mark, -cls.GAP)
            values.extend(reader.read_bits(cls.TIMING, cls.WIDTH - cls.SPLIT))
            reader.expect(cls.TIMING.mark)
            reader.end()
            result = cls.__new__(cls)
            WordCommand.__init__(result, data=number(values))
            _ = result.state
            return result
        except ValueError:
            return None
