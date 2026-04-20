"""Common IR command definitions."""

import abc
from typing import override


class Command(abc.ABC):
    """Base class for IR commands."""

    repeat_count: int
    modulation: int

    def __init__(self, *, modulation: int, repeat_count: int = 0) -> None:
        """Initialize the IR command."""
        self.modulation = modulation
        self.repeat_count = repeat_count

    @abc.abstractmethod
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the command.

        Positive values are pulse (high) durations in microseconds; negative
        values are space (low) durations in microseconds.
        """


class NECCommand(Command):
    """NEC IR command."""

    address: int
    command: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the NEC IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the NEC command.

        NEC protocol timing (in microseconds):
        - Leader pulse: 9000µs high, 4500µs low
        - Logical '0': 562µs high, 562µs low
        - Logical '1': 562µs high, 1687µs low
        - End pulse: 562µs high
        - Repeat code: 9000µs high, 2250µs low, 562µs end pulse
        - Frame gap: ~96ms between end pulse and next frame (total frame ~108ms)

        Data format (32 bits, LSB first):
        - Standard NEC: address (8-bit) + ~address (8-bit) + command (8-bit)
          + ~command (8-bit)
        - Extended NEC: address_low (8-bit) + address_high (8-bit) + command (8-bit)
          + ~command (8-bit)
        """
        # NEC timing constants (microseconds)
        leader_high = 9000
        leader_low = 4500
        bit_high = 562
        zero_low = 562
        one_low = 1687
        repeat_low = 2250
        initial_frame_gap = 41000  # Gap to make total frame ~108ms
        frame_gap = 96000  # Gap to make total frame ~108ms

        timings: list[int] = [leader_high, -leader_low]

        # Determine if standard (8-bit) or extended (16-bit) address
        if self.address <= 0xFF:
            # Standard NEC: address + inverted address
            address_low = self.address & 0xFF
            address_high = (~self.address) & 0xFF
        else:
            # Extended NEC: 16-bit address (no inversion)
            address_low = self.address & 0xFF
            address_high = (self.address >> 8) & 0xFF

        command_byte = self.command & 0xFF
        command_inverted = (~self.command) & 0xFF

        # Build 32-bit command data (LSB first in transmission)
        data = (
            address_low
            | (address_high << 8)
            | (command_byte << 16)
            | (command_inverted << 24)
        )

        for _ in range(32):
            bit = data & 1
            timings.append(bit_high)
            timings.append(-one_low if bit else -zero_low)
            data >>= 1

        # End pulse
        timings.append(bit_high)

        # Add repeat codes if requested
        gap = initial_frame_gap
        for _ in range(self.repeat_count):
            timings.extend([-gap, leader_high, -repeat_low, bit_high])
            gap = frame_gap  # Use standard frame gap for subsequent repeats

        return timings
