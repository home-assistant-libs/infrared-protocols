"""Pioneer WYT infrared frames, sharing TCL112 pulse timings."""

from ._timing import PulseTiming
from .pd_pioneer import PdPioneerCommand


class PioneerWytCommand(PdPioneerCommand):
    """A general or fan frame, with its type-dependent checksum."""

    HEADER = (3100, -1650)
    TIMING = PulseTiming(500, 350, 1100)
    GAP = 0
