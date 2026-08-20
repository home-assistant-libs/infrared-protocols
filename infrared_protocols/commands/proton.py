"""Proton IR command protocol."""

from typing import Self, override

from . import Command

# Proton timing unit in microseconds. Every other duration is a multiple of it.
UNIT = 500
LEADER_HIGH = 16 * UNIT
LEADER_LOW = 8 * UNIT
BIT_HIGH = UNIT
ZERO_LOW = UNIT
ONE_LOW = 3 * UNIT
# The address and command halves are separated by a stop mark and a gap as long
# as the leader's, which is what distinguishes this protocol from NEC.
MID_FRAME_GAP = 8 * UNIT
MODULATION_HZ = 38500
TOLERANCE = 0.4


class ProtonCommand(Command):
    """Proton IR command.

    Frame structure (LSB first throughout):
    - Leader: 8000µs mark, 4000µs space
    - 8 address bits: each 500µs mark + 500/1500µs space
    - Mid-frame stop: 500µs mark, 4000µs space
    - 8 command bits: each 500µs mark + 500/1500µs space
    - Stop: 500µs mark

    Used by NEC Display projectors and televisions, and by Proton and Audiovox
    devices. ``GEACCommand`` builds the same frame shape, but numbers its bits
    the other way round and uses a longer timing unit, so the two are not
    interchangeable.
    """

    address: int
    command: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        modulation: int = MODULATION_HZ,
    ) -> None:
        """Initialize the Proton IR command."""
        if not 0 <= address <= 0xFF:
            raise ValueError(f"address must be 0-255, got {address}")
        if not 0 <= command <= 0xFF:
            raise ValueError(f"command must be 0-255, got {command}")
        super().__init__(modulation=modulation, repeat_count=0)
        self.address = address
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Proton command."""
        timings: list[int] = [LEADER_HIGH, -LEADER_LOW]

        for i in range(8):
            bit = (self.address >> i) & 1
            timings.extend([BIT_HIGH, -(ONE_LOW if bit else ZERO_LOW)])

        timings.extend([BIT_HIGH, -MID_FRAME_GAP])

        for i in range(8):
            bit = (self.command >> i) & 1
            timings.extend([BIT_HIGH, -(ONE_LOW if bit else ZERO_LOW)])

        timings.append(BIT_HIGH)

        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a ProtonCommand.

        Returns a ProtonCommand if the timings match, or None otherwise.
        Minimum: leader (2) + 8 addr pairs (16) + mid-frame (2) + 8 cmd pairs (16)
        + stop (1) = 37 timings.
        """
        if len(timings) < 37:
            return None

        if not cls._is_close(timings[0], LEADER_HIGH) or not cls._is_close(
            -timings[1], LEADER_LOW
        ):
            return None

        address = 0
        for i in range(8):
            bit = cls._decode_bit(timings[2 + 2 * i], -timings[3 + 2 * i])
            if bit is None:
                return None
            address |= bit << i

        # Validate mid-frame stop mark and gap
        if not cls._is_close(timings[18], BIT_HIGH) or not cls._is_close(
            -timings[19], MID_FRAME_GAP
        ):
            return None

        command = 0
        for i in range(8):
            bit = cls._decode_bit(timings[20 + 2 * i], -timings[21 + 2 * i])
            if bit is None:
                return None
            command |= bit << i

        if not cls._is_close(timings[36], BIT_HIGH):
            return None

        return cls(address=address, command=command)

    @staticmethod
    def _is_close(actual: int, expected: int) -> bool:
        """Check if an actual timing value is within tolerance of the expected value."""
        margin = expected * TOLERANCE
        return expected - margin <= actual <= expected + margin

    @classmethod
    def _decode_bit(cls, high_us: int, low_us: int) -> int | None:
        """Decode a single Proton data bit from high and low timings."""
        if not cls._is_close(high_us, BIT_HIGH):
            return None
        if cls._is_close(low_us, ZERO_LOW):
            return 0
        if cls._is_close(low_us, ONE_LOW):
            return 1
        return None
