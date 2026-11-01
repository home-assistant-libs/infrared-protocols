"""Bang & Olufsen Beo4 infrared protocol (455 kHz carrier)."""

from typing import Self, override

from . import Command
from ._timing import Reader, bits, close, number


class Beo4Command(Command):
    """Beo4 source and button with differential space encoding."""

    def __init__(self, *, source: int, command: int, modulation: int = 455000) -> None:
        """Initialize one Beo4 frame."""
        bits(source, 8)
        bits(command, 8)
        super().__init__(modulation=modulation)
        self.source, self.command = source, command

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the source and command relative to the previous bit."""
        values = [0] + bits((self.source << 8) | self.command, 16)
        spaces = [
            6050 if a == b else 9175 if b else 2925
            for a, b in zip(values, values[1:], strict=False)
        ]
        return [
            200,
            -2925,
            200,
            -2925,
            200,
            -15425,
            200,
            -2925,
            *(duration for space in spaces for duration in (200, -space)),
            200,
            -12300,
            200,
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode a complete Beo4 frame."""
        r = Reader(timings)
        try:
            r.expect(200, -2925, 200, -2925, 200, -15425, 200, -2925)
            values = [0]
            for _ in range(16):
                r.expect(200)
                if r.pos >= len(timings):
                    return None
                space = timings[r.pos]
                r.pos += 1
                matches = [
                    value
                    for duration, value in ((-2925, 0), (-6050, values[-1]), (-9175, 1))
                    if close(space, duration, 0.15)
                ]
                if len(matches) != 1:
                    return None
                values.append(matches[0])
            r.expect(200, -12300, 200)
            r.end()
            return cls(source=number(values[1:9]), command=number(values[9:]))
        except ValueError:
            return None
