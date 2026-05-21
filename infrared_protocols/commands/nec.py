"""NEC IR command."""

from typing import Self, override

from . import Command

LEADER_HIGH = 9000
LEADER_LOW = 4500
BIT_HIGH = 562
ZERO_LOW = 562
ONE_LOW = 1687
REPEAT_LOW = 2250
INITIAL_FRAME_GAP = 41000  # Gap to make total frame ~108ms
FRAME_GAP = 96000  # Gap to make total frame ~108ms
TOLERANCE = 0.4


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
        timings: list[int] = [LEADER_HIGH, -LEADER_LOW]

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
            timings.append(BIT_HIGH)
            timings.append(-ONE_LOW if bit else -ZERO_LOW)
            data >>= 1

        # End pulse
        timings.append(BIT_HIGH)

        # Add repeat codes if requested
        gap = INITIAL_FRAME_GAP
        for _ in range(self.repeat_count):
            timings.extend([-gap, LEADER_HIGH, -REPEAT_LOW, BIT_HIGH])
            gap = FRAME_GAP  # Use standard frame gap for subsequent repeats

        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a NECCommand.

        Returns a NECCommand if the timings match, or None otherwise.
        """
        # Minimum: 1 leader pair (2) + 32 bit pairs (64) + 1 end pulse high (1) = 67
        if len(timings) < 67:
            return None

        # Validate leader pulse
        if not cls._is_close(timings[0], LEADER_HIGH) or not cls._is_close(
            -timings[1], LEADER_LOW
        ):
            return None

        # Decode 32 data bits (LSB first)
        data = 0
        for i in range(32):
            bit = cls._decode_bit(timings[2 + 2 * i], -timings[3 + 2 * i])
            if bit is None:
                return None
            data |= bit << i

        # Validate end pulse
        if not cls._is_close(timings[66], BIT_HIGH):
            return None

        # Extract bytes
        address_low = data & 0xFF
        address_high = (data >> 8) & 0xFF
        command_byte = (data >> 16) & 0xFF
        command_inverted = (data >> 24) & 0xFF

        # Validate command checksum
        if command_byte ^ command_inverted != 0xFF:
            return None

        # Reconstruct the full 16-bit address.
        # Standard NEC (8-bit address) and extended NEC (16-bit address) produce
        # identical timings when address_low ^ address_high == 0xFF, making them
        # indistinguishable from raw timings alone. We always return the 16-bit
        # representation; callers can check if the high byte is the complement
        # of the low byte to determine if it was originally a standard 8-bit address.
        address = address_low | (address_high << 8)

        # Count repeat codes after the end pulse. Counting stops at the first
        # mismatch or truncated repeat frame; any remaining timings are ignored.
        repeat_count = cls._count_repeat_codes(timings, 67)
        return cls(address=address, command=command_byte, repeat_count=repeat_count)

    @staticmethod
    def _is_close(actual: int, expected: int) -> bool:
        """Check if an actual timing value is within tolerance of the expected value."""
        margin = expected * TOLERANCE
        return expected - margin <= actual <= expected + margin

    @staticmethod
    def _decode_bit(high_us: int, low_us: int) -> int | None:
        """Decode a single NEC data bit from high and low timings.

        Returns 0, 1, or None if the timings don't match a valid NEC bit.
        """
        if not NECCommand._is_close(high_us, BIT_HIGH):
            return None
        if NECCommand._is_close(low_us, ZERO_LOW):
            return 0
        if NECCommand._is_close(low_us, ONE_LOW):
            return 1
        return None

    @staticmethod
    def _count_repeat_codes(timings: list[int], start_index: int) -> int:
        """Count NEC repeat codes starting from the given index.

        A repeat code consists of a frame gap, a leader burst (9000µs high,
        2250µs low), and an end pulse (562µs high). Counting stops at the first
        mismatch or truncated trailing frame; any remaining timings are ignored.
        """
        count = 0
        i = start_index
        gap = INITIAL_FRAME_GAP
        while (i + 3) < len(timings):
            if (
                NECCommand._is_close(-timings[i], gap)
                and NECCommand._is_close(timings[i + 1], LEADER_HIGH)
                and NECCommand._is_close(-timings[i + 2], REPEAT_LOW)
                and NECCommand._is_close(timings[i + 3], BIT_HIGH)
            ):
                count += 1
                i += 4
                gap = FRAME_GAP
            else:
                return count
        return count
