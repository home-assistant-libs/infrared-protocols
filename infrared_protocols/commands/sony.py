"""SONY SIRC IR command."""

from typing import Self, override

from . import Command
from ._timing import Reader, close, number


class SonyCommand(Command):
    """SONY SIRC IR command."""

    address: int
    address_bits: int
    command: int

    def __init__(
        self,
        *,
        address: int,
        address_bits: int,
        command: int,
        modulation: int = 40000,
    ) -> None:
        """Initialize the SONY SIRC IR command."""
        if address_bits not in (5, 8, 13):
            raise ValueError("SONY SIRC address_bits must be one of 5, 8, or 13")
        if not 0 <= address < (1 << address_bits):
            raise ValueError("SONY SIRC address is out of range for address_bits")
        if not 0 <= command <= 0x7F:
            raise ValueError("SONY SIRC command must be in range 0x00..0x7F")
        super().__init__(modulation=modulation)
        self.address = address
        self.address_bits = address_bits
        self.command = command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the SONY SIRC command.

        SONY SIRC protocol timing:
        - T (timing unit): 600µs
        - Leader pulse: 4T high
        - Logical '0': 1T low, 1T high
        - Logical '1': 1T low, 2T high
        - Trailer: (75 - leader and data length)T low (total: 45ms)
        - No repeat code; instead, it resends the same frame

        Data format (12/15/20 bits, LSB first):
        - command (7-bit) + address (5/8/13-bit)
        """
        t = 600
        leader_high = 4 * t
        zero_high = 1 * t
        one_high = 2 * t
        bit_low = 1 * t
        frame_period = 45000

        total_bits = 7 + self.address_bits
        data = self.command | (self.address << 7)

        frame: list[int] = [leader_high]

        for _ in range(total_bits):
            bit = data & 1
            frame.append(-bit_low)
            frame.append(one_high if bit else zero_high)
            data >>= 1

        trailer_low = frame_period - sum(abs(timing) for timing in frame)
        frame.append(-trailer_low)

        return frame

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode 12-, 15- or 20-bit SIRC with an optional trailing idle space."""
        for count in (12, 15, 20):
            reader = Reader(timings)
            try:
                reader.expect(2400)
                values: list[int] = []
                for _ in range(count):
                    reader.expect(-600)
                    if reader.pos >= len(timings):
                        raise ValueError("missing SIRC mark")
                    mark = timings[reader.pos]
                    if close(mark, 600):
                        values.append(0)
                    elif close(mark, 1200):
                        values.append(1)
                    else:
                        raise ValueError("invalid SIRC mark")
                    reader.pos += 1
                reader.end(min_gap=2000)
                return cls(
                    address=number(values[7:], lsb=True),
                    address_bits=count - 7,
                    command=number(values[:7], lsb=True),
                )
            except ValueError:
                continue
        return None
