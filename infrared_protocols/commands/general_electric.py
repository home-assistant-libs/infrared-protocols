"""GE AC IR command protocol."""

from typing import Self, override

from . import Command

LEADER_HIGH = 9000
LEADER_LOW = 4500
BIT_HIGH = 562
ZERO_LOW = 562
ONE_LOW = 1687
MID_FRAME_GAP = 4500
TOLERANCE = 0.4


class GEACCommand(Command):
    """GE AC IR command.

    Frame structure (MSB first throughout):
    - Leader: 9000µs mark, 4500µs space
    - 8 address bits (MSB first): each 562µs mark + 562/1687µs space
    - Mid-frame stop: 562µs mark, 4500µs space
    - 8 command bits (MSB first): each 562µs mark + 562/1687µs space
    - Stop: 562µs mark

    This is the protocol used by GE AC remotes such as the YAE1K2.
    """

    address: int
    command: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        modulation: int = 38000,
    ) -> None:
        """Initialize the GE AC IR command."""
        if not (0 <= address <= 0xFF):
            raise ValueError(f"address must be 0-255, got {address}")
        if not (0 <= command <= 0xFF):
            raise ValueError(f"command must be 0-255, got {command}")
        super().__init__(modulation=modulation, repeat_count=0)
        self.address = address
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the GE AC command."""
        timings: list[int] = [LEADER_HIGH, -LEADER_LOW]

        for i in range(7, -1, -1):
            bit = (self.address >> i) & 1
            timings.extend([BIT_HIGH, -(ONE_LOW if bit else ZERO_LOW)])

        timings.extend([BIT_HIGH, -MID_FRAME_GAP])

        for i in range(7, -1, -1):
            bit = (self.command >> i) & 1
            timings.extend([BIT_HIGH, -(ONE_LOW if bit else ZERO_LOW)])

        timings.append(BIT_HIGH)

        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a GEACCommand.

        Returns a GEACCommand if the timings match, or None otherwise.
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
            address = (address << 1) | bit

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
            command = (command << 1) | bit

        if not cls._is_close(timings[36], BIT_HIGH):
            return None

        return cls(address=address, command=command)

    @staticmethod
    def _is_close(actual: int, expected: int) -> bool:
        margin = expected * TOLERANCE
        return expected - margin <= actual <= expected + margin

    @classmethod
    def _decode_bit(cls, high_us: int, low_us: int) -> int | None:
        if not cls._is_close(high_us, BIT_HIGH):
            return None
        if cls._is_close(low_us, ZERO_LOW):
            return 0
        if cls._is_close(low_us, ONE_LOW):
            return 1
        return None
