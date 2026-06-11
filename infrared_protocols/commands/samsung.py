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


class SamsungAC2A20Command(Command):
    """Samsung AC 2A20 21-byte IR command."""

    payload: list[int]

    def __init__(
        self,
        *,
        payload: list[int],
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Samsung AC 2A20 IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        if len(payload) != 21:
            raise ValueError("Samsung AC 2A20 payload must be exactly 21 bytes")
        self.payload = payload

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Samsung AC 2A20 command.

        Samsung AC protocol timing (in microseconds):
        - Leader pulse: 3000µs high, 3000µs low
        - Logical '0': 600µs high, 400µs low
        - Logical '1': 600µs high, 1400µs low
        - Inter-packet gap: 600µs high, 4000µs low
        - End pulse: 600µs high
        """
        leader_high = 3000
        leader_low = 3000
        bit_high = 600
        zero_low = 400
        one_low = 1400
        gap_low = 4000  # The synchronization pause between 7-byte blocks

        timings: list[int] = []

        # The 21-byte payload is split into 3 distinct packets of 7 bytes each
        for packet_idx in range(3):
            # Each packet starts with its own leader pulse
            timings.append(leader_high)
            timings.append(-leader_low)

            # Extract the 7 bytes belonging to the current packet
            start_byte = packet_idx * 7
            packet_bytes = self.payload[start_byte : start_byte + 7]

            # Bit blast (LSB first for each byte in the packet)
            for byte in packet_bytes:
                for _ in range(8):
                    bit = byte & 1
                    timings.append(bit_high)
                    timings.append(-one_low if bit else -zero_low)
                    byte >>= 1

            # After packet 0 and packet 1, we insert the inter-packet sync gap.
            # Packet 2 (the last one) will bypass this and go straight to the end pulse.
            if packet_idx < 2:
                timings.append(bit_high)
                timings.append(-gap_low)

        # Final end pulse for the entire transmission
        timings.append(bit_high)

        if self.repeat_count > 0:
            base_frame = timings.copy()
            for _ in range(self.repeat_count):
                timings.append(-40000)  # Inter-frame delay between repeats
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


SamsungACCommand = SamsungAC2A20Command
