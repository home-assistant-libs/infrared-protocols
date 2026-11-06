"""SONY SIRC IR command."""

from typing import Self, override

from . import Command
from ._decode import frames
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
        repeat_count: int = 0,
    ) -> None:
        """Initialize the SONY SIRC IR command."""
        if address_bits not in (5, 8, 13):
            raise ValueError("SONY SIRC address_bits must be one of 5, 8, or 13")
        if not 0 <= address < (1 << address_bits):
            raise ValueError("SONY SIRC address is out of range for address_bits")
        if not 0 <= command <= 0x7F:
            raise ValueError("SONY SIRC command must be in range 0x00..0x7F")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
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

        return frame * (self.repeat_count + 1)

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode 12-, 15- or 20-bit SIRC with an optional trailing idle space."""
        try:
            captured = frames(timings, min_gap=2000, period=45000)
        except ValueError:
            return None
        decoded_frames = [cls._decode_frame(frame) for frame in captured]
        first = decoded_frames[0]
        if first is None or any(
            value is None
            or (value.address, value.address_bits, value.command)
            != (first.address, first.address_bits, first.command)
            for value in decoded_frames[1:]
        ):
            return None
        first.repeat_count = len(captured) - 1
        return first

    @classmethod
    def _decode_frame(cls, timings: list[int]) -> Self | None:
        for count in (12, 15, 20):
            reader = Reader(timings=timings)
            try:
                reader.expect(2400)
                values: list[int] = []
                for _ in range(count):
                    reader.expect(-600)
                    if reader.pos >= len(timings):
                        raise ValueError("missing SIRC mark")
                    mark = timings[reader.pos]
                    if close(mark, 600, absolute=200):
                        values.append(0)
                    elif close(mark, 1200, absolute=200):
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
