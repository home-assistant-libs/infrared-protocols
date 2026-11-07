"""Hob2Hood fan and lighting infrared protocol."""

from itertools import groupby
from typing import Self, override

from . import Command
from ._timing import bits, close


class Hob2HoodCommand(Command):
    """A Hob2Hood command byte and its two incrementing check bytes."""

    def __init__(self, *, command: int, modulation: int = 38000) -> None:
        """Initialize the command byte."""
        if command not in (0xD5, 0xD2, 0xD8, 0x6C, 0x6F, 0xE1, 0x72):
            raise ValueError("unknown Hob2Hood command")
        super().__init__(modulation=modulation)
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the adjusted runs of equal bits."""
        values = [0] + [
            bit for offset in range(3) for bit in bits((self.command + offset) & 255, 8)
        ]
        return [
            -(700 * len(list(group)) - 200) if bit else 700 * len(list(group)) + 300
            for bit, group in groupby(values)
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Recognize the seven defined fan and light commands."""
        for command in (0xD5, 0xD2, 0xD8, 0x6C, 0x6F, 0xE1, 0x72):
            candidate = cls(command=command)
            expected = candidate.get_raw_timings()
            actual = timings.copy()
            if actual and actual[-1] <= -3000:
                actual.pop()
                if actual and actual[-1] < 0:
                    actual.pop()
            if expected[-1] < 0:
                if len(actual) == len(expected) and actual[-1] <= expected[-1] + 350:
                    actual.pop()
                expected = expected[:-1]
            if len(actual) == len(expected) and all(
                close(a, b, absolute=350) for a, b in zip(actual, expected, strict=True)
            ):
                return candidate
        return None
