"""Toshiba 48-bit packet transport with a compulsory duplicate packet."""

from typing import ClassVar, Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number


class ToshibaAcPacketCommand(Command):
    """A duplicated primary word and an optional secondary word."""

    HEADER: ClassVar[tuple[int, int]] = (4500, -4500)
    TIMING: ClassVar[PulseTiming] = PulseTiming(560, 560, 1690)
    GAP: ClassVar[int] = 4500

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
            for duration in [
                *self.HEADER,
                *self.TIMING.encode(bits(word, 48)),
                self.TIMING.mark,
                -self.GAP,
            ]
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Validate duplicate words; accept an omitted final idle space."""
        words = cls._read_words(timings)
        if words is None:
            return None
        return cls(rc_code_1=words[0], rc_code_2=words[2] if len(words) == 3 else None)

    @classmethod
    def _read_words(cls, timings: list[int]) -> list[int] | None:
        r = Reader(timings=timings)
        words: list[int] = []
        try:
            while True:
                r.expect(*cls.HEADER)
                words.append(number(r.read_bits(cls.TIMING, 48)))
                r.expect(cls.TIMING.mark)
                if len(timings) - r.pos <= 1:
                    break
                if len(words) == 3:
                    return None
                r.expect(-cls.GAP)
            r.end()
            if len(words) < 2 or words[0] != words[1]:
                return None
            return words
        except ValueError:
            return None
