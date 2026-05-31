"""Generic Panasonic air-conditioner IR protocol.

Panasonic A/C remotes share a common framing: a state byte list split into two
sections (an 8-byte section 1 followed by a variable section 2), each encoded
LSB-first at 38 kHz with a fixed leader, per-bit mark/space, and a trailing
mark plus gap. Individual models differ only in the byte layout and checksum
range, so :class:`PanasonicAcCommand` encodes an already-built state and leaves
the layout to subclasses.
"""

from typing import override

from . import Command

# Physical-layer timings, in microseconds (canonical Panasonic values).
HEADER_MARK = 3456
HEADER_SPACE = 1728
BIT_MARK = 432
ZERO_SPACE = 432
ONE_SPACE = 1296
SECTION_GAP = 10000
MESSAGE_GAP = 100000

MODULATION_HZ = 38000

# Section 1 is always the first 8 bytes; section 2 is the remainder.
SECTION1_LENGTH = 8


def checksum(state: list[int], start: int, end: int) -> int:
    """Sum bytes ``state[start..end]`` (inclusive) modulo 256."""
    total = 0
    for i in range(start, end + 1):
        total = (total + state[i]) & 0xFF
    return total


def _bits_lsb(byte: int) -> list[int]:
    """Return the 8 bits of ``byte``, least-significant first."""
    return [(byte >> j) & 1 for j in range(8)]


def _section_timings(section: list[int], trailing_gap: int) -> list[int]:
    """Encode one section (header + LSB-first bits + trailing mark/gap)."""
    timings: list[int] = [HEADER_MARK, -HEADER_SPACE]
    for byte in section:
        for bit in _bits_lsb(byte):
            timings.append(BIT_MARK)
            timings.append(-(ONE_SPACE if bit else ZERO_SPACE))
    timings.append(BIT_MARK)
    timings.append(-trailing_gap)
    return timings


def state_to_timings(state: list[int]) -> list[int]:
    """Convert a state byte list into signed microsecond timings.

    Positive values are pulse (carrier on) durations; negative values are space
    (carrier off) durations. The state is split into section 1 (the first
    :data:`SECTION1_LENGTH` bytes) and section 2 (the remainder).
    """
    section1 = state[:SECTION1_LENGTH]
    section2 = state[SECTION1_LENGTH:]
    return [
        *_section_timings(section1, SECTION_GAP),
        *_section_timings(section2, MESSAGE_GAP),
    ]


class PanasonicAcCommand(Command):
    """Generic Panasonic air-conditioner IR command."""

    _state: list[int]

    def __init__(self, *, state: list[int], modulation: int = MODULATION_HZ) -> None:
        """Wrap a pre-built Panasonic A/C state byte list."""
        super().__init__(modulation=modulation, repeat_count=0)
        self._state = state

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the command."""
        return state_to_timings(self._state)
