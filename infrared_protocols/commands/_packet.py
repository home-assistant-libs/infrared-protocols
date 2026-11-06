"""Internal byte-packet framing with protocol-specific checksum hooks."""

from typing import ClassVar, Self, override

from . import Command
from ._timing import PulseTiming, Reader, byte_bits, pack_bytes


class PacketCommand(Command):
    """Payload bytes excluding the checksum byte added by the transport."""

    TIMING: ClassVar[PulseTiming]
    HEADER: ClassVar[tuple[int, ...]]
    LENGTHS: ClassVar[tuple[int, ...]]
    LSB: ClassVar[bool] = True
    GAP: ClassVar[int] = 0

    def __init__(self, *, data: bytes, modulation: int = 38000) -> None:
        """Validate payload length and retain immutable bytes."""
        if len(data) not in self.LENGTHS:
            raise ValueError(f"payload length must be one of {self.LENGTHS}")
        super().__init__(modulation=modulation)
        self.data = bytes(data)
        self.checksum(self.data)

    @staticmethod
    def checksum(data: bytes) -> int:
        """Compute the additive checksum."""
        return sum(data) & 255

    @override
    def get_raw_timings(self) -> list[int]:
        """Append the checksum and encode the packet."""
        wire = self.data + bytes([self.checksum(self.data)])
        result = [
            *self.HEADER,
            *self.TIMING.encode(byte_bits(wire, lsb=self.LSB)),
            self.TIMING.mark,
        ]
        if self.GAP:
            result.append(-self.GAP)
        return result

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode an allowed packet length and verify the checksum."""
        for length in cls.LENGTHS:
            r = Reader(timings=timings)
            try:
                r.expect(*cls.HEADER)
                wire = pack_bytes(
                    r.read_bits(cls.TIMING, (length + 1) * 8), lsb=cls.LSB
                )
                r.expect(cls.TIMING.mark)
                r.end()
                if cls.checksum(wire[:-1]) == wire[-1]:
                    return cls(data=wire[:-1])
            except ValueError:
                continue
        return None
