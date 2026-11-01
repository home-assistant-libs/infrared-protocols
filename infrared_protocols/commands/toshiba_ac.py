"""Toshiba 48-bit packet transport with a compulsory duplicate packet."""

from typing import Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number

_TIMING = PulseTiming(560, 560, 1690)


class ToshibaAcPacketCommand(Command):
    """A duplicated primary word and an optional secondary word."""

    def __init__(
        self, *, rc_code_1: int, rc_code_2: int | None = None, modulation: int = 38000
    ) -> None:
        """Initialize the 48-bit words."""
        bits(rc_code_1, 48)
        if rc_code_2 is not None:
            bits(rc_code_2, 48)
        super().__init__(modulation=modulation)
        self.rc_code_1, self.rc_code_2 = rc_code_1, rc_code_2

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the protocol's duplicate and optional extension."""
        words = [self.rc_code_1, self.rc_code_1]
        if self.rc_code_2 is not None:
            words.append(self.rc_code_2)
        return [
            duration
            for word in words
            for duration in [4500, -4500, *_TIMING.encode(bits(word, 48)), 560, -4500]
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Validate duplicate words; accept an omitted final idle space."""
        r = Reader(timings)
        words: list[int] = []
        try:
            while True:
                r.expect(4500, -4500)
                words.append(number(r.read_bits(_TIMING, 48)))
                r.expect(560)
                if len(timings) - r.pos <= 1:
                    break
                if len(words) == 3:
                    return None
                r.expect(-5000)
            r.end()
            if len(words) < 2 or words[0] != words[1]:
                return None
            return cls(
                rc_code_1=words[0], rc_code_2=words[2] if len(words) == 3 else None
            )
        except ValueError:
            return None
