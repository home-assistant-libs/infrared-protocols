"""Mirage 120-bit infrared packet transport."""

from ._packet import PacketCommand
from ._timing import PulseTiming


class MirageCommand(PacketCommand):
    """Fourteen payload bytes followed by a nibble-sum checksum."""

    HEADER = (8360, -4248)
    TIMING = PulseTiming(554, 545, 1592)
    LENGTHS = (14,)

    @staticmethod
    def checksum(data: bytes) -> int:
        """Sum both nibbles of each payload byte."""
        return sum((byte >> 4) + (byte & 15) for byte in data) & 255
