"""MagiQuest wand signals, including the legacy transmitter layout.

The current 56-bit format has an eight-bit zero header, a 31-bit wand id,
a nine-bit magnitude and an additive checksum. Legacy ESPHome transmission
uses a different 51-bit layout and is available explicitly.
"""

from typing import Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number

_TIMING = PulseTiming(288, 864, 576, one_mark=576)


class MagiQuestCommand(Command):
    """Checksummed MagiQuest wand message."""

    def __init__(
        self, *, wand_id: int, magnitude: int, modulation: int = 38000
    ) -> None:
        """Initialize a wand identifier and motion magnitude."""
        bits(wand_id, 31)
        bits(magnitude, 9)
        super().__init__(modulation=modulation)
        self.wand_id, self.magnitude = wand_id, magnitude

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the physical wand format, including its checksum."""
        payload = ((self.wand_id << 9) | self.magnitude).to_bytes(5, "big")
        checksum = -sum(payload) & 255
        return _TIMING.encode(
            [0] * 8
            + bits(self.wand_id, 31)
            + bits(self.magnitude, 9)
            + bits(checksum, 8)
        )

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode and verify the current wand format."""
        r = Reader(timings=timings)
        try:
            values = r.read_bits(_TIMING, 56, last_space_optional=True)
            r.end()
            if any(values[:8]) or sum(number(values[8:]).to_bytes(6, "big")) & 255:
                return None
            return cls(wand_id=number(values[8:39]), magnitude=number(values[39:48]))
        except ValueError:
            return None


class MagiQuestLegacyCommand(Command):
    """Legacy ESPHome transmitter format; distinct from physical wand frames."""

    def __init__(
        self, *, wand_id: int, magnitude: int, modulation: int = 38000
    ) -> None:
        """Initialize a legacy 32-bit identifier and 16-bit magnitude."""
        bits(wand_id, 32)
        bits(magnitude, 16)
        super().__init__(modulation=modulation)
        self.wand_id, self.magnitude = wand_id, magnitude

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the explicitly selected legacy format."""
        return [
            *_TIMING.encode([0, 0] + bits(self.wand_id, 32) + bits(self.magnitude, 16)),
            288,
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode the legacy layout, including its two start bits and stop mark."""
        reader = Reader(timings=timings)
        try:
            values = reader.read_bits(_TIMING, 50)
            reader.expect(288)
            reader.end()
            if values[:2] != [0, 0]:
                return None
            return cls(wand_id=number(values[2:34]), magnitude=number(values[34:]))
        except ValueError:
            return None
