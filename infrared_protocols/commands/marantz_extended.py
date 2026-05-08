"""Marantz extended IR command."""

from typing import override

from . import Command
from .rc5 import (
    RC5_HALF_BIT_US,
    RC5_MODULATION_HZ,
    RC5_REPEAT_PERIOD_US,
    append_signed_us,
    manchester_encode_bit,
    strip_idle_edges,
)

# The pause inserted between the address and command fields is exactly four
# RC-5 half-bit units of pure space.
_MARANTZ_PAUSE_US = 4 * RC5_HALF_BIT_US


class MarantzExtendedCommand(Command):
    """Marantz extended IR command."""

    address: int
    command: int
    extension: int
    toggle: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        extension: int,
        toggle: int = 0,
        modulation: int = RC5_MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Marantz extended IR command."""
        if not 0 <= address <= 0x1F:
            raise ValueError("Marantz address must be in range 0x00..0x1F")
        if not 0 <= command <= 0x7F:
            raise ValueError("Marantz command must be in range 0x00..0x7F")
        if not 0 <= extension <= 0x3F:
            raise ValueError("Marantz extension must be in range 0x00..0x3F")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.extension = extension
        self.toggle = toggle

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Marantz extended command."""
        start_bit_2 = 0 if self.command & 0x40 else 1
        command_bits = self.command & 0x3F

        # First 8 bits: S1, S2/field, T, A4..A0 (MSB first).
        leader_bits: list[int] = [1, start_bit_2, self.toggle & 1]
        for i in range(4, -1, -1):
            leader_bits.append((self.address >> i) & 1)

        # Last 12 bits: C5..C0 (MSB first), then E5..E0 (MSB first).
        trailing_bits: list[int] = []
        for i in range(5, -1, -1):
            trailing_bits.append((command_bits >> i) & 1)
        for i in range(5, -1, -1):
            trailing_bits.append((self.extension >> i) & 1)

        frame: list[int] = []
        for bit in leader_bits:
            manchester_encode_bit(frame, bit, RC5_HALF_BIT_US)
        # The pause is a fixed-length space; merge with whatever space
        # came before it (the trailing half of A0 if A0 == 0).
        append_signed_us(frame, -_MARANTZ_PAUSE_US)
        for bit in trailing_bits:
            manchester_encode_bit(frame, bit, RC5_HALF_BIT_US)
        strip_idle_edges(frame)

        timings = list(frame)

        if self.repeat_count > 0:
            frame_duration = sum(abs(t) for t in frame)
            gap = RC5_REPEAT_PERIOD_US - frame_duration
            for _ in range(self.repeat_count):
                timings.append(-gap)
                timings.extend(frame)

        return timings
