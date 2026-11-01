"""Internal transport for climate words split by a mid-frame gap."""

from typing import ClassVar, Self, override

from ._timing import Reader, bits, number
from ._word import WordCommand
from .climate import ClimateState


class SplitClimateCommand(WordCommand):
    """A 67-bit word transmitted as 35 and 32 bits."""

    WIDTH = 67
    SPLIT: ClassVar[int] = 35
    GAP: ClassVar[int] = 20000

    @property
    def state(self) -> ClimateState:
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
        reader = Reader(timings)
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
