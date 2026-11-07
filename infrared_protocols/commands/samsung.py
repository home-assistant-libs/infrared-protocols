"""Samsung IR commands."""

from typing import Self, override

from . import Command
from ._decode import frames, validate_pulse_prefix
from ._timing import PulseTiming, Reader, byte_bits, pack_bytes


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

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode standard/extended Samsung32 and validate command complements."""
        messages: list[bytes] = []
        try:
            packets = frames(timings, period=108000, tolerance=0.4)
            for index, frame in enumerate(packets):
                if messages and len(frame) < 67 and index == len(packets) - 1:
                    expected = [
                        4500,
                        -4500,
                        *PulseTiming(560, 560, 1690).encode(byte_bits(messages[0])),
                        560,
                    ]
                    validate_pulse_prefix(frame, expected, tolerance=0.4)
                    break
                reader = Reader(timings=frame, tolerance=0.4)
                reader.expect(4500, -4500)
                data = pack_bytes(reader.read_bits(PulseTiming(560, 560, 1690), 32))
                reader.expect(560)
                reader.end()
                if data[2] ^ data[3] != 255:
                    return None
                messages.append(data)
            first = messages[0]
            if any(message != first for message in messages[1:]):
                return None
            if first[1] == 0 and first[0] != 0:
                return None
            address = first[0] if first[0] == first[1] else first[0] | first[1] << 8
            return cls(
                address=address, command=first[2], repeat_count=len(messages) - 1
            )
        except ValueError:
            return None
