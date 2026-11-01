"""PD-Pioneer heat-pump burst transport."""

from ._packet import PacketCommand
from ._timing import PulseTiming


class PdPioneerCommand(PacketCommand):
    """A single odd or even 14-byte burst, with checksum added automatically."""

    HEADER = (3120, -1560)
    TIMING = PulseTiming(520, 312, 1066)
    LENGTHS = (13,)
    GAP = 10010

    @staticmethod
    def checksum(data: bytes) -> int:
        """Odd bursts add fifteen to the byte sum."""
        if data[3] not in (1, 2):
            raise ValueError("burst type must be 1 or 2")
        return (sum(data) + (15 if data[3] == 2 else 0)) & 255
