"""Samsung IR commands."""

from typing import override

from . import Command


class Samsung32Command(Command):
    """Samsung32 IR command."""

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
        """Initialize the Samsung32 IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Samsung32 command.

        Samsung32 protocol timing (in microseconds):
        - Leader pulse: 4500µs high, 4500µs low
        - Logical '0': 560µs high, 560µs low
        - Logical '1': 560µs high, 1690µs low
        - End pulse: 560µs high
        - Repeat: full frame retransmission, total frame padded to 108ms

        Data format (32 bits, LSB first per byte):
        - Standard Samsung32: address (8-bit) + address (8-bit) + command (8-bit)
          + ~command (8-bit)
        - Extended Samsung32: address_low (8-bit) + address_high (8-bit)
          + command (8-bit) + ~command (8-bit)
        """
        leader_high = 4500
        leader_low = 4500
        bit_high = 560
        zero_low = 560
        one_low = 1690
        frame_time = 108000

        timings: list[int] = [leader_high, -leader_low]

        if self.address <= 0xFF:
            # Standard Samsung32: same address byte sent twice
            address_low = self.address & 0xFF
            address_high = self.address & 0xFF
        else:
            # Extended: 16-bit address split into low/high
            address_low = self.address & 0xFF
            address_high = (self.address >> 8) & 0xFF

        command_byte = self.command & 0xFF
        command_inverted = (~self.command) & 0xFF

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

        # Add repeat codes (full frame retransmission)
        if self.repeat_count > 0:
            frame_duration = sum(abs(t) for t in timings)
            gap = frame_time - frame_duration
            base_frame = timings.copy()
            for _ in range(self.repeat_count):
                timings.append(-gap)
                timings.extend(base_frame)

        return timings


class SamsungAC0292Command(Command):
    """Samsung AC 0292 21-byte IR command."""

    payload: list[int]

    def __init__(
        self,
        *,
        payload: list[int],
        modulation: int = 38000,
    ) -> None:
        """Initialize the Samsung AC 0292 IR command."""
        super().__init__(modulation=modulation, repeat_count=0)
        if len(payload) != 21:
            raise ValueError("Samsung AC 0292 payload must be exactly 21 bytes")
        self.payload = payload

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Samsung AC 0292 command."""
        timings: list[int] = [690, -17844]

        for offset in range(0, len(self.payload), 7):
            timings.extend([3086, -8864])
            for byte in self.payload[offset : offset + 7]:
                for bit in range(8):
                    timings.extend([586, -1432 if (byte >> bit) & 1 else -436])
            timings.extend([586, -30000 if offset + 7 >= len(self.payload) else -2886])

        return timings
