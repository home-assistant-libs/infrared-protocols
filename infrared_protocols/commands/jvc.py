"""JVC 16-bit infrared words, in wire order."""

from ._timing import PulseTiming
from ._word import WordCommand


class JvcCommand(WordCommand):
    """JVC frame including its leader; data is the MSB-first wire word."""

    WIDTH = 16
    TIMING = PulseTiming(525, 525, 1725)
    HEADER = (8400, -4200)
    FOOTER = (525,)
