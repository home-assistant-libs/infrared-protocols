"""Kaseikyo format IR command."""

from collections.abc import Callable
from typing import override

from . import Command


class KaseikyoCommand(Command):
    """Kaseikyo format IR command."""

    address: int
    data: list[bytes]
    error_correction: Callable[[bytes], bytes] | None
    base_unit: float

    def __init__(
        self,
        *,
        address: int,
        data: list[bytes],
        error_correction: Callable[[bytes], bytes] | None = None,
        modulation: int = 38000,
        burst_pulse: int = 16,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Kaseikyo IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.data = data
        self.error_correction = error_correction
        self.base_unit = 1000000 * burst_pulse / modulation

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Kaseikyo command.

        Kaseikyo protocol timing (in base time units):
        - T: base time unit (16/38kHz = 421µs typ.)
        - Leader pulse: 8T high, 4T low
        - Logical '0': 1T high, 1T low
        - Logical '1': 1T high, 3T low
        - End pulse: 1T high
        - Repeat code: 8T high, 8T low, 1T end pulse
        - Frame gap: total frame typically ~130ms

        Data format (variable length, LSB first):
        - Address (16-bit) + Parity (4-bit) + Data 0 (4-bit) + Data 1 (8-bit) + ...
        """
        leader_high = round(8 * self.base_unit)
        leader_low = round(4 * self.base_unit)
        repeat_low = round(8 * self.base_unit)
        bit_high = round(1 * self.base_unit)
        zero_low = round(1 * self.base_unit)
        one_low = round(3 * self.base_unit)
        frame_time = 130000
        repeat_frame_gap = frame_time - (leader_high + repeat_low + bit_high)
        multi_frame_gap = 10000

        parity = self.address & 0xFFFF
        parity ^= parity >> 8
        parity ^= parity >> 4
        parity &= 0x0F

        timings: list[int] = []
        for i, data in enumerate(self.data):
            if i != 0:
                # Add inter-frame gap for multi-frame commands
                timings.append(-multi_frame_gap)
            timings.extend([leader_high, -leader_low])

            data_bytes = [
                self.address & 0xFF,
                (self.address >> 8) & 0xFF,
                (data[0] & 0xF0) | parity,
                *data[1:],
            ]
            if self.error_correction:
                data_bytes.extend(self.error_correction(bytes(data_bytes)))

            for byte in data_bytes:
                for _ in range(8):
                    bit = byte & 1
                    timings.append(bit_high)
                    timings.append(-one_low if bit else -zero_low)
                    byte >>= 1

            # End pulse
            timings.append(bit_high)

        # Add repeat codes if requested
        gap = max(frame_time - sum(abs(t) for t in timings), multi_frame_gap)
        for _ in range(self.repeat_count):
            timings.extend([-gap, leader_high, -repeat_low, bit_high])
            gap = repeat_frame_gap  # Use standard frame gap for subsequent repeats

        return timings
