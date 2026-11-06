"""Pioneer WYT infrared frames, sharing TCL112 pulse timings."""

from ._packet import PacketCommand
from ._timing import PulseTiming
from .pd_pioneer import PdPioneerCommand


class PioneerWytCommand(PdPioneerCommand):
    """Pioneer WYT transport with unrestricted application bytes."""

    def __init__(self, *, data: bytes, modulation: int = 38000) -> None:
        """Accept any 13-byte WYT payload."""
        PacketCommand.__init__(self, data=data, modulation=modulation)

    HEADER = (3100, -1650)
    TIMING = PulseTiming(500, 350, 1100)
    GAP = 0

    @staticmethod
    def checksum(data: bytes) -> int:
        """Type two adds fifteen; other WYT packets use the byte sum."""
        return (sum(data) + (15 if data[3] == 2 else 0)) & 255
