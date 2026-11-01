"""Raw LG 28- and 32-bit transports, without appliance-specific fields."""

from ._timing import PulseTiming
from ._word import WordCommand


class Lg28Command(WordCommand):
    """An arbitrary 28-bit LG word; no application checksum is imposed."""

    WIDTH = 28
    HEADER = (8000, -4000)
    TIMING = PulseTiming(600, 550, 1600)
    FOOTER = (600,)


class Lg32Command(Lg28Command):
    """The 32-bit variant of the same pulse-distance transport."""

    WIDTH = 32
