"""NEC1-f16 IR command."""

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


class NEC1F16Command(Command):
    """NEC1-f16 IR command."""

    address: int
    function: int
    subfunction: int

    def __init__(
        self,
        *,
        address: int,
        function: int,
        subfunction: int = 0,
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the NEC1-f16 IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.function = function
        self.subfunction = subfunction

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the NEC1-f16 command.

        NEC1-f16 protocol timing (in microseconds):
        - Leader pulse: 9000µs high, 4500µs low
        - Logical '0': 562µs high, 562µs low
        - Logical '1': 562µs high, 1687µs low
        - End pulse: 562µs high
        - Repeat code: 9000µs high, 2250µs low, 562µs end pulse
        - Frame gap: ~96ms between end pulse and next frame (total frame ~108ms)

        Data format (32 bits, LSB first):
        - address_low (8-bit)
        - address_high (8-bit)
        - function (8-bit)
        - subfunction (8-bit)
        """
        timings: list[int] = [LEADER_HIGH, -LEADER_LOW]

        address_low = self.address & 0xFF
        address_high = (self.address >> 8) & 0xFF
        function_byte = self.function & 0xFF
        subfunction_byte = self.subfunction & 0xFF

        data = (
            address_low
            | (address_high << 8)
            | (function_byte << 16)
            | (subfunction_byte << 24)
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
        """Decode raw IR timings into an NEC1F16Command.

        Returns an NEC1F16Command if the timings match, or None otherwise.
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
        function_byte = (data >> 16) & 0xFF
        subfunction_byte = (data >> 24) & 0xFF

        # Reconstruct the full 16-bit address.
        address = address_low | (address_high << 8)

        # Count repeat codes after the end pulse. Counting stops at the first
        # mismatch or truncated repeat frame; any remaining timings are ignored.
        repeat_count = cls._count_repeat_codes(timings, 67)
        return cls(
            address=address,
            function=function_byte,
            subfunction=subfunction_byte,
            repeat_count=repeat_count,
        )

    @staticmethod
    def _is_close(actual: int, expected: int) -> bool:
        """Check if an actual timing value is within tolerance of the expected value."""
        margin = expected * TOLERANCE
        return expected - margin <= actual <= expected + margin

    @staticmethod
    def _decode_bit(high_us: int, low_us: int) -> int | None:
        """Decode a single NEC1-f16 data bit from high and low timings.

        Returns 0, 1, or None if the timings don't match a valid NEC-style bit.
        """
        if not NEC1F16Command._is_close(high_us, BIT_HIGH):
            return None
        if NEC1F16Command._is_close(low_us, ZERO_LOW):
            return 0
        if NEC1F16Command._is_close(low_us, ONE_LOW):
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
                NEC1F16Command._is_close(-timings[i], gap)
                and NEC1F16Command._is_close(timings[i + 1], LEADER_HIGH)
                and NEC1F16Command._is_close(-timings[i + 2], REPEAT_LOW)
                and NEC1F16Command._is_close(timings[i + 3], BIT_HIGH)
            ):
                count += 1
                i += 4
                gap = FRAME_GAP
            else:
                return count
        return count
